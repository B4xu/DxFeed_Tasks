"""Analyse a load_test.py run: latency percentiles per step and kind, errors by code, response
consistency (fixed-window bodies), size/shape changes, headers seen, staleness, and a fit of
latency against concurrency (linear vs exponential vs step).

    python analyze_load.py --run market_open_fri
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVIDENCE  # noqa: E402


def pct(s, p):
    return float(np.percentile(s, p)) if len(s) else math.nan


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); a = ap.parse_args()
    d = EVIDENCE / "load" / a.run
    rows = [json.loads(l) for l in (d / "requests.jsonl").read_text().splitlines()]
    df = pd.DataFrame(rows)
    meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
    out = {"run": a.run, "meta": meta, "n": len(df)}
    plots = EVIDENCE / "plots" / "load"; plots.mkdir(parents=True, exist_ok=True)

    # per step
    per_step = []
    for (step, conc), g in df.groupby(["step", "concurrency"]):
        lat = g["latency_s"].values
        per_step.append({"step": int(step), "concurrency": int(conc), "n": len(g), "errors": int((~g["ok"]).sum()),
                         "error_pct": round(100 * (~g["ok"]).mean(), 2),
                         "http_codes": {str(k): int(v) for k, v in Counter(g["http"].astype(str)).items()},
                         "dx_status": {str(k): int(v) for k, v in Counter(g.get("dx_status", pd.Series()).astype(str)).items()},
                         "p50": round(pct(lat, 50), 3), "p95": round(pct(lat, 95), 3), "p99": round(pct(lat, 99), 3), "max": round(float(lat.max()), 3),
                         "mean": round(float(lat.mean()), 3),
                         "duration_s": round((pd.to_datetime(g["ts"]).max() - pd.to_datetime(g["ts"]).min()).total_seconds(), 1),
                         # throughput through request COMPLETION: the last request finishes after it starts,
                         # so start-to-start spans overstate rps at high concurrency (in-flight work is dropped)
                         "rps": round(len(g) / max(1e-6, ((pd.to_datetime(g["ts"]) + pd.to_timedelta(g["latency_s"], unit="s")).max() - pd.to_datetime(g["ts"]).min()).total_seconds()), 2),
                         "rps_start_to_start_overstated": round(len(g) / max(1e-6, (pd.to_datetime(g["ts"]).max() - pd.to_datetime(g["ts"]).min()).total_seconds()), 2),
                         "by_kind": {k: {"n": len(kg), "p50": round(pct(kg["latency_s"], 50), 3), "p95": round(pct(kg["latency_s"], 95), 3),
                                         "err": int((~kg["ok"]).sum()), "bytes_min": int(kg["bytes"].min()) if kg["bytes"].notna().any() else None,
                                         "bytes_max": int(kg["bytes"].max()) if kg["bytes"].notna().any() else None,
                                         "age_p50": round(pct(kg["age_s"].dropna(), 50), 1) if "age_s" in kg and kg["age_s"].notna().any() else None,
                                         "age_max": round(float(kg["age_s"].max()), 1) if "age_s" in kg and kg["age_s"].notna().any() else None,
                                         "empty": int(kg.get("empty", pd.Series(dtype=bool)).fillna(False).sum())}
                                     for k, kg in g.groupby("kind")}})
    out["per_step"] = per_step

    # consistency: fixed-window bodies must be identical per symbol
    fx = df[df["kind"] == "candle_fixed"]
    cons = {}
    for sym, g in fx.groupby("symbol"):
        shas = Counter(g["sha1"].dropna())
        cons[sym] = {"n": len(g), "distinct_bodies": len(shas), "distinct_sizes": sorted(set(g["bytes"].dropna().astype(int))),
                     "n_candles": sorted(set(g["n_candles"].dropna().astype(int)))}
    out["consistency_fixed_window"] = cons
    # repeated-query latency (cache indicator): first vs later fixed-window queries
    if len(fx):
        out["fixed_window_latency"] = {"first_request_s": float(fx.iloc[0]["latency_s"]), "p50_all": round(pct(fx["latency_s"], 50), 3),
                                       "p50_step0": round(pct(fx[fx.step == 0]["latency_s"], 50), 3) if (fx.step == 0).any() else None}
    # headers observed
    hdr = Counter()
    for h in df["headers"].dropna():
        for k in h:
            hdr[k.lower()] += 1
    out["header_keys_seen"] = dict(hdr)
    sample = next((h for h in df["headers"].dropna() if h), {})
    out["header_sample"] = sample
    out["rate_limit_headers_present"] = any(k.startswith("x-ratelimit") or k == "retry-after" for k in hdr)
    # errors / symbols behaving differently
    out["errors_by_kind_symbol"] = {f"{k}|{s}": int(n) for (k, s), n in df[~df["ok"]].groupby(["kind", "symbol"]).size().items()}
    out["timed_out_by_symbol"] = {s: int(n) for s, n in df[df.get("dx_status", pd.Series()).astype(str) == "TIMED_OUT"].groupby("symbol").size().items()}
    sym_lat = df[df.kind == "quote"].groupby("symbol")["latency_s"].agg(["count", "median", lambda s: pct(s, 95)]).round(3)
    sym_lat.columns = ["n", "p50", "p95"]; out["quote_latency_by_symbol"] = sym_lat.to_dict("index")
    # staleness
    if "age_s" in df:
        st = df.dropna(subset=["age_s"]).groupby("kind")["age_s"].agg(["count", "median", "min", "max"]).round(1)
        out["staleness_by_kind"] = st.to_dict("index")

    # fit latency vs concurrency
    xs = np.array([s["concurrency"] for s in per_step], float); p50 = np.array([s["p50"] for s in per_step]); p95 = np.array([s["p95"] for s in per_step])
    fits = {}
    if len(xs) >= 3:
        for name, y in (("p50", p50), ("p95", p95)):
            lin = np.polyfit(xs, y, 1); yl = np.polyval(lin, xs)
            r2l = 1 - ((y - yl) ** 2).sum() / max(1e-12, ((y - y.mean()) ** 2).sum())
            exp = np.polyfit(xs, np.log(np.maximum(y, 1e-6)), 1); ye = np.exp(np.polyval(exp, xs))
            r2e = 1 - ((y - ye) ** 2).sum() / max(1e-12, ((y - y.mean()) ** 2).sum())
            ratios = [round(float(y[i] / y[i - 1]), 2) for i in range(1, len(y))]
            fits[name] = {"linear_slope_s_per_conn": round(float(lin[0]), 5), "linear_r2": round(float(r2l), 3),
                          "exp_rate_per_conn": round(float(exp[0]), 5), "exp_r2": round(float(r2e), 3),
                          "step_to_step_ratio": ratios, "values": [round(float(v), 3) for v in y]}
    out["latency_vs_concurrency_fit"] = fits
    (d / "analysis.json").write_text(json.dumps(out, indent=2, default=str))

    # plots
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    ax[0].plot(xs, p50, "o-", label="p50"); ax[0].plot(xs, p95, "s-", label="p95")
    ax[0].plot(xs, [s["p99"] for s in per_step], "^-", label="p99"); ax[0].set_xlabel("concurrency"); ax[0].set_ylabel("latency (seconds)")
    ax[0].set_title(f"Latency vs concurrency — {a.run}"); ax[0].grid(alpha=.3); ax[0].legend()
    for (step, conc), g in df.groupby(["step", "concurrency"]):
        ax[1].hist(g["latency_s"], bins=40, alpha=.5, label=f"c={conc}")
    ax[1].set_xlabel("latency (seconds)"); ax[1].set_title("Latency distribution per step"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    fig.suptitle("Unit: seconds, not milliseconds", fontsize=12, fontweight="bold")
    fig.tight_layout(); fig.savefig(plots / f"{a.run}_latency.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, 3.5))
    t = pd.to_datetime(df["ts"])
    for k, g in df.groupby("kind"):
        ax.plot(pd.to_datetime(g["ts"]), g["latency_s"], ".", ms=2.5, label=k)
    for (step, conc), g in df.groupby(["step", "concurrency"]):
        ax.axvline(pd.to_datetime(g["ts"]).min(), color="k", lw=.5, alpha=.5); ax.text(pd.to_datetime(g["ts"]).min(), ax.get_ylim()[1] * .9 if ax.get_ylim()[1] > 0 else 1, f"c={conc}", fontsize=8)
    ax.set_ylabel("latency (seconds)"); ax.set_title(f"Per-request latency over time — {a.run} (UTC), unit: seconds"); ax.legend(fontsize=8); ax.grid(alpha=.3)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(plots / f"{a.run}_timeline.png", dpi=120); plt.close(fig)

    # markdown summary
    L = [f"# Load test analysis — {a.run}", "", f"Window (UTC): {meta.get('started_at')} → {meta.get('finished_at')}; requests: {len(df)}; stop reason: {meta.get('stop_reason')}", "",
         "| step | conc | n | rps | errors | p50 s | p95 s | p99 s | max s | http codes | dx status |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in per_step:
        L.append(f"| {s['step']} | {s['concurrency']} | {s['n']} | {s['rps']} | {s['errors']} ({s['error_pct']}%) | {s['p50']} | {s['p95']} | {s['p99']} | {s['max']} | {s['http_codes']} | {s['dx_status']} |")
    L += ["", "rps = requests / (last completion - first start), i.e. through request completion. "
              "Start-to-start spans (older versions of this file) overstate throughput at high concurrency. "
              "p50 is computed from completed requests only; the auto-stop therefore also sees completed requests only "
              "(censored at high concurrency).", ""]
    L += ["", "Per kind (p50/p95 s, staleness p50/max s):", ""]
    for s in per_step:
        L.append(f"- c={s['concurrency']}: " + "; ".join(f"{k}: n={v['n']} p50={v['p50']} p95={v['p95']} err={v['err']} age={v['age_p50']}/{v['age_max']} bytes={v['bytes_min']}–{v['bytes_max']} empty={v['empty']}" for k, v in s["by_kind"].items()))
    L += ["", f"Fixed-window consistency: {json.dumps(cons)}", "", f"Rate-limit headers present: {out['rate_limit_headers_present']}; header keys seen: {sorted(hdr)}", "",
          f"Latency fit: {json.dumps(fits)}", "", f"TIMED_OUT by symbol: {out['timed_out_by_symbol']}", ""]
    (d / "analysis.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())

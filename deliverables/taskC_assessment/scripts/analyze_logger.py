"""Analyse weekend_logger.py output: freshness (age of latest quote / 1m candle vs wall clock),
freeze periods, close/reopen transitions per asset class, errors, and the feed delay baseline.

    python analyze_logger.py            # writes evidence/weekend_logger/analysis.{json,md} + plots/logger/*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVIDENCE, INSTRUMENTS  # noqa: E402

NY = ZoneInfo("America/New_York")
D = EVIDENCE / "weekend_logger"
FREEZE_MIN_S = 30 * 60      # a "freeze" is no new candle for >= 30 min while the market should be open


def expected_open(key: str, t: pd.Timestamp) -> bool:
    ny = t.tz_convert(NY); wd = ny.weekday(); hm = ny.hour * 60 + ny.minute
    cls = INSTRUMENTS[key][2]
    if cls in ("us_stock", "high_vol_stock"):
        return wd < 5 and 4 * 60 <= hm < 20 * 60              # extended hours 04:00-20:00 ET
    if cls == "fx":
        return not (wd == 5 or (wd == 4 and hm >= 17 * 60) or (wd == 6 and hm < 17 * 60))
    if cls == "futures_control":
        return not (wd == 5 or (wd == 4 and hm >= 17 * 60) or (wd == 6 and hm < 18 * 60) or (17 * 60 <= hm < 18 * 60))
    return True


def main() -> int:
    rows = [json.loads(l) for l in (D / "poll_log.jsonl").read_text().splitlines() if l.strip()]
    df = pd.DataFrame(rows); df["t"] = pd.to_datetime(df["polled_at"])
    out = {"polls": int(df["polled_at"].nunique()), "first": df["t"].min().isoformat(), "last": df["t"].max().isoformat(),
           "instruments": {}}
    plots = EVIDENCE / "plots" / "logger"; plots.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(INSTRUMENTS), 1, figsize=(12, 2.6 * len(INSTRUMENTS)), sharex=True)
    for ax, key in zip(axes, INSTRUMENTS):
        g = df[df.instrument == key].sort_values("t").copy()
        if g.empty:
            continue
        g["open_expected"] = [expected_open(key, t) for t in g["t"]]
        active = g[g["open_expected"] & g["quote_age_s"].notna()]
        q = lambda s, p: float(round(s.quantile(p), 1))  # noqa: E731
        res = {"polls": len(g), "errors_quote": int(g["quote_http"].ne(200).sum() + g["quote_dx_status"].ne("OK").sum()),
               "errors_candle": int(g["candle_http"].ne(200).sum() + g["candle_dx_status"].ne("OK").sum()),
               "quote_latency_p50_s": round(g["quote_latency_s"].median(), 3), "candle_latency_p50_s": round(g["candle_latency_s"].median(), 3),
               "candle_latency_max_s": round(g["candle_latency_s"].max(), 3),
               "delay_baseline_quote_age_s": {"p10": q(active["quote_age_s"], .1), "median": q(active["quote_age_s"], .5),
                                              "p90": q(active["quote_age_s"], .9)} if len(active) else None,
               "candle_age_when_open": {"median": q(active["last_candle_age_s"], .5), "p90": q(active["last_candle_age_s"], .9),
                                        "max": float(round(active["last_candle_age_s"].max(), 1))} if len(active) else None,
               "max_quote_age_s": float(round(g["quote_age_s"].max(), 1)), "max_candle_age_s": float(round(g["last_candle_age_s"].max(), 1))}
        # freezes while expected open
        fr = active[active["last_candle_age_s"] >= FREEZE_MIN_S]
        runs = []
        for t, age in zip(fr["t"], fr["last_candle_age_s"]):
            if runs and (t - runs[-1]["to"]).total_seconds() <= 180:
                runs[-1]["to"] = t; runs[-1]["max_age_s"] = max(runs[-1]["max_age_s"], age)
            else:
                runs.append({"from": t, "to": t, "max_age_s": age})
        res["freeze_runs_while_open"] = [{"from": r["from"].isoformat(), "to": r["to"].isoformat(), "max_age_s": round(r["max_age_s"], 1)} for r in runs]
        # transitions: last new candle before a closed period, first new candle after
        g["new_candle"] = g["last_candle_time"].ne(g["last_candle_time"].shift())
        trans = g[g["open_expected"].ne(g["open_expected"].shift())]
        res["session_transitions_observed"] = [{"at": t.isoformat(), "open_expected": bool(o), "last_candle_time": lc, "quote_time": qt}
                                               for t, o, lc, qt in zip(trans["t"], trans["open_expected"], trans["last_candle_time"], trans["quote_time"])][:20]
        # how stale did data get over closed periods
        closed = g[~g["open_expected"]]
        if len(closed):
            res["closed_period"] = {"polls": len(closed), "max_candle_age_s": round(closed["last_candle_age_s"].max(), 1),
                                    "distinct_last_candle_times": int(closed["last_candle_time"].nunique()),
                                    "distinct_quote_times": int(closed["quote_time"].nunique())}
        out["instruments"][key] = res
        ax.plot(g["t"], g["quote_age_s"] / 60, ".", ms=2.5, label="quote age (min)")
        ax.plot(g["t"], g["last_candle_age_s"] / 60, ".", ms=2.5, label="last 1m candle age (min)")
        ax.fill_between(g["t"], 0, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1, where=~g["open_expected"], color="grey", alpha=.15, label="expected closed")
        ax.axhline(15, color="k", lw=.6, ls="--"); ax.set_ylabel(f"{key}\nage (min)"); ax.set_yscale("symlog"); ax.grid(alpha=.3); ax.legend(fontsize=7, loc="upper left")
    axes[-1].set_xlabel("UTC"); fig.suptitle("Weekend logger: data age vs wall clock (dashed = 15 min delay baseline; grey = market expected closed)")
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(plots / "data_age_timeline.png", dpi=120); plt.close(fig)
    (D / "analysis.json").write_text(json.dumps(out, indent=2, default=str))
    L = [f"# Weekend logger analysis ({out['first']} → {out['last']}, {out['polls']} polls)", ""]
    for k, r in out["instruments"].items():
        L.append(f"## {k} ({INSTRUMENTS[k][0]})")
        L.append(f"- polls {r['polls']}, quote errors {r['errors_quote']}, candle errors {r['errors_candle']}, latency p50 quote {r['quote_latency_p50_s']} s / candle {r['candle_latency_p50_s']} s (max {r['candle_latency_max_s']} s)")
        L.append(f"- delay baseline while open (quote age): {r['delay_baseline_quote_age_s']}; candle age while open: {r['candle_age_when_open']}")
        L.append(f"- max quote age {r['max_quote_age_s']} s, max candle age {r['max_candle_age_s']} s; closed-period: {r.get('closed_period')}")
        L.append(f"- freeze runs while expected open (>= {FREEZE_MIN_S // 60} min without a new 1m candle): {r['freeze_runs_while_open'] or 'none'}")
        L.append(f"- session transitions observed: {r['session_transitions_observed'] or 'none yet'}")
        L.append("")
    (D / "analysis.md").write_text("\n".join(L) + "\n"); print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())

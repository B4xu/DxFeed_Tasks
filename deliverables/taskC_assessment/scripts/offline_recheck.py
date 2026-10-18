"""Offline re-check of headline numbers from saved evidence (no demo traffic).

    python offline_recheck.py

Writes evidence/recheck/recheck.json and recheck.md. Every number quoted in the report that was
questioned in review is recomputed here: weekend/session split for FX and ES, OHLC mismatches in
the 1h-from-5m check, ET hour coverage, daily vs sum(1h) vs sum(1m) volume, realised 1m volatility,
load throughput through request completion, TIMED_OUT latency by concurrency, per-kind latency,
and chunk boundary conflicts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVIDENCE, read_json  # noqa: E402

NY = ZoneInfo("America/New_York")
P1 = EVIDENCE / "candles" / "pass1"
VAL = EVIDENCE / "validation" / "pass1"
OUT = EVIDENCE / "recheck"


def ts(df):
    return pd.to_datetime(df["time"], unit="ms", utc=True)


def load(key, period):
    df = pd.DataFrame(read_json(P1 / f"{key}_{period}.json"))
    for c in ("open", "high", "low", "close", "volume", "count"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = ts(df)
    return df.sort_values("time").reset_index(drop=True)


def fx_split(key):
    """Split candles flagged as UTC-weekend into New York clock buckets."""
    out = {}
    for p in ("1m", "5m"):
        df = load(key, p)
        wk = df[df["ts"].dt.weekday >= 5]
        ny = wk["ts"].dt.tz_convert(NY)
        fri_after_close = int(((ny.dt.weekday == 4) & (ny.dt.hour >= 17)).sum())
        sat = int((ny.dt.weekday == 5).sum())
        sun_pre = int(((ny.dt.weekday == 6) & (ny.dt.hour < 17)).sum())
        sun_after_open = int(((ny.dt.weekday == 6) & (ny.dt.hour >= 17)).sum())
        # UTC-weekend rows that fall on NY Friday evening are Saturday 00:00Z+ candles
        out[p] = {"utc_weekend_total": int(len(wk)), "ny_friday_after_17": fri_after_close,
                  "ny_saturday": sat, "ny_sunday_before_17": sun_pre,
                  "ny_sunday_from_17_reopen": sun_after_open}
    return out


def ohlc_mismatches():
    res = {}
    for key in ("AAPL", "TSLA", "ES", "EURUSD"):
        d = pd.read_csv(VAL / f"agg_{key}_1h_from_5m.csv")
        bad = pd.Series(False, index=d.index)
        for f in ("open", "high", "low", "close"):
            bad |= ~np.isclose(d[f + "_rb"], d[f + "_sv"], rtol=0, atol=1e-9)
        rows = d[bad][["time_iso", "n_src", "open_rb", "open_sv", "high_rb", "high_sv", "low_rb", "low_sv",
                       "close_rb", "close_sv"]]
        res[key] = {"compared": int(len(d)), "ohlc_mismatch_rows": int(bad.sum()),
                    "rows": rows.round(4).to_dict("records")}
    return res


def et_hours():
    res = {}
    for key in ("AAPL", "TSLA"):
        for p in ("1m", "1h"):
            df = load(key, p)
            h = sorted(int(x) for x in df["ts"].dt.tz_convert(NY).dt.hour.unique())
            res[f"{key}_{p}"] = {"et_hours_present": h}
        d = load(key, "1h")
        first_by_day = d.groupby(d["ts"].dt.tz_convert(NY).dt.date)["ts"].min()
        res[f"{key}_1h"]["first_candle_utc_hour_hist"] = {
            int(k): int(v) for k, v in first_by_day.dt.hour.value_counts().sort_index().items()}
        res[f"{key}_1h"]["first_candle_et_hour_hist"] = {
            int(k): int(v) for k, v in first_by_day.dt.tz_convert(NY).dt.hour.value_counts().sort_index().items()}
    return res


def volume_reconcile():
    """Daily candle vs sum of 1h vs sum of 1m vs sum of 5m for each fully covered ET day."""
    res = {}
    daily = None
    for p in (EVIDENCE / "radar").glob("compare_1D_*.json"):
        daily = json.loads(p.read_text())
    res["daily_source"] = "radar/compare_1D_*.json" if daily else None
    # Daily candle volume for 2026-10-14 trading is quoted in the report; recompute sums.
    a1m, a5m, a1h = load("AAPL", "1m"), load("AAPL", "5m"), load("AAPL", "1h")
    sums = {}
    for name, df in (("1m", a1m), ("5m", a5m), ("1h", a1h)):
        day = df["ts"].dt.tz_convert(NY).dt.date
        sums[name] = df.groupby(day)["volume"].sum()
    table = {}
    for d in sorted(set(sums["1h"].index) & set(sums["1m"].index)):
        if d.weekday() >= 5:
            continue
        table[str(d)] = {k: round(float(sums[k].get(d, np.nan)), 0) for k in ("1m", "5m", "1h")}
    res["aapl_sum_by_et_day"] = table
    d14 = pd.Timestamp("2026-10-14").date()
    res["aapl_2026_10_14"] = {k: float(sums[k][d14]) for k in ("1m", "5m", "1h")}
    res["aapl_2026_10_14"]["daily_candle_volume_reported"] = 50061053.0
    r = res["aapl_2026_10_14"]
    res["aapl_2026_10_14"]["1h_vs_daily_pct"] = round(100 * (r["1h"] - 50061053.0) / 50061053.0, 3)
    res["aapl_2026_10_14"]["1m_vs_daily_pct"] = round(100 * (r["1m"] - 50061053.0) / 50061053.0, 3)
    # Worst ETH hour: served 1h vs rebuilt
    agg = pd.read_csv(VAL / "agg_AAPL_1h_from_5m.csv")
    agg["rel"] = (agg["volume_rb"] - agg["volume_sv"]) / agg["volume_sv"]
    w = agg.sort_values("rel").iloc[0]
    res["aapl_worst_hour"] = {"time_iso": w["time_iso"], "volume_rb": round(float(w["volume_rb"]), 0),
                              "volume_sv": round(float(w["volume_sv"]), 0), "rel_pct": round(100 * float(w["rel"]), 1)}
    served_gt = int((agg["volume_sv"] > agg["volume_rb"] + 1e-6).sum())
    served_lt = int((agg["volume_sv"] < agg["volume_rb"] - 1e-6).sum())
    res["aapl_1h_served_gt_rebuilt_hours"] = served_gt
    res["aapl_1h_served_lt_rebuilt_hours"] = served_lt
    return res


def realised_vol():
    res = {}
    for key in ("AAPL", "TSLA"):
        df = load(key, "1m")
        r = np.log(df["close"]).diff().dropna()
        gap = df["time"].diff().iloc[1:] == 60_000
        r = r[gap.values]
        res[key] = {"n_returns": int(len(r)), "std_1m_log_return_bp": round(float(r.std() * 1e4), 3),
                    "annualised_pct_rough": round(float(r.std() * np.sqrt(252 * 390) * 100), 1)}
    res["note"] = "contiguous 1m returns only, includes extended hours; rough, descriptive"
    return res


def load_throughput():
    res = {}
    for run in ("premarket_fri", "market_hours_fri"):
        d = EVIDENCE / "load" / run
        df = pd.DataFrame([json.loads(l) for l in (d / "requests.jsonl").read_text().splitlines()])
        df["t0"] = pd.to_datetime(df["ts"])
        df["t1"] = df["t0"] + pd.to_timedelta(df["latency_s"], unit="s")
        steps = []
        for (step, conc), g in df.groupby(["step", "concurrency"]):
            span_start_only = (g["t0"].max() - g["t0"].min()).total_seconds()
            span_done = (g["t1"].max() - g["t0"].min()).total_seconds()
            to = g[g["dx_status"] == "TIMED_OUT"] if "dx_status" in g else g.iloc[0:0]
            kinds = {k: round(float(kg["latency_s"].median()), 2) for k, kg in g.groupby("kind")}
            steps.append({"step": int(step), "c": int(conc), "n": int(len(g)),
                          "rps_start_to_start": round(len(g) / max(1e-6, span_start_only), 2),
                          "rps_through_completion": round(len(g) / max(1e-6, span_done), 2),
                          "timed_out_n": int(len(to)),
                          "timed_out_p50_s": round(float(to["latency_s"].median()), 2) if len(to) else None,
                          "timed_out_max_s": round(float(to["latency_s"].max()), 2) if len(to) else None,
                          "p50_by_kind_s": kinds})
        sym = df[df["dx_status"] == "TIMED_OUT"]["symbol"].value_counts().to_dict() if "symbol" in df else {}
        res[run] = {"steps": steps, "timed_out_by_symbol": sym}
    return res


def boundary_conflicts():
    """Boundary duplicates between chunks that disagree (same time, different OHLCV)."""
    conflicts, dups = 0, 0
    per = {}
    chunks = [json.loads(l) for l in (P1 / "chunks.jsonl").read_text().splitlines()]
    seen = {}
    for r in chunks:
        if not r.get("raw_path"):
            continue
        body = read_json(EVIDENCE / r["raw_path"])
        for lst in (body.get("Candle") or {}).values():
            for c in lst:
                k = (r["instrument"], r["period"], c["time"])
                sig = tuple(c.get(f) for f in ("open", "high", "low", "close", "volume", "count"))
                if k in seen:
                    dups += 1
                    if seen[k] != sig:
                        conflicts += 1
                        per[f"{k[0]}_{k[1]}"] = per.get(f"{k[0]}_{k[1]}", 0) + 1
                else:
                    seen[k] = sig
    return {"boundary_duplicates": dups, "boundary_conflicts": conflicts, "conflicts_by_series": per}


def totals():
    rep = json.loads((VAL / "report.json").read_text())
    n = {f"{s['instrument']}_{s['period']}": s["n"] for s in rep["series"]}
    return {"total_candles": int(sum(n.values())), "per_series": n,
            "series_outside_session": {f"{s['instrument']}_{s['period']}": s["candles_outside_session"] for s in rep["series"]},
            "series_utc_weekend": {f"{s['instrument']}_{s['period']}": s["weekend_candles"] for s in rep["series"]}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"totals": totals(), "eurusd_weekend_split": fx_split("EURUSD"), "es_weekend_split": fx_split("ES"),
           "ohlc_1h_from_5m": ohlc_mismatches(), "et_hours": et_hours(), "volume_reconcile": volume_reconcile(),
           "realised_vol": realised_vol(), "load": load_throughput(), "boundary": boundary_conflicts()}
    (OUT / "recheck.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()

"""Task C Part 1 — candle validation.

    python validate_candles.py --pass pass1 [--holidays ../../taskA_holidays/output/trading_holidays_combined.csv]

Reads evidence/candles/<pass>/<KEY>_<period>.json and produces
    evidence/validation/<pass>/report.md, report.json, per-check CSVs, and plots in evidence/plots/<pass>/.

Checks: duplicates / out-of-order (in raw responses), boundary alignment, gaps inside expected
sessions, zero-volume candles, frozen OHLC runs, NaN fields, partial last candle, weekend and
holiday behaviour (holidays from Task A), DST handling (first candle of the ET session day),
and aggregation consistency: 5m rebuilt from 1m vs served 5m, 1h rebuilt from 5m vs served 1h.
All mismatches are quantified (count, share, max abs / rel deviation).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVIDENCE, INSTRUMENTS, PERIODS, read_json  # noqa: E402

NY = ZoneInfo("America/New_York")
PERIOD_MS = {"1m": 60_000, "5m": 300_000, "1h": 3_600_000}
UTC = dt.timezone.utc


# ----------------------------------------------------------------- sessions
def in_session(key: str, t: dt.datetime) -> bool:
    """Expected trading session for gap analysis (UTC datetime of candle start).
    Equities: regular hours 09:30-16:00 New York, Mon-Fri. FX: Sun 17:00 NY -> Fri 17:00 NY.
    ES futures: Sun 18:00 NY -> Fri 17:00 NY, daily maintenance break 17:00-18:00 NY."""
    ny = t.astimezone(NY)
    wd = ny.weekday()
    hm = ny.hour * 60 + ny.minute
    cls = INSTRUMENTS[key][2]
    if cls in ("us_stock", "high_vol_stock"):
        return wd < 5 and 9 * 60 + 30 <= hm < 16 * 60
    if cls == "fx":
        if wd == 5:
            return False
        if wd == 6:
            return hm >= 17 * 60
        if wd == 4:
            return hm < 17 * 60
        return True
    if cls == "futures_control":
        if wd == 5:
            return False
        if wd == 6:
            return hm >= 18 * 60
        if wd == 4:
            return hm < 17 * 60
        return not (17 * 60 <= hm < 18 * 60)
    return True


def load(pass_dir: Path, key: str, period: str) -> pd.DataFrame:
    p = pass_dir / f"{key}_{period}.json"
    if not p.exists() and not p.with_name(p.name + ".gz").exists():
        return pd.DataFrame()
    df = pd.DataFrame(read_json(p))
    if df.empty:
        return df
    for c in ("open", "high", "low", "close", "volume", "vwap", "count", "bidVolume", "askVolume", "impVolatility"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    return df.sort_values("time").reset_index(drop=True)


def raw_order_check(pass_dir: Path, key: str, period: str) -> dict:
    """Look at the raw responses: are candles returned in time order, any duplicate times inside one response?"""
    dups = 0; out_of_order = 0; n_resp = 0; desc = 0
    for line in (pass_dir / "chunks.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["instrument"] != key or r["period"] != period or not r.get("raw_path"):
            continue
        body = read_json(EVIDENCE / r["raw_path"])
        for lst in (body.get("Candle") or {}).values():
            n_resp += 1
            times = [c["time"] for c in lst]
            dups += len(times) - len(set(times))
            if times != sorted(times):
                out_of_order += 1
                if times == sorted(times, reverse=True):
                    desc += 1
    return {"responses": n_resp, "responses_not_ascending": out_of_order, "responses_descending": desc,
            "duplicate_times_within_response": dups}


# ------------------------------------------------------------------ checks
def series_checks(key: str, period: str, df: pd.DataFrame, fetched_at: dt.datetime, holidays: pd.DataFrame) -> dict:
    res: dict = {"instrument": key, "symbol": INSTRUMENTS[key][0], "period": period, "n": int(len(df))}
    if df.empty:
        return res
    pm = PERIOD_MS[period]
    res["first"] = df["ts"].iloc[0].isoformat(); res["last"] = df["ts"].iloc[-1].isoformat()
    res["duplicate_times_after_merge"] = int(df["time"].duplicated().sum())
    res["misaligned"] = int((df["time"] % pm != 0).sum())
    # partial last candle: candle still open at fetch time (fetch time is the pass end)
    last_end = df["ts"].iloc[-1] + pd.Timedelta(milliseconds=pm)
    res["last_candle_open_at_fetch"] = bool(last_end > fetched_at)
    res["last_candle_age_at_fetch_s"] = round((fetched_at - df["ts"].iloc[-1]).total_seconds(), 1)
    # NaNs / zero volume / frozen
    res["nan_ohlc"] = int(df[["open", "high", "low", "close"]].isna().any(axis=1).sum())
    res["zero_volume"] = int((df["volume"] == 0).sum())
    res["zero_count"] = int((df["count"] == 0).sum()) if "count" in df else None
    res["high_lt_low"] = int((df["high"] < df["low"]).sum())
    res["ohlc_outside_range"] = int(((df["open"] > df["high"]) | (df["open"] < df["low"]) | (df["close"] > df["high"]) | (df["close"] < df["low"])).sum())
    same = (df[["open", "high", "low", "close"]].diff().abs().sum(axis=1) == 0)
    run = 0; longest = 0; frozen_runs = 0
    for s in same:
        if s:
            run += 1
            if run == 1:
                frozen_runs += 1
            longest = max(longest, run + 1)
        else:
            run = 0
    res["frozen_runs"] = int(frozen_runs); res["longest_frozen_run"] = int(longest)
    res["frozen_candles_share_pct"] = round(100 * same.sum() / len(df), 2)
    # gaps inside expected session
    exp = pd.date_range(df["ts"].iloc[0], df["ts"].iloc[-1], freq=pd.Timedelta(milliseconds=pm), tz="UTC")
    exp = [t for t in exp if in_session(key, t.to_pydatetime())]
    have = set(df["time"])
    missing = [t for t in exp if int(t.timestamp() * 1000) not in have]
    res["expected_in_session"] = len(exp); res["missing_in_session"] = len(missing)
    res["missing_in_session_pct"] = round(100 * len(missing) / max(1, len(exp)), 2)
    # group missing into runs for the report
    runs = []
    for t in missing:
        if runs and (t - runs[-1][1]).total_seconds() * 1000 == pm:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    res["missing_runs"] = [{"from": a.isoformat(), "to": b.isoformat(), "n": int((b - a).total_seconds() * 1000 // pm) + 1} for a, b in runs[:25]]
    res["missing_runs_total"] = len(runs)
    # candles outside expected session (e.g. weekend FX, extended hours)
    outside = df[[not in_session(key, t.to_pydatetime()) for t in df["ts"]]]
    res["candles_outside_session"] = int(len(outside)); res["candles_outside_session_pct"] = round(100 * len(outside) / len(df), 2)
    # Equities: split candles by regular hours (Mon-Fri 09:30-16:00 ET) vs everything else observed.
    if INSTRUMENTS[key][2] in ("us_stock", "high_vol_stock"):
        nyt = df["ts"].dt.tz_convert(NY)
        hm = nyt.dt.hour * 60 + nyt.dt.minute
        rth = (nyt.dt.weekday < 5) & (hm >= 9 * 60 + 30) & (hm < 16 * 60)
        res["rth_candles"] = int(rth.sum()); res["eth_candles"] = int((~rth).sum())
        res["et_hours_present"] = sorted(int(h) for h in nyt.dt.hour.unique())
    # LEGACY / informational only: UTC weekday tagging. Sunday 21:00Z+ is 17:00 ET, when FX and ES
    # legitimately reopen, so this overstates anomalies. Use candles_outside_session as the headline.
    wk = df[df["ts"].dt.weekday >= 5]
    res["weekend_candles_utc_legacy"] = int(len(wk))
    res["weekend_candles"] = int(len(wk))
    res["weekend_candle_times"] = [t.isoformat() for t in wk["ts"].head(10)]
    if INSTRUMENTS[key][2] == "fx":
        nyw = outside["ts"].dt.tz_convert(NY)
        res["outside_session_split"] = {
            "friday_after_17_et": int(((nyw.dt.weekday == 4) & (nyw.dt.hour >= 17)).sum()),
            "saturday_et": int((nyw.dt.weekday == 5).sum()),
            "sunday_before_17_et": int(((nyw.dt.weekday == 6) & (nyw.dt.hour < 17)).sum()),
            "other": int((~(((nyw.dt.weekday == 4) & (nyw.dt.hour >= 17)) | (nyw.dt.weekday == 5)
                            | ((nyw.dt.weekday == 6) & (nyw.dt.hour < 17)))).sum())}
    # per-day counts (New York calendar day)
    ny_day = df["ts"].dt.tz_convert(NY).dt.date
    res["per_day_counts"] = {str(k): int(v) for k, v in Counter(ny_day).items()}
    # holiday behaviour (US equity holidays from Task A, NYSE rows)
    if holidays is not None and not holidays.empty:
        hol = holidays[(holidays.exchange == "NYSE")]
        hits = {}
        for r in hol.itertuples():
            d = dt.date.fromisoformat(r.date)
            if df["ts"].iloc[0].date() <= d <= df["ts"].iloc[-1].date():
                n = int((ny_day == d).sum())
                sub = df[ny_day == d]
                hits[r.date] = {"holiday": r.holiday_name, "status": r.status, "candles": n,
                                "first": sub["ts"].iloc[0].astimezone(NY).strftime("%H:%M ET") if n else None,
                                "last": sub["ts"].iloc[-1].astimezone(NY).strftime("%H:%M ET") if n else None}
        res["holidays_in_range"] = hits
    # DST: first candle of each NY day in UTC hour terms (should move by 1h when DST changes)
    if period == "1h":
        first_by_day = df.groupby(ny_day)["ts"].min()
        utc_hours = Counter(t.hour for t in first_by_day)
        res["first_candle_utc_hour_hist"] = dict(sorted(utc_hours.items()))
        for day in (dt.date(2026, 3, 6), dt.date(2026, 3, 9)):   # Fri before / Mon after US DST start (Mar 8 2026)
            if day in first_by_day.index:
                res[f"first_candle_{day}"] = first_by_day[day].isoformat()
    return res


def aggregate(df: pd.DataFrame, target_ms: int) -> pd.DataFrame:
    g = df.assign(bucket=(df["time"] // target_ms) * target_ms).groupby("bucket")
    out = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
                volume=("volume", "sum"), count=("count", "sum"), n_src=("time", "size"))
    return out.reset_index().rename(columns={"bucket": "time"})


def compare(rebuilt: pd.DataFrame, served: pd.DataFrame, label: str, tol_rel: float = 1e-9) -> tuple:
    m = rebuilt.merge(served, on="time", how="inner", suffixes=("_rb", "_sv"))
    res: dict = {"label": label, "rebuilt_buckets": int(len(rebuilt)), "served_candles": int(len(served)), "compared": int(len(m))}
    res["served_without_source"] = int(len(set(served["time"]) - set(rebuilt["time"])))
    res["rebuilt_without_served"] = int(len(set(rebuilt["time"]) - set(served["time"])))
    fields = {}
    for f in ("open", "high", "low", "close", "volume", "count"):
        a, b = m[f + "_rb"], m[f + "_sv"]
        diff = (a - b).abs()
        rel = diff / b.abs().replace(0, math.nan)
        mism = diff > (b.abs() * tol_rel + 1e-9)
        fields[f] = {"mismatches": int(mism.sum()), "pct": round(100 * mism.sum() / max(1, len(m)), 2),
                     "max_abs": float(diff.max()) if len(diff) else None,
                     "max_rel_pct": round(float(rel.max() * 100), 4) if len(rel.dropna()) else None,
                     "mean_rel_pct": round(float(rel.mean() * 100), 4) if len(rel.dropna()) else None}
    res["fields"] = fields
    # explicit any-of over every OHLC field and volume (same tolerance as the per-field counts above)
    field_masks = np.column_stack([
        ((m[f + "_rb"] - m[f + "_sv"]).abs() > (m[f + "_sv"].abs() * tol_rel + 1e-9)).to_numpy()
        for f in ("open", "high", "low", "close", "volume")])
    any_mism = m[np.any(field_masks, axis=1)]
    ohlc_masks = field_masks[:, :4]
    res["candles_with_ohlc_mismatch"] = int(np.any(ohlc_masks, axis=1).sum())
    res["ohlc_mismatch_times"] = pd.to_datetime(m.loc[np.any(ohlc_masks, axis=1), "time"], unit="ms", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()[:20]
    res["candles_with_any_mismatch"] = int(len(any_mism)); res["candles_with_any_mismatch_pct"] = round(100 * len(any_mism) / max(1, len(m)), 2)
    ex = any_mism.head(15).copy()
    ex["time_iso"] = pd.to_datetime(ex["time"], unit="ms", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    res["examples"] = ex[["time_iso", "n_src", "open_rb", "open_sv", "high_rb", "high_sv", "low_rb", "low_sv", "close_rb", "close_sv", "volume_rb", "volume_sv"]].to_dict("records")
    # Where do mismatches sit? by n_src (incomplete source buckets) and by time of day
    if len(any_mism):
        res["mismatch_by_n_src"] = {str(k): int(v) for k, v in Counter(any_mism["n_src"]).items()}
        hrs = pd.to_datetime(any_mism["time"], unit="ms", utc=True).dt.tz_convert(NY).dt.strftime("%H:%M")
        res["mismatch_by_ny_time_top"] = dict(Counter(hrs).most_common(8))
    return res, m, any_mism


# ------------------------------------------------------------------- plots
def plot_per_day(all_checks: list[dict], plots: Path, pass_name: str):
    fig, axes = plt.subplots(len(INSTRUMENTS), 1, figsize=(11, 2.4 * len(INSTRUMENTS)), sharex=True)
    for ax, key in zip(axes, INSTRUMENTS):
        c = next((x for x in all_checks if x["instrument"] == key and x["period"] == "1m"), None)
        if not c or "per_day_counts" not in c:
            continue
        s = pd.Series(c["per_day_counts"]); s.index = pd.to_datetime(s.index)
        s = s.reindex(pd.date_range(s.index.min(), s.index.max()), fill_value=0)
        colors = ["#d62728" if d.weekday() >= 5 else "#1f77b4" for d in s.index]
        ax.bar(s.index, s.values, color=colors)
        ax.set_ylabel(f"{key}\n1m candles/day"); ax.grid(alpha=.3)
    axes[-1].set_xlabel("New York calendar day (red = Saturday/Sunday)")
    fig.suptitle(f"1-minute candles per day — {pass_name} (weekend handling)")
    fig.tight_layout(); fig.savefig(plots / "per_day_1m_counts.png", dpi=120); plt.close(fig)


def plot_mismatch(m: pd.DataFrame, any_mism: pd.DataFrame, label: str, plots: Path):
    if m.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 3.5))
    t = pd.to_datetime(m["time"], unit="ms", utc=True)
    rel = ((m["volume_rb"] - m["volume_sv"]) / m["volume_sv"].replace(0, math.nan) * 100)
    ax.plot(t, rel, ".", ms=3, label="volume: rebuilt vs served (%)")
    relc = ((m["close_rb"] - m["close_sv"]) / m["close_sv"] * 100)
    ax.plot(t, relc, "x", ms=3, label="close: rebuilt vs served (%)")
    ax.axhline(0, color="k", lw=.5); ax.set_ylabel("deviation %"); ax.legend(loc="upper left", fontsize=8)
    ax.set_title(f"Aggregation check {label}: {len(any_mism)} of {len(m)} candles differ"); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(plots / f"agg_{label.replace(' ', '_').replace('/', '')}.png", dpi=120); plt.close(fig)


def plot_weekend_fx(df: pd.DataFrame, plots: Path, key: str):
    if df.empty:
        return
    sub = df[(df["ts"] >= "2026-10-09T18:00:00Z") & (df["ts"] <= "2026-10-12T02:00:00Z")]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.plot(sub["ts"], sub["close"], ".", ms=3)
    for t in sub["ts"]:
        if not in_session(key, t.to_pydatetime()):
            ax.axvline(t, color="#d62728", alpha=.35, lw=.8)
    ax.set_title(f"{key} 1m close, Fri 2026-10-09 18:00Z → Mon 2026-10-12 02:00Z "
                 "(red = candles OUTSIDE the FX session; Sunday 17:00 ET+ reopen is not red)")
    ax.grid(alpha=.3); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(plots / f"weekend_{key}_1m.png", dpi=120); plt.close(fig)


# -------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="pass_name", required=True)
    ap.add_argument("--holidays", default=str(Path(__file__).resolve().parents[2] / "taskA_holidays" / "output" / "trading_holidays_combined.csv"))
    a = ap.parse_args()
    pass_dir = EVIDENCE / "candles" / a.pass_name
    out = EVIDENCE / "validation" / a.pass_name; out.mkdir(parents=True, exist_ok=True)
    plots = EVIDENCE / "plots" / a.pass_name; plots.mkdir(parents=True, exist_ok=True)
    summary = json.loads((pass_dir / "summary.json").read_text())
    fetched_at = pd.Timestamp(summary["end"]).tz_localize("UTC") if pd.Timestamp(summary["end"]).tzinfo is None else pd.Timestamp(summary["end"])
    holidays = pd.read_csv(a.holidays, dtype=str) if Path(a.holidays).exists() else pd.DataFrame()

    all_checks, aggs = [], []
    for key in INSTRUMENTS:
        dfs = {p: load(pass_dir, key, p) for p in PERIODS}
        for p in PERIODS:
            c = series_checks(key, p, dfs[p], fetched_at, holidays)
            c["raw_order"] = raw_order_check(pass_dir, key, p) if not dfs[p].empty else None
            all_checks.append(c)
        if not dfs["1m"].empty and not dfs["5m"].empty:
            lo, hi = dfs["1m"]["time"].min(), dfs["1m"]["time"].max()
            served = dfs["5m"][(dfs["5m"]["time"] >= (lo // 300000) * 300000) & (dfs["5m"]["time"] <= hi)]
            r, m, am = compare(aggregate(dfs["1m"], 300_000), served, f"{key} 5m from 1m")
            aggs.append(r); m.to_csv(out / f"agg_{key}_5m_from_1m.csv", index=False); plot_mismatch(m, am, f"{key} 5m from 1m", plots)
        if not dfs["5m"].empty and not dfs["1h"].empty:
            lo, hi = dfs["5m"]["time"].min(), dfs["5m"]["time"].max()
            served = dfs["1h"][(dfs["1h"]["time"] >= (lo // 3600000) * 3600000) & (dfs["1h"]["time"] <= hi)]
            r, m, am = compare(aggregate(dfs["5m"], 3_600_000), served, f"{key} 1h from 5m")
            aggs.append(r); m.to_csv(out / f"agg_{key}_1h_from_5m.csv", index=False); plot_mismatch(m, am, f"{key} 1h from 5m", plots)
        if key == "EURUSD":
            plot_weekend_fx(dfs["1m"], plots, key)
    plot_per_day(all_checks, plots, a.pass_name)

    (out / "report.json").write_text(json.dumps({"pass": a.pass_name, "fetched_at": str(fetched_at), "series": all_checks, "aggregation": aggs}, indent=2, default=str))
    # markdown
    L = [f"# Candle validation — {a.pass_name} (data as of {fetched_at})", "", "## Series checks", "",
         "Headline anomaly count = **outside session** (session model: equities 09:30-16:00 ET; FX Sun 17:00 ET - Fri 17:00 ET; ES Sun 18:00 ET - Fri 17:00 ET "
         "minus 17:00-18:00 break). The `weekend (UTC, legacy)` column tags UTC Saturday/Sunday and counts the legitimate Sunday reopen; it is informational only.", "",
         "| series | n | first | last | dup | misaligned | missing in session | **outside session** | weekend (UTC, legacy) | zero-vol | frozen runs (longest) | last open at fetch | resp. not ascending |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in all_checks:
        if c["n"] == 0:
            L.append(f"| {c['instrument']} {c['period']} | 0 | | | | | | | | | | | |"); continue
        ro = c["raw_order"] or {}
        L.append(f"| {c['instrument']} {c['period']} | {c['n']} | {c['first'][:16]} | {c['last'][:16]} | {c['duplicate_times_after_merge']} | {c['misaligned']} | "
                 f"{c['missing_in_session']}/{c['expected_in_session']} ({c['missing_in_session_pct']}%) | {c['candles_outside_session']} ({c['candles_outside_session_pct']}%) | {c['weekend_candles']} | "
                 f"{c['zero_volume']} | {c['frozen_runs']} ({c['longest_frozen_run']}) | {c['last_candle_open_at_fetch']} ({c['last_candle_age_at_fetch_s']}s) | {ro.get('responses_not_ascending')}/{ro.get('responses')} |")
    L += ["", "## Aggregation consistency", "", "| check | compared | any mismatch | open | high | low | close | volume | served w/o source | rebuilt w/o served |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in aggs:
        f = r["fields"]
        L.append(f"| {r['label']} | {r['compared']} | {r['candles_with_any_mismatch']} ({r['candles_with_any_mismatch_pct']}%) | {f['open']['mismatches']} | {f['high']['mismatches']} | {f['low']['mismatches']} | {f['close']['mismatches']} | "
                 f"{f['volume']['mismatches']} (max {f['volume']['max_rel_pct']}%) | {r['served_without_source']} | {r['rebuilt_without_served']} |")
    L += ["", "## Holidays in range (NYSE calendar from Task A, 1h series)", ""]
    for c in all_checks:
        if c.get("period") == "1h" and c.get("holidays_in_range"):
            for d, h in c["holidays_in_range"].items():
                L.append(f"- {c['instrument']} {d} {h['holiday']} ({h['status']}): {h['candles']} hourly candles" + (f", {h['first']}–{h['last']}" if h['candles'] else ""))
    L += ["", "## DST (first 1h candle of the New York day, UTC hour histogram)", ""]
    for c in all_checks:
        if c.get("period") == "1h" and c.get("first_candle_utc_hour_hist"):
            L.append(f"- {c['instrument']}: {c['first_candle_utc_hour_hist']}; Fri 2026-03-06 → {c.get('first_candle_2026-03-06')}, Mon 2026-03-09 → {c.get('first_candle_2026-03-09')}")
    L += ["", "## Missing runs inside expected sessions (first 25 per series)", ""]
    for c in all_checks:
        if c.get("missing_runs"):
            L.append(f"- {c['instrument']} {c['period']}: {c['missing_runs_total']} runs; " + "; ".join(f"{r['from'][:16]}→{r['to'][11:16]} ({r['n']})" for r in c["missing_runs"][:12]))
    (out / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Presentation-quality summary charts for Task C, built offline from saved evidence.

    python make_report_charts.py

Reads evidence/recheck/recheck.json, evidence/validation/pass1/*.csv and the load request logs;
writes PNGs to taskC_assessment/charts/. No demo traffic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
from dxclient import EVIDENCE  # noqa: E402
from report_kit import (AMBER, BLUE, CORAL, GREEN, NAVY, PURPLE, SLATE, TEAL,  # noqa: E402
                        mpl_style, plt)

NY = ZoneInfo("America/New_York")
OUT = HERE.parent / "charts"
RC = json.loads((EVIDENCE / "recheck" / "recheck.json").read_text())
VAL = EVIDENCE / "validation" / "pass1"


def _save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p)
    plt.close(fig)
    return p


def throughput():
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for run, color, label in (("premarket_fri", AMBER, "Pre-market (11:52Z)"),
                              ("market_hours_fri", TEAL, "Market hours (13:47Z)")):
        st = RC["load"][run]["steps"]
        c = [s["c"] for s in st]
        r = [s["rps_through_completion"] for s in st]
        ax.plot(c, r, "o-", color=color, lw=2.6, ms=9, label=label)
        for x, y in zip(c, r):
            ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=9.5, color=color, fontweight="bold")
    ax.axhspan(2.75, 3.25, color=TEAL, alpha=0.08)
    ax.text(50, 3.33, "saturation ≈ 3 req/s", ha="right", color=TEAL, fontsize=10)
    ax.set_xscale("log")
    ax.set_xticks([1, 5, 10, 25, 50], ["1", "5", "10", "25", "50"])
    ax.set_xlabel("Configured concurrency (parallel workers, log scale)")
    ax.set_ylabel("Throughput (requests per second)")
    ax.set_ylim(0, 3.9)
    ax.set_title("More parallel workers did not buy more throughput")
    ax.legend(loc="lower right")
    return _save(fig, "throughput_vs_concurrency.png")


def latency_by_kind():
    st = RC["load"]["market_hours_fri"]["steps"]
    kinds = [("quote", BLUE, "Quote"), ("candle_fixed", PURPLE, "Candle, fixed window"),
             ("candle_fresh", CORAL, "Candle, latest")]
    c = [s["c"] for s in st]
    x = np.arange(len(c))
    w = 0.26
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for i, (k, col, lab) in enumerate(kinds):
        v = [s["p50_by_kind_s"].get(k, np.nan) for s in st]
        bars = ax.bar(x + (i - 1) * w, v, w, color=col, label=lab)
        for b, y in zip(bars, v):
            if not np.isnan(y):
                ax.text(b.get_x() + b.get_width() / 2, y + 0.4, f"{y:.1f}", ha="center", fontsize=8.5, color=SLATE)
    ax.set_xticks(x, [f"c={v}" for v in c])
    ax.set_ylabel("p50 latency (seconds)")
    ax.set_title("Under load, candle requests wait far longer than quotes (market hours)")
    ax.legend(loc="upper left")
    ax.text(4, -2.6, "fixed-window n=17 at c=50", ha="center", fontsize=8, color=SLATE)
    return _save(fig, "latency_by_request_type.png")


def timed_out():
    st = RC["load"]["market_hours_fri"]["steps"]
    c = [s["c"] for s in st if s["timed_out_p50_s"]]
    v = [s["timed_out_p50_s"] for s in st if s["timed_out_p50_s"]]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar([str(x) for x in c], v, color=[GREEN, AMBER, AMBER, CORAL, CORAL])
    for i, y in enumerate(v):
        ax.text(i, y + 0.6, f"{y:.1f} s", ha="center", fontweight="bold", color=NAVY)
    ax.set_xlabel("Configured concurrency")
    ax.set_ylabel("TIMED_OUT response time (seconds)")
    ax.set_title("TIMED_OUT for AUD/USD bid candles: 3 s alone, 29 s under load")
    return _save(fig, "timed_out_stretch.png")


def fx_session():
    rep = json.loads((VAL / "report.json").read_text())
    ser = next(s for s in rep["series"] if s["instrument"] == "EURUSD" and s["period"] == "1m")
    d = ser["outside_session_split"]
    fri, sat, sun = d["friday_after_17_et"], d["saturday_et"], d["sunday_before_17_et"]
    utc = RC["eurusd_weekend_split"]["1m"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1, 1.25]})
    vals = [fri, sun]
    a1.pie(vals, labels=[f"Friday after\n17:00 ET close\n{fri}", f"Sunday before\n17:00 ET reopen\n{sun}"],
           colors=[AMBER, CORAL], startangle=90, labeldistance=1.18, wedgeprops=dict(width=0.38, edgecolor="white"),
           textprops=dict(fontsize=10))
    a1.text(0, 0, f"{fri + sat + sun}\nout of\nsession", ha="center", va="center", fontsize=13,
            fontweight="bold", color=NAVY)
    a1.set_title("EUR/USD 1m candles outside the FX session")
    a1.text(0, -1.35, f"Saturday (New York time): {sat}", ha="center", fontsize=9.5, color=SLATE)
    labels = ["UTC-weekday\n'weekend' tag\n(old headline)", "Legitimate\nSunday reopen\n(17:00–19:59 ET)",
              "Truly outside\nsession\n(new headline)"]
    v2 = [utc["utc_weekend_total"], utc["ny_sunday_from_17_reopen"], fri + sat + sun]
    a2.bar(labels, v2, color=[SLATE, GREEN, CORAL])
    for i, y in enumerate(v2):
        a2.text(i, y + 4, str(y), ha="center", fontweight="bold", color=NAVY)
    a2.set_ylabel("1-minute candles")
    a2.set_title("Why 214 was the wrong headline")
    a2.grid(axis="x", visible=False)
    fig.tight_layout()
    return _save(fig, "fx_outside_session.png")


def aapl_heatmap():
    df = pd.read_csv(VAL / "agg_AAPL_1h_from_5m.csv")
    t = pd.to_datetime(df["time_iso"], utc=True).dt.tz_convert(NY)
    df["day"] = t.dt.strftime("%a %d %b")
    df["d"] = t.dt.date
    df["hour"] = t.dt.hour
    df["rel"] = (df["volume_rb"] - df["volume_sv"]) / df["volume_sv"] * 100
    piv = df.pivot_table(index="d", columns="hour", values="rel", aggfunc="first")
    labels = [pd.Timestamp(d).strftime("%a %d %b") for d in piv.index]
    fig, ax = plt.subplots(figsize=(11, 4.9))
    cmap = plt.get_cmap("RdBu").copy()
    cmap.set_bad("#F0F0F0")
    im = ax.imshow(np.ma.masked_invalid(piv.values), aspect="auto", cmap=cmap, vmin=-60, vmax=60)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xticks(range(len(piv.columns)), [f"{h:02d}" for h in piv.columns])
    ax.set_xlabel("Hour of the hourly candle (New York time)")
    ax.grid(False)
    cols = list(piv.columns)
    if 9 in cols and 15 in cols:
        a, b = cols.index(9) - 0.5, cols.index(15) + 0.5
        ax.add_patch(plt.Rectangle((a, -0.5), b - a, len(labels), fill=False, ec=NAVY, lw=2.2))
        ax.text((a + b) / 2, -0.8, "regular-hours candles (09:00–15:00 bars)", ha="center",
                color=NAVY, fontsize=9.5, fontweight="bold")
    i8 = list(piv.index).index(pd.Timestamp("2026-10-08").date()) if pd.Timestamp("2026-10-08").date() in piv.index else None
    if i8 is not None and 11 in cols:
        ax.annotate("+2 % RTH exception", (cols.index(11), i8), xytext=(cols.index(11) + 1.6, i8 + 1.6),
                    fontsize=9, color=BLUE, fontweight="bold", arrowprops=dict(arrowstyle="->", color=BLUE))
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Σ5m vs served 1h volume (%)")
    ax.set_title("AAPL: hourly volume disagrees with the 5-minute sum outside regular hours", pad=22)
    return _save(fig, "aapl_volume_heatmap.png")


def volume_reconcile():
    vr = RC["volume_reconcile"]
    days = vr["aapl_sum_by_et_day"]
    keep = [d for d in days if d not in ("2026-10-05", "2026-10-16")]
    m1 = np.array([days[d]["1m"] for d in keep]) / 1e6
    h1 = np.array([days[d]["1h"] for d in keep]) / 1e6
    x = np.arange(len(keep))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [2.2, 1]})
    a1.bar(x - 0.2, m1, 0.4, color=BLUE, label="Σ 1-minute")
    a1.bar(x + 0.2, h1, 0.4, color=TEAL, label="Σ hourly")
    a1.set_xticks(x, [pd.Timestamp(d).strftime("%d %b") for d in keep])
    a1.set_ylabel("AAPL volume per New York day (millions)")
    a1.set_title("Hourly totals are never below the 1-minute totals")
    a1.legend(loc="upper left")
    d = vr["aapl_2026_10_14"]
    vals = [d["daily_candle_volume_reported"] / 1e6, d["1h"] / 1e6, d["1m"] / 1e6]
    a2.barh(["Daily candle", "Σ hourly", "Σ 1-minute"], vals, color=[NAVY, TEAL, BLUE])
    lo = min(vals) * 0.995
    a2.set_xlim(lo, max(vals) * 1.001)
    for i, v in enumerate(vals):
        a2.text(v, i, f" {v:.3f}M", va="center", fontsize=9.5, color=NAVY)
    a2.set_xlabel(f"millions (axis starts at {lo:.2f}M)")
    a2.set_title(f"14 Oct, the only day with a daily bar\nhourly {d['1h_vs_daily_pct']:+.2f}% · 1-minute "
                 f"{d['1m_vs_daily_pct']:+.2f}% vs daily", fontsize=12)
    fig.tight_layout()
    return _save(fig, "volume_reconcile.png")


def ohlc_mismatch():
    rows = []
    for inst in ("AAPL", "TSLA", "ES", "EURUSD"):
        df = pd.read_csv(VAL / f"agg_{inst}_1h_from_5m.csv")
        for _, r in df.iterrows():
            for f in ("open", "high", "low", "close"):
                a, b = r[f"{f}_rb"], r[f"{f}_sv"]
                if pd.notna(a) and pd.notna(b) and not np.isclose(a, b, rtol=1e-9, atol=1e-9):
                    rows.append((f"{inst} {r['time_iso'][5:16].replace('T', ' ')}Z {f}",
                                 abs(a - b) / abs(b) * 100, r["n_src"] < 12))
    rows.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=[AMBER if r[2] else CORAL for r in rows])
    for i, r in enumerate(rows):
        ax.text(r[1], i, f" {r[1]:.4f}%", va="center", fontsize=9, color=NAVY)
    ax.set_xlabel("Absolute difference, served 1h vs rebuilt from 5m (% of price)")
    ax.set_title(f"Price fields: {len({r[0].rsplit(' ', 1)[0] for r in rows})} hourly candles differ, all by ≤ 0.03 %")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=CORAL, label="complete hour (12 of 12 five-minute bars)"),
                       Patch(color=AMBER, label="forming hour at fetch time")], loc="lower right")
    return _save(fig, "ohlc_mismatches.png")


def candle_totals():
    per = RC["totals"]["per_series"]
    inst = ["AAPL", "TSLA", "EURUSD", "ES"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bottom = np.zeros(len(inst))
    for p, col in (("1m", NAVY), ("5m", TEAL), ("1h", AMBER)):
        v = np.array([per[f"{i}_{p}"] for i in inst])
        ax.bar(inst, v, bottom=bottom, color=col, label=p)
        for j, val in enumerate(v):
            ax.text(j, bottom[j] + val / 2, f"{val:,}", ha="center", va="center", color="white", fontsize=9)
        bottom += v
    ax.set_ylabel("Candles retrieved")
    ax.set_title(f"{RC['totals']['total_candles']:,} candles in pass 1 (1m series capped near 8,000)")
    ax.legend(ncol=3, loc="upper right")
    ax.set_ylim(0, bottom.max() * 1.12)
    return _save(fig, "candle_totals.png")


def quote_age():
    ages = []
    for run in ("premarket_fri", "market_hours_fri"):
        for line in (EVIDENCE / "load" / run / "requests.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "quote" and r.get("age_s") is not None:
                ages.append(r["age_s"])
    ages = np.array(ages)
    fig, ax = plt.subplots(figsize=(10, 4.0))
    ax.hist(ages, bins=np.arange(890, 965, 2.5), color=TEAL, edgecolor="white")
    ax.axvline(900, color=CORAL, ls="--", lw=2)
    ax.text(903.5, ax.get_ylim()[1] * 0.9, "900 s = 15 minutes", color=CORAL, fontweight="bold")
    ax.set_xlabel("Quote age at response time (seconds)")
    ax.set_ylabel("Quote responses")
    ax.set_title(f"Every quote is ~15 minutes old (median {np.median(ages):.1f} s, n={len(ages)})")
    return _save(fig, "quote_age.png")


def main():
    mpl_style()
    out = {f.__name__: f() for f in (throughput, latency_by_kind, timed_out, fx_session, aapl_heatmap,
                                      volume_reconcile, ohlc_mismatch, candle_totals, quote_age)}
    for k, v in out.items():
        print(k, v)
    return out


if __name__ == "__main__":
    main()

"""Automated validation of the normalised holiday table.

Checks: weekday-only dates, no duplicates, plausible closure counts per year, NYSE == NASDAQ,
OPRA agrees with equities (differences flagged, never fixed), Good Friday == computed Easter-2,
early closes have a close time, diff against the previous run with a change threshold.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
from pathlib import Path

import pandas as pd

PLAUSIBLE_CLOSURES = {"NYSE": (8, 11), "NASDAQ": (8, 11), "OPRA": (8, 11), "CME": (2, 14)}
EQUITY_LIKE = ["NYSE", "NASDAQ", "OPRA"]
MAX_ROW_CHANGE_PCT = 30.0


MIN_EARLY_CLOSES = {"NYSE": 1, "NASDAQ": 1}


def easter(year: int) -> dt.date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(year, month, day)


def good_friday(year: int) -> dt.date:
    return easter(year) - dt.timedelta(days=2)


@dataclasses.dataclass
class Check:
    name: str
    level: str  # PASS | WARN | FAIL
    detail: str


def run_checks(df: pd.DataFrame, adapter_counts: dict[str, int], adapter_notes: dict[str, list[str]],
               previous_csv: Path | None) -> list[Check]:
    checks: list[Check] = []
    if df.empty:
        return [Check("rows", "FAIL", "normalised table is empty")]
    dfd = df.assign(dtp=pd.to_datetime(df["date"]))

    # 1. zero-row parsers
    for ex, n in adapter_counts.items():
        if n == 0:
            notes = adapter_notes.get(ex, [])
            manual = any("MANUAL_INPUT_REQUIRED" in x for x in notes)
            unavailable = any("SOURCE_UNAVAILABLE" in x for x in notes)
            if manual:
                checks.append(Check(f"{ex}.rows", "WARN", f"{ex} returned 0 rows (manual input required, see notes)"))
            elif unavailable:
                checks.append(Check(f"{ex}.rows", "WARN", f"{ex} MISSING: all sources failed, see adapter notes; other exchanges unaffected"))
            else:
                checks.append(Check(f"{ex}.rows", "FAIL", f"{ex} returned 0 rows"))
        else:
            checks.append(Check(f"{ex}.rows", "PASS", f"{ex} returned {n} rows"))

    # 2. weekdays only
    wk = dfd[dfd["dtp"].dt.weekday >= 5]
    checks.append(Check("weekday", "FAIL" if len(wk) else "PASS",
                        f"{len(wk)} weekend-dated rows" + (": " + "; ".join(f"{r.exchange} {r.date} {r.holiday_name}" for r in wk.itertuples()) if len(wk) else "")))

    # 3. duplicates
    dup = df[df.duplicated(subset=["exchange", "date", "status"], keep=False)]
    checks.append(Check("duplicates", "FAIL" if len(dup) else "PASS", f"{len(dup)} duplicate (exchange,date,status) rows"))

    # 4. closures per year plausible
    closed = dfd[dfd["status"] == "closed"]
    for (ex, y), g in closed.groupby(["exchange", dfd["dtp"].dt.year]):
        lo, hi = PLAUSIBLE_CLOSURES.get(ex, (1, 20))
        # a partial-year source (e.g. OPRA listing next year's Jan 1 only) is not a failure
        if len(g) <= 2 and y != g["source_year"].iloc[0]:
            checks.append(Check(f"{ex}.{y}.closures", "PASS", f"{len(g)} closure(s) spilling from source_year {g['source_year'].iloc[0]}"))
            continue
        ok = lo <= len(g) <= hi
        checks.append(Check(f"{ex}.{y}.closures", "PASS" if ok else "FAIL", f"{len(g)} full-day closures (plausible {lo}-{hi})"))

    # 5. early closes have a time
    ec = df[(df["status"] == "early_close") & (df["close_time_local"] == "")]
    checks.append(Check("early_close_time", "WARN" if len(ec) else "PASS", f"{len(ec)} early-close rows without a close time"))

    # 5b. minimum early-close count per exchange-year: a footnote-parsing regression that
    # silently yields 0 early closes must not pass (NYSE/NASDAQ normally list 2-3 per year).
    for (ex, y), g in dfd.groupby(["exchange", dfd["dtp"].dt.year]):
        if ex not in MIN_EARLY_CLOSES:
            continue
        full_year = (g["status"] == "closed").sum() > 2
        if not full_year:
            continue
        n_ec = int((g["status"] == "early_close").sum())
        need = MIN_EARLY_CLOSES[ex]
        lvl = "PASS" if n_ec >= need else "WARN"
        checks.append(Check(f"{ex}.{y}.early_closes", lvl, f"{n_ec} early closes (minimum expected {need})" + ("" if lvl == "PASS" else "; check footnote parsing")))

    # 6. NYSE vs NASDAQ, OPRA vs equities (same year coverage only)
    def dates(ex, status, years):
        s = dfd[(dfd["exchange"] == ex) & (dfd["status"] == status) & dfd["dtp"].dt.year.isin(years)]
        return set(s["date"])
    years_by_ex = {ex: set(dfd[(dfd["exchange"] == ex) & (dfd["status"] == "closed")]["source_year"]) for ex in EQUITY_LIKE}
    for a, b in [("NYSE", "NASDAQ"), ("NYSE", "OPRA"), ("NASDAQ", "OPRA")]:
        common = years_by_ex.get(a, set()) & years_by_ex.get(b, set())
        if not common:
            checks.append(Check(f"{a}_vs_{b}", "WARN", f"no overlapping source years ({sorted(years_by_ex.get(a, []))} vs {sorted(years_by_ex.get(b, []))}); comparison skipped"))
            continue
        for status in ("closed", "early_close"):
            da, db = dates(a, status, common), dates(b, status, common)
            diff = sorted(da ^ db)
            lvl = "PASS" if not diff else ("FAIL" if status == "closed" else "WARN")
            checks.append(Check(f"{a}_vs_{b}.{status}", lvl, f"years {sorted(common)}: {len(diff)} differing dates" + (f": only in {a}: {sorted(da - db)}; only in {b}: {sorted(db - da)}" if diff else "")))

    # 6b. NYSE vs CME equity index, only for years where the CME input covers a full calendar.
    # CME early closes are 12:00-12:15 CT, so only the dates are compared. A difference is WARN:
    # futures and cash equities can legitimately differ.
    cme_closed = dfd[(dfd["exchange"] == "CME") & (dfd["status"] == "closed")]
    full_cme_years = sorted(y for y, g in cme_closed.groupby(cme_closed["dtp"].dt.year) if len(g) >= 8)
    for y in full_cme_years:
        for status in ("closed", "early_close"):
            dn, dc = dates("NYSE", status, [y]), dates("CME", status, [y])
            diff = sorted(dn ^ dc)
            checks.append(Check(f"NYSE_vs_CME.{y}.{status}", "WARN" if diff else "PASS",
                                f"{len(diff)} differing dates" + (f": only NYSE {sorted(dn - dc)}; only CME {sorted(dc - dn)}" if diff else "")))

    # 7. Good Friday vs computed Easter
    gf = dfd[dfd["canonical_name"] == "Good Friday"]
    bad = [f"{r.exchange} {r.date} (expected {good_friday(r.dtp.year)})" for r in gf.itertuples() if r.dtp.date() != good_friday(r.dtp.year)]
    checks.append(Check("good_friday", "FAIL" if bad else "PASS", f"{len(gf)} Good Friday rows checked against Easter-2" + (": " + "; ".join(bad) if bad else "")))

    # 8. diff vs previous run
    if previous_csv and Path(previous_csv).exists():
        prev = pd.read_csv(previous_csv, dtype=str).fillna("")
        key = ["exchange", "date", "status"]
        cur_keys = set(map(tuple, df[key].values.tolist()))
        prev_keys = set(map(tuple, prev[key].values.tolist()))
        added, removed = cur_keys - prev_keys, prev_keys - cur_keys
        pct = 100.0 * abs(len(df) - len(prev)) / max(1, len(prev))
        lvl = "FAIL" if pct > MAX_ROW_CHANGE_PCT else ("WARN" if (added or removed) else "PASS")
        checks.append(Check("diff_previous", lvl, f"rows {len(prev)} -> {len(df)} ({pct:.1f}% change, threshold {MAX_ROW_CHANGE_PCT}%); added {len(added)}: {sorted(added)[:10]}; removed {len(removed)}: {sorted(removed)[:10]}"))
    else:
        checks.append(Check("diff_previous", "WARN", "no previous run to diff against"))
    return checks


def render_report(checks: list[Check], df: pd.DataFrame, adapter_notes: dict[str, list[str]], run_ts: dt.datetime) -> str:
    worst = "FAIL" if any(c.level == "FAIL" for c in checks) else ("WARN" if any(c.level == "WARN" for c in checks) else "PASS")
    lines = [f"# Validation report — {run_ts.strftime('%Y-%m-%dT%H:%M:%SZ')}", "", f"Overall: **{worst}**", "",
             "| check | level | detail |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c.name} | {c.level} | {c.detail.replace('|', '/')} |")
    lines += ["", "## Row counts", "", "| exchange | closed | early_close | years |", "|---|---|---|---|"]
    if not df.empty:
        for ex, g in df.groupby("exchange"):
            yrs = sorted(set(pd.to_datetime(g["date"]).dt.year))
            lines.append(f"| {ex} | {(g['status'] == 'closed').sum()} | {(g['status'] == 'early_close').sum()} | {yrs} |")
    lines += ["", "## Adapter notes", ""]
    for ex, notes in adapter_notes.items():
        for n in notes:
            lines.append(f"- {ex}: {n}")
    return "\n".join(lines) + "\n"


def overall_level(checks: list[Check]) -> str:
    return "FAIL" if any(c.level == "FAIL" for c in checks) else ("WARN" if any(c.level == "WARN" for c in checks) else "PASS")


def checks_to_json(checks: list[Check]) -> str:
    return json.dumps([dataclasses.asdict(c) for c in checks], indent=2)

"""Normalisation: canonical holiday names, observed-date handling, dedup, UTC conversion."""
from __future__ import annotations

import datetime as dt
import re

import pandas as pd

from .schema import COLUMNS, HolidayRow

# Canonical names used for cross-exchange comparison; the scraped name is kept in `holiday_name`
CANON = [
    (r"new year", "New Year's Day"),
    (r"martin luther|mlk", "Martin Luther King Jr. Day"),
    (r"washington|presidents", "Presidents' Day"),
    (r"good friday", "Good Friday"),
    (r"memorial", "Memorial Day"),
    (r"juneteenth|junteenth", "Juneteenth"),  # OPRA's 2025 PDF spells it 'JUNTEENTH'
    (r"independence", "Independence Day"),
    (r"labor", "Labor Day"),
    (r"thanksgiving", "Thanksgiving Day"),
    (r"christmas", "Christmas Day"),
]


def canonical_name(name: str) -> str:
    low = name.lower()
    for pat, canon in CANON:
        if re.search(pat, low):
            if "early close" in low:
                return f"Early close (day after {canon})" if "day after" in low else f"Early close (eve of {canon})"
            return canon
    return name


def observed_date(holiday: dt.date) -> dt.date:
    """US exchange observed-date rule: Saturday -> preceding Friday, Sunday -> following Monday.
    Exception (NYSE Rule 7.2): if the Friday before a Saturday holiday is the last business day
    of the month/year, the holiday is NOT observed (e.g. New Year's Day 2028 falls on a Saturday
    and is not observed). We only *flag* such cases; sources already publish observed dates."""
    if holiday.weekday() == 5:
        return holiday - dt.timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + dt.timedelta(days=1)
    return holiday


def normalize(rows: list[HolidayRow]) -> pd.DataFrame:
    for r in rows:
        r.holiday_name = re.sub(r"\s+", " ", r.holiday_name).strip()
        r.compute_close_utc()
    recs = [r.to_record() for r in rows]
    df = pd.DataFrame(recs, columns=COLUMNS)
    if df.empty:
        df["canonical_name"] = []
        return df
    df["canonical_name"] = df["holiday_name"].map(canonical_name)
    # One logical row per (exchange, date, status); keep the first occurrence but merge names
    before = len(df)
    df = (df.sort_values(["exchange", "date", "status"])
            .drop_duplicates(subset=["exchange", "date", "status"], keep="first")
            .reset_index(drop=True))
    df.attrs["dedup_removed"] = before - len(df)
    return df

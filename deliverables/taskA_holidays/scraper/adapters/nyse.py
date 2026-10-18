"""NYSE holidays & early closes.

Source: https://www.nyse.com/markets/hours-calendars (301 -> /trade/hours-calendars).
Static HTML; one <table> with columns Holiday | <year> | <year> | <year> (currently 2026-2028).
Early closes are NOT table rows: they live in footnotes marked with * markers under the
table ("Each market will close early at 1:00 p.m. ... on Friday, November 27, 2026, ...").
A cell of "—*" means the holiday is not observed that year (e.g. New Year's Day 2028
falls on a Saturday) and yields no row.
"""
from __future__ import annotations

import datetime as dt
import re

from bs4 import BeautifulSoup

from .base import BaseAdapter

WEEKDAY_DATE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})")


class NyseAdapter(BaseAdapter):
    exchange = "NYSE"
    timezone = "America/New_York"
    source_url = "https://www.nyse.com/markets/hours-calendars"
    scope = "NYSE equities core session (9:30-16:00 ET); early-close footnotes also state 13:15 for eligible options"

    def scrape(self):
        body = self.fetch(self.source_url)
        return self.parse(body)

    def parse(self, body: bytes, **kw):
        soup = BeautifulSoup(body, "lxml")
        table = soup.find("table")
        if table is None:
            raise ValueError("NYSE: no <table> found on page (layout changed?)")
        rows_out = []
        header = [self.clean(th.get_text(" ")) for th in table.find_all("tr")[0].find_all(["th", "td"])]
        years = [int(h) for h in header[1:] if re.fullmatch(r"\d{4}", h)]
        if not years:
            raise ValueError(f"NYSE: could not read years from header {header}")
        for tr in table.find_all("tr")[1:]:
            cells = [self.clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if len(cells) < 1 + len(years):
                continue
            name = cells[0]
            for year, cell in zip(years, cells[1:1 + len(years)]):
                if not cell or cell.startswith("—") or cell.startswith("-"):
                    self.notes.append(f"NYSE {year}: '{name}' not observed ('{cell}')")
                    continue
                d = self.parse_month_day(cell, year)
                if d is None:
                    self.notes.append(f"NYSE {year}: could not parse date cell '{cell}' for '{name}'")
                    continue
                obs = "(observed)" if "observed" in cell.lower() else ""
                rows_out.append(self.row(d, f"{name} {obs}".strip(), "closed", year))
        closed_dates = {r.date: r.holiday_name for r in rows_out}

        # Footnotes: everything after the table that mentions an early close.
        # Keep the '*' markers here (self.clean would strip them) so we can split on them.
        tail = " ".join(x.strip() for x in table.find_all_next(string=True) if x.strip())
        tail = re.sub(r"\s+", " ", tail.replace("\xa0", " ").replace("’", "'"))
        tail = tail.split("Trading Hours")[0]  # footnotes end where the hours section starts
        footnotes = [s for s in re.split(r"(?<!\S)(?=\*{1,6}\s)", tail) if s.strip().startswith("*")]
        if not footnotes:
            self.notes.append("NYSE: no footnotes found under the table - early closes may be missing")
        for sent in footnotes:
            if "close early" not in sent.lower():
                continue
            tm = re.search(r"close early at\s+(\d{1,2}:\d{2}\s*[ap]\.?m\.?)", sent, re.I)
            close_t = self.parse_time(tm.group(1)) if tm else None
            # only the first sentence lists the dates ('... (the day after Thanksgiving).')
            sent_core = sent.split("All times are")[0]
            for m in WEEKDAY_DATE.finditer(sent_core):
                d = self.parse_month_day(f"{m.group(1)} {m.group(2)} {m.group(3)}", int(m.group(3)))
                if d is None or d.year not in years:
                    continue
                label = self._early_close_label(d, closed_dates, sent_core)
                rows_out.append(self.row(d, label, "early_close", d.year, close_local=close_t))
        return rows_out

    @staticmethod
    def _early_close_label(d: dt.date, closed: dict, sent: str) -> str:
        if "thanksgiving" in sent.lower():
            return "Early close (day after Thanksgiving)"
        for delta in (1, 2, 3, 4):
            nxt = d + dt.timedelta(days=delta)
            if nxt in closed:
                return f"Early close (eve of {closed[nxt].replace(' (observed)', '')})"
        return "Early close"

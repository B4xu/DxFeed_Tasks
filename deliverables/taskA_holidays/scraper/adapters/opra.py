"""OPRA (Options Price Reporting Authority) holiday schedule.

Official source: OPRA publishes a yearly "Holiday Schedule" notice as a PDF on
https://www.opraplan.com/ (files on cdn.opraplan.com/documents/notices/...). OCC
(theocc.com) is the clearing house, not the market-data authority, and its site
returns HTTP 403 to non-browser clients, so OPRA is used as the source of record.

The PDF is a one-page list:  "<HOLIDAY NAME> <MONTH D[, YYYY]>[*]" with footnotes such as
"* Each market will close 3 hours early on Friday, November 28, 2025 (the day after
Thanksgiving) and Wednesday, December 24, 2025". Options close 3 hours early relative
to the regular 16:00 ET close (16:15 for eligible ETF/index options), i.e. 13:00 ET.
Options markets otherwise follow the US equity holiday calendar.
"""
from __future__ import annotations

import datetime as dt
import io
import re

import pdfplumber
from bs4 import BeautifulSoup

from .base import BaseAdapter

INDEX_URL = "https://www.opraplan.com/"
HOLIDAY_LINK = re.compile(r"holiday[_\s-]*schedule", re.I)
REGULAR_CLOSE = dt.time(16, 0)
MONTH_LINE = re.compile(
    r"^(?P<name>[A-Z][A-Z'’\.\s]+?)\s+(?P<date>(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?)(?P<marks>\**)\s*$",
    re.I)
FOOT = re.compile(r"^(?P<marks>\*+)\s*(?P<text>.+)$")
DATE_IN_TEXT = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})", re.I)


class OpraAdapter(BaseAdapter):
    exchange = "OPRA"
    timezone = "America/New_York"
    source_url = INDEX_URL
    scope = "US listed options (all OPRA participant exchanges); early close = 3h before 16:00 ET regular close (16:15 eligible options -> 13:15)"

    def discover_pdfs(self, min_year: int) -> dict[int, str]:
        body = self.fetch(INDEX_URL)
        soup = BeautifulSoup(body, "lxml")
        found: dict[int, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)
            if not (HOLIDAY_LINK.search(href) or HOLIDAY_LINK.search(text)):
                continue
            m = re.search(r"(20\d{2})", href) or re.search(r"(20\d{2})", text)
            if not m:
                continue
            y = int(m.group(1))
            if y >= min_year:
                found[y] = href if href.startswith("http") else "https://www.opraplan.com" + href
        return found

    def scrape(self, min_year: int | None = None):
        min_year = min_year or (self.run_ts.year - 1)
        pdfs = self.discover_pdfs(min_year)
        if not pdfs:
            raise ValueError(f"OPRA: no holiday-schedule PDF links found for year >= {min_year}")
        self.notes.append(f"OPRA PDFs discovered: {pdfs}")
        rows = []
        for y, url in sorted(pdfs.items()):
            body = self.fetch(url, min_delay=1.0)
            rows.extend(self.parse(body, year=y, url=url))
        return rows

    def parse(self, body: bytes, year: int = 0, url: str = "", **kw):
        with pdfplumber.open(io.BytesIO(body)) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        lines = [self.clean_keep_marks(l) for l in text.splitlines() if l.strip()]
        if not year:
            m = re.search(r"(20\d{2})\s+HOLIDAY SCHEDULE", text, re.I)
            year = int(m.group(1)) if m else self.run_ts.year
        rows = []
        marks_by_date: dict[str, dt.date] = {}
        # join wrapped footnote lines: a line that does not start with '*' and follows a footnote continues it
        foot_lines: list[str] = []
        for l in lines:
            if FOOT.match(l):
                foot_lines.append(l)
            elif foot_lines and not MONTH_LINE.match(l) and "HOLIDAY SCHEDULE" not in l.upper():
                foot_lines[-1] += " " + l
        for l in lines:
            m = MONTH_LINE.match(l)
            if not m:
                continue
            d = self.parse_month_day(m.group("date"), year)
            if d is None:
                continue
            name = self.clean(m.group("name")).title().replace("'S", "'s")
            rows.append(self.row(d, name, "closed", year, url=url or self.source_url))
            if m.group("marks"):
                marks_by_date[m.group("marks")] = d
        for fl in foot_lines:
            fm = FOOT.match(fl)
            if not fm:
                continue
            txt = fm.group("text")
            hours = re.search(r"close\s+(\d+)\s+hours?\s+early", txt, re.I)
            if hours:
                h = int(hours.group(1))
                close_local = (dt.datetime.combine(dt.date(2000, 1, 1), REGULAR_CLOSE) - dt.timedelta(hours=h)).time()
            else:
                tm = re.search(r"(\d{1,2}:\d{2}\s*[ap]\.?m\.?)", txt, re.I)
                close_local = self.parse_time(tm.group(1)) if tm else None
            for dm in DATE_IN_TEXT.finditer(txt):
                d = self.parse_month_day(dm.group(1), year)
                if d is None:
                    continue
                label = "Early close (day after Thanksgiving)" if "thanksgiving" in txt.lower() and d.month == 11 else self._eve_label(d, rows)
                rows.append(self.row(d, label, "early_close", year, close_local=close_local, url=url or self.source_url))
        if not any(r.status == "closed" for r in rows):
            raise ValueError("OPRA: parsed zero closure rows from PDF")
        return rows

    @staticmethod
    def clean_keep_marks(s: str) -> str:
        return re.sub(r"\s+", " ", s.replace("\xa0", " ").replace("’", "'")).strip()

    @staticmethod
    def _eve_label(d, rows):
        closed = {r.date: r.holiday_name for r in rows if r.status == "closed"}
        for delta in (1, 2, 3, 4):
            if d + dt.timedelta(days=delta) in closed:
                return f"Early close (eve of {closed[d + dt.timedelta(days=delta)]})"
        return "Early close"

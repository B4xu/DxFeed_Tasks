"""CME Group holiday calendar.

Scope decision: CME Globex **US Equity Index futures and options** (ES, NQ, YM, RTY ...),
because the CME holiday schedule differs by product group (equity index, interest rates,
FX, energy, metals, agriculturals) and by venue (Globex vs ClearPort vs floor), so a
single "CME calendar" does not exist. Equity index futures typically trade a shortened
session (early close 12:00 CT) on US holidays rather than closing fully; a full closure
("Halt") usually spans Good Friday and Christmas/New Year in Globex.

Access decision: cmegroup.com returns HTTP 403 with the message "This IP address is
blocked due to suspected web scraping ... Use of scripts ... is strictly prohibited by
CME Group's website Data Terms of Use" for every URL including /robots.txt. Because the
Terms of Use explicitly forbid automated access, this adapter does **not** attempt to
bypass the block (no Playwright, no UA spoofing). Instead it reads operator-downloaded
files from `input/cme/`:

  * `*.csv`  with header `date,holiday_name,status,close_time_local,product_scope,source_url`
             (status in {closed, early_close}; close_time_local HH:MM Chicago time), or
  * `*.pdf`  the per-holiday PDFs CME publishes under
             https://www.cmegroup.com/tools-information/holiday-calendar.html ->
             the adapter dumps their text into the raw folder and tries a best-effort line
             parse ("<Product group> ... <date> ... <Halt|Early Close HH:MM>"). Lines it
             cannot parse are listed in the validation report, never guessed, or
  * `*.xlsx` Trading Hours → Holidays "Download data" exports (one file per holiday).
             Only the **Equities** asset-class row is used (matches the scope above).

If `input/cme/` is empty, the adapter returns zero rows with a MANUAL_INPUT_REQUIRED note
and the run is marked WARN (not FAIL) for CME only.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from pathlib import Path

import openpyxl
import pdfplumber

from .base import BaseAdapter

DATE_RE = re.compile(
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
    re.I,
)
TIME_RE = re.compile(r"(\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?)", re.I)
EVENT_RE = re.compile(
    r"(\d{1,2}:\d{2})\s+Trade Date:\s+(\d{4}-\d{2}-\d{2})\s+\(([A-Z]+)\)"
)

# Filename token → holiday display name (longest / most specific first).
_NAME_TOKENS = (
    ("martin_luther", "Martin Luther King Jr. Day"),
    ("new_year", "New Year's Day"),
    ("president", "Presidents' Day"),
    ("good_friday", "Good Friday"),
    ("memorial", "Memorial Day"),
    ("juneteenth", "Juneteenth"),
    ("indepedence", "Independence Day"),  # common typo in downloads
    ("independence", "Independence Day"),
    ("labor", "Labor Day"),
    ("thanksgiving", "Thanksgiving Day"),
    ("christmas", "Christmas Day"),
)


class CmeAdapter(BaseAdapter):
    exchange = "CME"
    timezone = "America/Chicago"
    source_url = "https://www.cmegroup.com/trading-hours.html"
    scope = "CME Globex US Equity Index futures & options (ES, NQ, YM, RTY)"

    def __init__(self, raw_root: Path, run_ts=None, session=None, input_dir: Path | None = None):
        super().__init__(raw_root, run_ts, session)
        self.input_dir = Path(input_dir) if input_dir else Path(raw_root).parent / "input" / "cme"

    def scrape(self):
        exts = {".csv", ".pdf", ".xlsx"}
        files = (
            sorted(p for p in self.input_dir.glob("*") if p.suffix.lower() in exts and p.name != "README.md")
            if self.input_dir.exists()
            else []
        )
        if not files:
            self.notes.append(
                "CME: MANUAL_INPUT_REQUIRED - cmegroup.com blocks automated clients (HTTP 403) and its Data "
                f"Terms of Use prohibit scraping. Download Trading Hours Holidays xlsx/CSV/PDF into {self.input_dir}."
            )
            return []
        rows = []
        for p in files:
            body = p.read_bytes()
            self._save_raw(f"file://{p.name}", body)
            suf = p.suffix.lower()
            if suf == ".csv":
                rows.extend(self.parse_csv(body, src=p.name))
            elif suf == ".xlsx":
                rows.extend(self.parse_xlsx(body, src=p.name))
            else:
                rows.extend(self.parse(body, src=p.name))
        # Deduplicate across overlapping downloads (same date+status).
        seen: set[tuple[dt.date, str]] = set()
        out = []
        for r in sorted(rows, key=lambda x: (x.date, x.status, x.holiday_name)):
            key = (r.date, r.status)
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        self.notes.append(f"CME: parsed {len(out)} rows from {len(files)} input file(s)")
        return out

    def parse_csv(self, body: bytes, src: str = "manual.csv"):
        out = []
        for rec in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
            d = dt.date.fromisoformat(rec["date"].strip())
            status = rec["status"].strip().lower()
            t = self.parse_time(rec.get("close_time_local", "")) if status == "early_close" else None
            out.append(
                self.row(
                    d,
                    rec["holiday_name"],
                    status,
                    d.year,
                    close_local=t,
                    scope=rec.get("product_scope") or self.scope,
                    url=rec.get("source_url") or f"{self.source_url} (manual download: {src})",
                )
            )
        return out

    def parse_xlsx(self, body: bytes, src: str = "manual.xlsx"):
        """Parse a Trading Hours → Holidays Excel export.

        Layout: row "Asset Class" with calendar dates as column headers; one row per
        asset class. We only use **Equities**. For each weekday column:

        * empty cell → full close on that calendar day
        * CLOSED before 16:00 on that trade date → early_close at that time
        * only PREOPEN/OPEN for a *different* trade date → closed (no session for
          the holiday's own trade date), e.g. Thanksgiving / Monday US holidays
        """
        wb = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
        ws = wb.active
        header_dates: list[dt.date] = []
        equities: list[str] = []
        for row in ws.iter_rows(values_only=True):
            if not row or row[0] is None:
                continue
            key = str(row[0]).strip()
            if key == "Asset Class":
                header_dates = []
                for c in row[1:]:
                    if c is None or (isinstance(c, str) and not c.strip()):
                        continue
                    if isinstance(c, dt.datetime):
                        header_dates.append(c.date())
                    elif isinstance(c, dt.date):
                        header_dates.append(c)
                    else:
                        header_dates.append(dt.date.fromisoformat(str(c)[:10]))
            elif key == "Equities" and header_dates:
                equities = [(c or "") if not isinstance(c, str) else c for c in row[1 : 1 + len(header_dates)]]
                equities = [str(c) if c is not None else "" for c in equities]
        if not header_dates or not equities:
            self.notes.append(f"CME {src}: no Equities row / date header — skipped")
            return []

        holiday_name = self._holiday_name_from_file(src, header_dates)
        out = []
        for cal_date, cell in zip(header_dates, equities):
            if cal_date.weekday() >= 5:
                continue
            classified = self._classify_equities_cell(cal_date, cell or "")
            if classified is None:
                continue
            status, close_local = classified
            name = holiday_name
            if status == "early_close" and cal_date != self._primary_holiday_date(header_dates, holiday_name):
                # e.g. Friday after Thanksgiving, Christmas Eve
                name = f"{holiday_name} (early close)"
            out.append(
                self.row(
                    cal_date,
                    name,
                    status,
                    cal_date.year,
                    close_local=close_local,
                    url=f"{self.source_url} (manual download: {src})",
                )
            )
        if not out:
            self.notes.append(f"CME {src}: Equities row produced zero holiday rows")
        return out

    @staticmethod
    def _holiday_name_from_file(src: str, dates: list[dt.date]) -> str:
        key = src.lower().replace("-", "_").replace(" ", "_")
        for token, label in _NAME_TOKENS:
            if token in key:
                return label
        # Untitled download (Trading-Hours-Holiday.xlsx): infer from November Thanksgiving.
        for d in dates:
            if d.month == 11 and d.weekday() == 3:  # Thursday in November
                return "Thanksgiving Day"
        return "Holiday"

    @staticmethod
    def _primary_holiday_date(dates: list[dt.date], name: str) -> dt.date | None:
        """Best guess at the named holiday date inside the 3–4 day window."""
        weekdays = [d for d in dates if d.weekday() < 5]
        if not weekdays:
            return None
        low = name.lower()
        if "thanksgiving" in low:
            for d in weekdays:
                if d.month == 11 and d.weekday() == 3:
                    return d
        if "christmas" in low:
            for d in weekdays:
                if d.month == 12 and d.day == 25:
                    return d
            for d in weekdays:
                if d.month == 12 and d.day == 24:
                    return d
        if "new year" in low:
            for d in weekdays:
                if d.month == 1 and d.day == 1:
                    return d
        # Middle weekday column is usually the holiday in CME's 3-day export.
        return weekdays[len(weekdays) // 2]

    def _classify_equities_cell(self, cal_date: dt.date, cell: str):
        text = cell.strip()
        if not text:
            return ("closed", None)
        events = []
        for tm, td, st in EVENT_RE.findall(text):
            hh, mm = tm.split(":")
            events.append((dt.time(int(hh), int(mm)), dt.date.fromisoformat(td), st))
        if not events:
            self.notes.append(f"CME Equities {cal_date}: unparsed cell {text!r}")
            return None
        own_closed = [tm for tm, td, st in events if td == cal_date and st == "CLOSED"]
        if own_closed:
            t = min(own_closed)
            if t < dt.time(16, 0):
                return ("early_close", t)
            # 16:00 CLOSE on this calendar day is the normal Globex daily close, not a holiday row.
            return None
        # Session activity only for other trade dates → this calendar day has no equity session.
        if all(td != cal_date or st in ("PREOPEN", "OPEN", "PAUSED", "PCP") for tm, td, st in events):
            if not any(td == cal_date and st == "OPEN" for tm, td, st in events):
                return ("closed", None)
        return None

    def parse(self, body: bytes, src: str = "manual.pdf", **kw):
        """Best-effort parser for CME per-holiday PDFs. Only lines that contain a full date and
        either 'halt'/'closed' or 'early close'/a time are turned into rows; everything else is
        recorded in notes so a human can check."""
        with pdfplumber.open(io.BytesIO(body)) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        self._save_raw(f"file://{src}.txt", text.encode())
        title = next((l for l in text.splitlines() if l.strip()), src)
        out = []
        for line in text.splitlines():
            l = self.clean(line)
            dm = DATE_RE.search(l)
            if not dm or not re.search(r"equity", l, re.I) and not re.search(r"equity", title, re.I):
                continue
            d = self.parse_month_day(dm.group(1), 0)
            if d is None:
                continue
            low = l.lower()
            if "halt" in low or "closed" in low:
                out.append(self.row(d, title, "closed", d.year, url=f"{self.source_url} ({src})"))
            elif "early" in low or TIME_RE.search(l):
                tm = TIME_RE.search(l)
                out.append(
                    self.row(
                        d,
                        f"{title} (early close)",
                        "early_close",
                        d.year,
                        close_local=self.parse_time(tm.group(1)) if tm else None,
                        url=f"{self.source_url} ({src})",
                    )
                )
            else:
                self.notes.append(f"CME {src}: unparsed line '{l}'")
        if not out:
            self.notes.append(f"CME {src}: parsed zero rows - check raw text dump")
        return out

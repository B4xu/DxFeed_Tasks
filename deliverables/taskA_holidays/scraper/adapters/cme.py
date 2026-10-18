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
             cannot parse are listed in the validation report, never guessed.

If `input/cme/` is empty, the adapter returns zero rows with a MANUAL_INPUT_REQUIRED note
and the run is marked WARN (not FAIL) for CME only.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from pathlib import Path

import pdfplumber

from .base import BaseAdapter

DATE_RE = re.compile(r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})", re.I)
TIME_RE = re.compile(r"(\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?)", re.I)


class CmeAdapter(BaseAdapter):
    exchange = "CME"
    timezone = "America/Chicago"
    source_url = "https://www.cmegroup.com/tools-information/holiday-calendar.html"
    scope = "CME Globex US Equity Index futures & options (ES, NQ, YM, RTY)"

    def __init__(self, raw_root: Path, run_ts=None, session=None, input_dir: Path | None = None):
        super().__init__(raw_root, run_ts, session)
        self.input_dir = Path(input_dir) if input_dir else Path(raw_root).parent / "input" / "cme"

    def scrape(self):
        files = sorted(p for p in self.input_dir.glob("*") if p.suffix.lower() in (".csv", ".pdf")) if self.input_dir.exists() else []
        if not files:
            self.notes.append(
                "CME: MANUAL_INPUT_REQUIRED - cmegroup.com blocks automated clients (HTTP 403) and its Data "
                f"Terms of Use prohibit scraping. Download the equity-index holiday PDFs/CSV manually into {self.input_dir}.")
            return []
        rows = []
        for p in files:
            body = p.read_bytes()
            self._save_raw(f"file://{p.name}", body)
            if p.suffix.lower() == ".csv":
                rows.extend(self.parse_csv(body, src=p.name))
            else:
                rows.extend(self.parse(body, src=p.name))
        return rows

    def parse_csv(self, body: bytes, src: str = "manual.csv"):
        out = []
        for rec in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
            d = dt.date.fromisoformat(rec["date"].strip())
            status = rec["status"].strip().lower()
            t = self.parse_time(rec.get("close_time_local", "")) if status == "early_close" else None
            out.append(self.row(d, rec["holiday_name"], status, d.year, close_local=t,
                                scope=rec.get("product_scope") or self.scope,
                                url=rec.get("source_url") or f"{self.source_url} (manual download: {src})"))
        return out

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
                out.append(self.row(d, f"{title} (early close)", "early_close", d.year,
                                    close_local=self.parse_time(tm.group(1)) if tm else None,
                                    url=f"{self.source_url} ({src})"))
            else:
                self.notes.append(f"CME {src}: unparsed line '{l}'")
        if not out:
            self.notes.append(f"CME {src}: parsed zero rows - check raw text dump")
        return out

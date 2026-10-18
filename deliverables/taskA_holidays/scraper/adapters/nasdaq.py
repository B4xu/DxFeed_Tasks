"""NASDAQ holidays & early closes.

Sources, tried in order:

1. Nasdaq Trader (official market-operations site):
   https://www.nasdaqtrader.com/trader.aspx?id=Calendar
   Static HTML, one <table> with columns  <year> | Holiday | Status, e.g.
   "November 27, 2026 | Early Close* - U.S. | 1:00 p.m.".  The '*' refers to a footnote
   below the table (alerts are sent for early-close days). Only the current year is shown.
   During reconnaissance this host once answered with an Incapsula JavaScript challenge
   (212-byte stub); a later request with a normal browser User-Agent returned the page.
2. nasdaq.com public page (fallback, needs a real browser):
   https://www.nasdaq.com/market-activity/stock-market-holiday-schedule
   Requests from `requests`/curl are reset or time out (HTTP/2 INTERNAL_ERROR / ReadTimeout),
   i.e. the site rejects non-browser clients. We therefore load it once with headless
   Chromium via Playwright (no stealth, no header spoofing), save the rendered HTML and
   parse the table Holiday | Date | Market Status.

If every source fails the adapter logs an ERROR and returns zero rows; the pipeline keeps
running and the validation report flags NASDAQ as missing.

Network policy for this adapter: connect timeout 10 s, read timeout 10 s, at most 2 retries
(exponential backoff + jitter) on 429/5xx, and no retry on connection resets/timeouts.
"""
from __future__ import annotations

import datetime as dt
import logging
import re

from bs4 import BeautifulSoup

from .base import BaseAdapter, FetchError

log = logging.getLogger("holidays")

NASDAQTRADER_URL = "https://www.nasdaqtrader.com/trader.aspx?id=Calendar"
NASDAQ_COM_URL = "https://www.nasdaq.com/market-activity/stock-market-holiday-schedule"
TIMEOUT = (10.0, 10.0)


class NasdaqAdapter(BaseAdapter):
    exchange = "NASDAQ"
    timezone = "America/New_York"
    source_url = NASDAQTRADER_URL
    scope = "The Nasdaq Stock Market regular session (9:30-16:00 ET)"

    # ------------------------------------------------------------ sources
    def scrape(self):
        errors = []
        # 1. nasdaqtrader.com with plain requests
        try:
            body = self.fetch(NASDAQTRADER_URL, retries=2, timeout=TIMEOUT, retry_on_connection_error=False)
            rows = self.parse(body, url=NASDAQTRADER_URL)
            log.info("NASDAQ: source nasdaqtrader.com succeeded with %d rows", len(rows))
            self.notes.append(f"source=nasdaqtrader.com rows={len(rows)}")
            return rows
        except (FetchError, ValueError) as e:
            errors.append(f"nasdaqtrader.com: {e}")
            log.warning("NASDAQ: nasdaqtrader.com failed: %s", e)
        # 2. nasdaq.com rendered by a real browser
        try:
            body = self._fetch_with_playwright(NASDAQ_COM_URL)
            rows = self.parse(body, url=NASDAQ_COM_URL)
            log.info("NASDAQ: source nasdaq.com (Playwright) succeeded with %d rows", len(rows))
            self.notes.append(f"source=nasdaq.com(playwright) rows={len(rows)}")
            return rows
        except Exception as e:  # noqa: BLE001
            errors.append(f"nasdaq.com(playwright): {e!r}")
            log.warning("NASDAQ: nasdaq.com via Playwright failed: %r", e)
        log.error("NASDAQ: all sources failed: %s", " | ".join(errors))
        self.notes.append("SOURCE_UNAVAILABLE: " + " | ".join(errors))
        return []

    def _fetch_with_playwright(self, url: str) -> bytes:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise RuntimeError("playwright not installed (pip install playwright && playwright install chromium)") from e
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector("table", timeout=20_000)
            html = page.content()
            browser.close()
        body = html.encode("utf-8")
        self._save_raw(url, body, suffix=".rendered.html")
        return body

    # ------------------------------------------------------------- parsing
    def parse(self, body: bytes, url: str = NASDAQTRADER_URL, **kw):
        soup = BeautifulSoup(body, "lxml")
        table, layout = None, None
        for t in soup.find_all("table"):
            first = [self.clean(c.get_text(" ")).lower() for c in t.find_all("tr")[0].find_all(["th", "td"])] if t.find_all("tr") else []
            if len(first) >= 3 and first[1] == "holiday" and first[2] == "status" and re.fullmatch(r"\d{4}", first[0]):
                table, layout = t, "nasdaqtrader"          # <year> | Holiday | Status
                break
            if len(first) >= 3 and first[0] == "holiday" and first[1] == "date" and "status" in first[2]:
                table, layout = t, "nasdaq.com"            # Holiday | Date | Market Status
                break
        if table is None:
            raise ValueError("NASDAQ: holiday table not found (layout changed or challenge page)")
        out = []
        for tr in table.find_all("tr")[1:]:
            cells = [self.clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            if layout == "nasdaqtrader":
                date_txt, name, status_txt = cells[0], cells[1], cells[2]
            else:
                name, date_txt, status_txt = cells[0], cells[1], cells[2]
            m = re.search(r"(\d{4})", date_txt)
            if not m:
                self.notes.append(f"NASDAQ: no year in '{date_txt}'")
                continue
            year = int(m.group(1))
            d = self.parse_month_day(date_txt, year)
            if d is None:
                self.notes.append(f"NASDAQ: unparsable date '{date_txt}'")
                continue
            name = re.sub(r"\s*-\s*U\.S\.\s*", " ", name).strip()      # 'Labor Day - U.S.' -> 'Labor Day'
            name = re.sub(r"\s+", " ", name)
            if status_txt.lower().startswith("closed"):
                out.append(self.row(d, name, "closed", year, url=url))
            else:
                t = self.parse_time(status_txt)
                if t is None:
                    self.notes.append(f"NASDAQ: early close without parsable time '{status_txt}' on {d}")
                out.append(self.row(d, name, "early_close", year, close_local=t, url=url))
        # second pass: give generic "Early Close" rows a descriptive label now that all closures are known
        for r in out:
            if r.status == "early_close" and r.holiday_name.lower().startswith("early close"):
                r.holiday_name = self._label(r.date, out)
        if not out:
            raise ValueError("NASDAQ: table found but zero rows parsed")
        return out

    @staticmethod
    def _label(d: dt.date, rows) -> str:
        closed = {r.date: r.holiday_name for r in rows if r.status == "closed"}
        prev = closed.get(d - dt.timedelta(days=1), "")
        if "thanksgiving" in prev.lower():
            return "Early close (day after Thanksgiving)"
        for delta in (1, 2, 3, 4):
            if d + dt.timedelta(days=delta) in closed:
                return f"Early close (eve of {closed[d + dt.timedelta(days=delta)]})"
        return "Early close"

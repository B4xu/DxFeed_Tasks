"""Base adapter: polite HTTP fetch with retries/backoff and raw snapshotting."""
from __future__ import annotations

import datetime as dt
import logging
import random
import re
import time
from pathlib import Path

import requests

from ..schema import HolidayRow

log = logging.getLogger("holidays")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 holiday-calendar-bot/0.1")

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}


class FetchError(RuntimeError):
    pass


class BaseAdapter:
    exchange: str = ""
    timezone: str = "America/New_York"
    source_url: str = ""
    scope: str = ""

    def __init__(self, raw_root: Path, run_ts: dt.datetime | None = None, session: requests.Session | None = None):
        self.run_ts = run_ts or dt.datetime.now(dt.timezone.utc)
        self.raw_dir = Path(raw_root) / self.exchange.lower() / self.run_ts.strftime("%Y%m%dT%H%M%SZ")
        self.session = session or requests.Session()
        # Browser-like headers: nasdaq.com (Akamai) never answers a bare python-requests
        # header set (read timeout), but responds in ~3 s with Accept/Accept-Language present.
        self.session.headers.setdefault("User-Agent", UA)
        self.session.headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        self.session.headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        self.notes: list[str] = []

    # ------------------------------------------------------------- fetching
    def fetch(self, url: str, retries: int = 4, timeout: float | tuple[float, float] = 30.0,
              min_delay: float = 0.0, retry_on_connection_error: bool = True) -> bytes:
        """GET with exponential backoff (2^n + jitter). Stops on 403 (bot block) immediately,
        retries 429/5xx and (optionally) network errors. `timeout` may be a (connect, read)
        tuple. With retry_on_connection_error=False a connection reset / read timeout is
        treated as "the server rejects this client" and is not retried.
        Saves raw body under raw/<exchange>/<ts>/."""
        last: Exception | None = None
        for attempt in range(1, retries + 1):
            if min_delay:
                time.sleep(min_delay)
            try:
                r = self.session.get(url, timeout=timeout)
                log.info("GET %s -> %s (%d bytes)", url, r.status_code, len(r.content))
                if r.status_code == 200:
                    self._save_raw(url, r.content)
                    return r.content
                if r.status_code in (401, 403, 404):
                    self._save_raw(url, r.content, suffix=f".http{r.status_code}")
                    raise FetchError(f"{url} returned HTTP {r.status_code} (not retried)")
                if r.status_code == 429 or r.status_code >= 500:
                    ra = r.headers.get("Retry-After")
                    delay = float(ra) if ra and ra.isdigit() else (2 ** attempt) + random.uniform(0, 1)
                    log.warning("HTTP %s on %s, retry in %.1fs", r.status_code, url, delay)
                    last = FetchError(f"HTTP {r.status_code}")
                    time.sleep(delay)
                    continue
                raise FetchError(f"{url} unexpected HTTP {r.status_code}")
            except requests.RequestException as e:
                last = e
                if not retry_on_connection_error:
                    raise FetchError(f"{url}: {e!r} (connection error, not retried)") from e
                delay = (2 ** attempt) + random.uniform(0, 1)
                log.warning("network error on %s: %r, retry in %.1fs", url, e, delay)
                time.sleep(delay)
        raise FetchError(f"giving up on {url}: {last!r}")

    def _save_raw(self, url: str, body: bytes, suffix: str = "") -> Path:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("//", 1)[-1])[:150] + suffix
        p = self.raw_dir / name
        p.write_bytes(body)
        return p

    # ---------------------------------------------------------------- utils
    @staticmethod
    def clean(s: str) -> str:
        s = s.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
        s = re.sub(r"[\*†‡]+", "", s)           # footnote markers
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def parse_month_day(text: str, year: int) -> dt.date | None:
        """'Friday, April 3' / 'April 3, 2026' / 'JANUARY 1, 2025' / 'July 3rd' -> date."""
        t = text.lower().replace(",", " ")
        t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
        m = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:\s+(\d{4}))?", t)
        if not m:
            return None
        y = int(m.group(3)) if m.group(3) else year
        return dt.date(y, MONTHS[m.group(1)], int(m.group(2)))

    @staticmethod
    def parse_time(text: str) -> dt.time | None:
        """'1:00 p.m.' / '1:00 pm' / '13:00' / '12:15 p.m.' -> time."""
        t = text.lower().replace(".", "").replace(" ", "")
        m = re.search(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", t)
        if not m:
            return None
        h = int(m.group(1)); mi = int(m.group(2) or 0)
        if m.group(3) == "pm" and h < 12:
            h += 12
        if m.group(3) == "am" and h == 12:
            h = 0
        return dt.time(h, mi)

    def row(self, date: dt.date, name: str, status: str, year: int, close_local: dt.time | None = None,
            scope: str | None = None, url: str | None = None) -> HolidayRow:
        return HolidayRow(exchange=self.exchange, date=date, holiday_name=self.clean(name), status=status,  # type: ignore[arg-type]
                          timezone=self.timezone, source_url=url or self.source_url, scraped_at_utc=self.run_ts,
                          source_year=year, session_or_product_scope=scope if scope is not None else self.scope,
                          close_time_local=close_local)

    # ----------------------------------------------------------------- api
    def scrape(self) -> list[HolidayRow]:  # pragma: no cover - abstract
        raise NotImplementedError

    def parse(self, body: bytes, **kw) -> list[HolidayRow]:  # pragma: no cover - abstract
        raise NotImplementedError

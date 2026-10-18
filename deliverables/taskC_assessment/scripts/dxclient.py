"""Small, polite client for the public dxFeed demo REST web service.

Every request is logged (UTC timestamp, full URL, latency, HTTP status, body size,
dxFeed `status` field) to a JSONL request log so that any number in the report
can be traced back to a concrete call. Raw bodies can optionally be saved.

Endpoint discovered from https://tools.dxfeed.com/webservice/rest/help
(which redirects to https://demo.dxfeed.com/webservice/rest/help).
Candle symbol syntax from
https://docs.dxfeed.com/dxfeed/api/com/dxfeed/event/candle/CandleSymbol.html
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import requests

BASE = "https://demo.dxfeed.com/webservice/rest"
EVENTS_URL = f"{BASE}/events.json"
SSE_URL = f"{BASE}/eventSource"
UA = "dxfeed-l2-assessment/0.1 (+polite; single client; contact via report)"

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "evidence"


def read_json(path: Path) -> Any:
    """Read a JSON evidence file, falling back to its gzipped copy (``<name>.gz``)."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text())
    gz = path.with_name(path.name + ".gz")
    with gzip.open(gz, "rt") as f:
        return json.load(f)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(ts: dt.datetime | None = None) -> str:
    return (ts or utcnow()).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def ms_to_iso(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class DxClient:
    """Synchronous client with request logging, retries and backoff.

    Stops (raises) after `max_consecutive_failures` consecutive 429/5xx/network
    errors so that a misbehaving loop never hammers the shared demo service.
    """

    def __init__(self, log_path: Path, raw_dir: Path | None = None,
                 timeout: float = 30.0, max_consecutive_failures: int = 3,
                 min_interval_s: float = 0.0):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(raw_dir) if raw_dir else None
        if self.raw_dir:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_consecutive_failures = max_consecutive_failures
        self.min_interval_s = min_interval_s
        self._last_call = 0.0
        self._consecutive_failures = 0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA

    # ------------------------------------------------------------------ core
    def get(self, params: dict[str, Any], tag: str = "", save_raw: bool = False,
            retries: int = 3) -> dict[str, Any]:
        """GET events.json. Returns dict with keys: ok, status_code, dx_status,
        data (parsed JSON or None), latency_s, url, requested_at, raw_path."""
        attempt = 0
        while True:
            attempt += 1
            # politeness: minimum spacing between calls
            wait = self.min_interval_s - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            rec: dict[str, Any] = {"requested_at": iso(), "tag": tag, "attempt": attempt,
                                   "params": params}
            t0 = time.perf_counter()
            try:
                r = self.session.get(EVENTS_URL, params=params, timeout=self.timeout)
                lat = time.perf_counter() - t0
                self._last_call = time.monotonic()
                rec.update(url=r.url, status_code=r.status_code, latency_s=round(lat, 4),
                           bytes=len(r.content),
                           headers={k: v for k, v in r.headers.items()
                                    if k.lower() in ("date", "server", "cache-control", "age",
                                                     "etag", "retry-after", "x-ratelimit-limit",
                                                     "x-ratelimit-remaining", "x-origin-nginx",
                                                     "content-encoding", "via", "x-cache")})
                data = None
                try:
                    data = r.json()
                except ValueError:
                    rec["json_error"] = True
                rec["dx_status"] = data.get("status") if isinstance(data, dict) else None
                rec["body_sha1"] = hashlib.sha1(r.content).hexdigest()
                if save_raw and self.raw_dir is not None:
                    name = f"{rec['requested_at'].replace(':', '').replace('.', '_')}_{tag or 'req'}_{rec['body_sha1'][:8]}.json"
                    p = self.raw_dir / name
                    p.write_bytes(r.content)
                    rec["raw_path"] = str(p.relative_to(EVIDENCE)) if p.is_relative_to(EVIDENCE) else str(p)
                self._log(rec)
                if r.status_code == 429 or r.status_code >= 500:
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self.max_consecutive_failures:
                        raise RuntimeError(f"Stopping: {self._consecutive_failures} consecutive {r.status_code} responses")
                    if attempt <= retries:
                        self._backoff(attempt, r.headers.get("Retry-After"))
                        continue
                else:
                    self._consecutive_failures = 0
                return {"ok": r.status_code == 200 and data is not None, "status_code": r.status_code,
                        "dx_status": rec["dx_status"], "data": data, "latency_s": lat, "url": r.url,
                        "requested_at": rec["requested_at"], "raw_path": rec.get("raw_path"),
                        "bytes": len(r.content), "body_sha1": rec["body_sha1"]}
            except (requests.RequestException,) as e:
                lat = time.perf_counter() - t0
                self._last_call = time.monotonic()
                rec.update(error=repr(e), latency_s=round(lat, 4))
                self._log(rec)
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.max_consecutive_failures:
                    raise RuntimeError(f"Stopping: {self._consecutive_failures} consecutive network errors: {e!r}")
                if attempt <= retries:
                    self._backoff(attempt)
                    continue
                return {"ok": False, "status_code": None, "dx_status": None, "data": None,
                        "latency_s": lat, "url": None, "requested_at": rec["requested_at"],
                        "error": repr(e)}

    # --------------------------------------------------------------- helpers
    def candles(self, symbol: str, period: str, from_time: str, to_time: str | None = None,
                tag: str = "", save_raw: bool = True, extra_attrs: str = "") -> dict[str, Any]:
        """Fetch Candle events. `symbol` is the base symbol, `period` like '1m', '5m', '1h'.
        extra_attrs e.g. ',price=bid' for FX (required on the demo for FX pairs)."""
        csym = f"{symbol}{{={period}{extra_attrs}}}"
        params = {"events": "Candle", "symbols": csym, "fromTime": from_time}
        if to_time:
            params["toTime"] = to_time
        res = self.get(params, tag=tag or f"candles_{symbol}_{period}", save_raw=save_raw)
        rows = []
        if res["ok"] and isinstance(res["data"], dict):
            cmap = res["data"].get("Candle", {}) or {}
            # the server normalises the symbol (e.g. {=1m} -> {=m}); take whatever key it returns
            for _k, lst in cmap.items():
                rows.extend(lst)
        res["candles"] = rows
        res["candle_symbol_requested"] = csym
        return res

    def quotes(self, symbols: list[str], tag: str = "quotes", save_raw: bool = False) -> dict[str, Any]:
        return self.get({"events": "Quote", "symbols": ",".join(symbols)}, tag=tag, save_raw=save_raw)

    def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after and retry_after.isdigit():
            delay = float(retry_after)
        else:
            delay = min(60.0, (2 ** attempt) + random.uniform(0, 1))
        time.sleep(delay)

    def _log(self, rec: dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")


# Instruments chosen for the assessment (see report.md, Part 1, for justification).
INSTRUMENTS = {
    # key: (base symbol, extra candle attrs, asset class, note)
    "AAPL": ("AAPL", "", "us_stock", "Most liquid US stock; RTH 13:30-20:00Z, ETH 08:00-00:00Z"),
    "EURUSD": ("EUR/USD", ",price=bid", "fx", "Most liquid FX pair; demo returns no 'last' candles for FX, bid candles required"),
    "TSLA": ("TSLA", "", "high_vol_stock", "High-volatility US stock (no crypto is served by the demo)"),
    "ES": ("/ESZ26:XCME", "", "futures_control", "CME E-mini S&P Dec-26: trades ~23h/day Sun-Fri, used as near-24h control"),
}
PERIODS = ["1m", "5m", "1h"]

"""Weekend / freeze logger (Task C, Part 1 weekend behaviour and Part 3 staleness).

Polls, at a fixed long interval (default 60 s), the latest Quote and the latest
1-minute candle for each instrument and records: UTC wall clock, the newest
timestamp seen in the response, its age against the wall clock, the dxFeed
status, HTTP latency and any error. One JSONL line per instrument per poll.

Politeness: one request at a time, 60 s cadence (4 instruments -> ~5 req/min),
exponential backoff on errors, and the process exits after 3 consecutive
429/5xx/network failures (see DxClient).

Run (from the repo root, with the `dxfeed` conda env active):

    nohup python deliverables/taskC_assessment/scripts/weekend_logger.py \
        --interval 60 --until 2026-10-19T15:00:00Z > /tmp/weekend_logger.out 2>&1 &

Output: deliverables/taskC_assessment/evidence/weekend_logger/poll_log.jsonl
        deliverables/taskC_assessment/evidence/weekend_logger/requests.jsonl
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import INSTRUMENTS, EVIDENCE, DxClient, iso, ms_to_iso, utcnow  # noqa: E402

OUT_DIR = EVIDENCE / "weekend_logger"
POLL_LOG = OUT_DIR / "poll_log.jsonl"
REQ_LOG = OUT_DIR / "requests.jsonl"

_stop = False


def _handle(sig, frame):  # noqa: ANN001
    global _stop
    _stop = True


def poll_once(client: DxClient) -> list[dict]:
    now = utcnow()
    rows = []
    # One Quote call for all symbols (cheap, single request).
    qsyms = [v[0] for v in INSTRUMENTS.values()]
    q = client.quotes(qsyms, tag="logger_quote")
    qmap = (q.get("data") or {}).get("Quote", {}) if q.get("ok") else {}
    for key, (sym, attrs, cls, _note) in INSTRUMENTS.items():
        rec = {"polled_at": iso(now), "instrument": key, "symbol": sym, "asset_class": cls}
        qv = qmap.get(sym)
        if qv:
            bt = qv.get("bidTime") or 0
            at = qv.get("askTime") or 0
            qt = max(bt, at)
            rec.update(quote_time=ms_to_iso(qt) if qt else None,
                       quote_age_s=round((now.timestamp() * 1000 - qt) / 1000, 1) if qt else None,
                       bid=qv.get("bidPrice"), ask=qv.get("askPrice"),
                       quote_http=q.get("status_code"), quote_dx_status=q.get("dx_status"),
                       quote_latency_s=round(q.get("latency_s", 0), 3))
        else:
            rec.update(quote_time=None, quote_age_s=None, quote_http=q.get("status_code"),
                       quote_dx_status=q.get("dx_status"), quote_error=q.get("error"))
        # Latest 1m candle: ask for the last 3 hours so that a closed market still returns something.
        frm = (now - dt.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        c = client.candles(sym, "1m", frm, None, tag=f"logger_candle_{key}", save_raw=False, extra_attrs=attrs)
        cs = c.get("candles") or []
        if cs:
            last = max(cs, key=lambda x: x["time"])
            rec.update(candle_count_3h=len(cs), last_candle_time=ms_to_iso(last["time"]),
                       last_candle_age_s=round((now.timestamp() * 1000 - last["time"]) / 1000, 1),
                       last_close=last.get("close"), last_volume=last.get("volume"),
                       last_count=last.get("count"))
        else:
            rec.update(candle_count_3h=0, last_candle_time=None, last_candle_age_s=None)
        rec.update(candle_http=c.get("status_code"), candle_dx_status=c.get("dx_status"),
                   candle_latency_s=round(c.get("latency_s", 0), 3), candle_error=c.get("error"))
        rows.append(rec)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=60.0, help="seconds between polls (>= 30)")
    ap.add_argument("--until", default=None, help="ISO UTC time to stop, e.g. 2026-10-19T15:00:00Z")
    ap.add_argument("--max-polls", type=int, default=None, help="stop after N polls (for a smoke test)")
    a = ap.parse_args()
    interval = max(30.0, a.interval)
    until = dt.datetime.strptime(a.until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc) if a.until else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = DxClient(REQ_LOG, raw_dir=None, timeout=30, max_consecutive_failures=3, min_interval_s=1.0)
    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    n = 0
    backoff = interval
    print(f"[{iso()}] logger start interval={interval}s until={a.until} out={POLL_LOG}", flush=True)
    while not _stop:
        t0 = time.monotonic()
        try:
            rows = poll_once(client)
            with POLL_LOG.open("a", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            n += 1
            backoff = interval
            summ = " | ".join(f"{r['instrument']}: q_age={r.get('quote_age_s')} c_age={r.get('last_candle_age_s')}" for r in rows)
            print(f"[{iso()}] poll {n}: {summ}", flush=True)
        except RuntimeError as e:  # consecutive failures -> stop loudly
            print(f"[{iso()}] FATAL {e}", flush=True)
            return 2
        except Exception as e:  # noqa: BLE001
            backoff = min(backoff * 2, 900)
            print(f"[{iso()}] error {e!r}; backing off to {backoff}s", flush=True)
        if a.max_polls and n >= a.max_polls:
            break
        if until and utcnow() >= until:
            break
        elapsed = time.monotonic() - t0
        time.sleep(max(0.0, backoff - elapsed))
    print(f"[{iso()}] logger stop after {n} polls", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

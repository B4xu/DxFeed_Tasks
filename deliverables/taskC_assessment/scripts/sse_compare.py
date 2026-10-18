"""Task C Part 1 — compare the demo streaming output (Server-Sent Events `eventSource`) with
REST snapshots (`events.json`) for the same symbols.

    python sse_compare.py --seconds 180 --symbols AAPL,TSLA --poll 5

What it records (evidence/sse/<ts>/):
  sse_events.jsonl   every SSE message: arrival time, event type, symbol, event time fields,
                     OHLCV for candles (so partial-candle updates can be counted)
  rest_polls.jsonl   REST Quote + 1m Candle snapshot every --poll seconds
  summary.json       update rate, lag of SSE vs REST (time at which the same bidTime was first
                     seen on each side), number of updates per forming candle, max/median age.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVENTS_URL, EVIDENCE, SSE_URL, UA, iso, ms_to_iso  # noqa: E402

NS = "{http://schema.dxfeed.com/event}"


def to_ms(v: str | None) -> int:
    """SSE XML carries ISO-8601 strings ('2026-10-16T11:29:12.000Z'); REST JSON carries epoch ms."""
    if not v:
        return 0
    if v.isdigit():
        return int(v)
    try:
        return int(dt.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    except ValueError:
        return 0


def sse_reader(symbols: list[str], stop: threading.Event, out: Path, stats: dict):
    frm = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"events": "Quote,Candle", "symbols": ",".join(symbols + [f"{s}{{=1m}}" for s in symbols]), "fromTime": frm}
    stats["sse_url_params"] = params
    with requests.get(SSE_URL, params=params, headers={"User-Agent": UA, "Accept": "text/event-stream"}, stream=True, timeout=(10, 60)) as r:
        stats["sse_http"] = r.status_code
        stats["sse_headers"] = dict(r.headers)
        f = (out / "sse_events.jsonl").open("a")
        for line in r.iter_lines():
            if stop.is_set():
                break
            if not line or not line.startswith(b"data:"):
                continue
            arrival = time.time()
            payload = line[5:].strip()
            try:
                root = ET.fromstring(payload)
            except ET.ParseError:
                f.write(json.dumps({"arrival": iso(), "raw": payload[:200].decode(errors="ignore")}) + "\n"); continue
            for ev in root:
                tag = ev.tag.replace(NS, "")
                if tag == "status":
                    f.write(json.dumps({"arrival": iso(), "type": "status", "value": ev.text}) + "\n"); continue
                rec = {"arrival": iso(dt.datetime.fromtimestamp(arrival, dt.timezone.utc)), "type": tag}
                for child in ev:
                    rec[child.tag.replace(NS, "")] = child.text
                if tag == "Quote":
                    qt = max(to_ms(rec.get("bidTime")), to_ms(rec.get("askTime")))
                    rec["age_s"] = round(arrival - qt / 1000, 1) if qt else None
                    stats.setdefault("sse_quote_first_seen", {}).setdefault(f"{rec.get('eventSymbol')}|{qt}", arrival)
                elif tag == "Candle":
                    t = to_ms(rec.get("time"))
                    rec["age_s"] = round(arrival - t / 1000, 1) if t else None
                    key = f"{rec.get('eventSymbol')}|{t}"
                    stats.setdefault("candle_updates", {})[key] = stats.get("candle_updates", {}).get(key, 0) + 1
                stats["sse_events"] = stats.get("sse_events", 0) + 1
                f.write(json.dumps(rec) + "\n")
        f.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=180)
    ap.add_argument("--symbols", default="AAPL,TSLA")
    ap.add_argument("--poll", type=float, default=5.0)
    a = ap.parse_args()
    symbols = a.symbols.split(",")
    out = EVIDENCE / "sse" / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=True)
    stats: dict = {"started_at": iso(), "symbols": symbols, "seconds": a.seconds, "poll_s": a.poll}
    stop = threading.Event()
    th = threading.Thread(target=sse_reader, args=(symbols, stop, out, stats), daemon=True); th.start()
    rest_first_seen: dict[str, float] = {}
    pf = (out / "rest_polls.jsonl").open("a")
    sess = requests.Session(); sess.headers["User-Agent"] = UA
    t_end = time.time() + a.seconds
    n_polls = 0
    while time.time() < t_end:
        t0 = time.time()
        try:
            r = sess.get(EVENTS_URL, params={"events": "Quote", "symbols": ",".join(symbols)}, timeout=20)
            j = r.json(); now = time.time()
            rec = {"ts": iso(), "http": r.status_code, "latency_s": round(now - t0, 3), "dx_status": j.get("status"), "quotes": {}}
            for s, q in (j.get("Quote") or {}).items():
                qt = max(q.get("bidTime") or 0, q.get("askTime") or 0)
                rec["quotes"][s] = {"bidTime": qt, "bid": q.get("bidPrice"), "ask": q.get("askPrice"), "age_s": round(now - qt / 1000, 1)}
                rest_first_seen.setdefault(f"{s}|{qt}", now)
            # 25 min window: the demo feed is ~15 min delayed, so a short window is always empty
            frm = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
            r2 = sess.get(EVENTS_URL, params={"events": "Candle", "symbols": ",".join(f"{s}{{=1m}}" for s in symbols), "fromTime": frm}, timeout=20)
            j2 = r2.json(); rec["candles"] = {}
            for s, lst in (j2.get("Candle") or {}).items():
                if lst:
                    last = max(lst, key=lambda c: c["time"])
                    rec["candles"][s] = {"time": last["time"], "close": last["close"], "volume": last["volume"], "count": last["count"],
                                         "age_s": round(time.time() - last["time"] / 1000, 1), "n": len(lst)}
            pf.write(json.dumps(rec) + "\n"); pf.flush(); n_polls += 1
        except Exception as e:  # noqa: BLE001
            pf.write(json.dumps({"ts": iso(), "error": repr(e)}) + "\n")
        time.sleep(max(0, a.poll - (time.time() - t0)))
    stop.set(); th.join(timeout=5)
    # lag: for each (symbol, bidTime) seen on both sides, REST_first_seen - SSE_first_seen
    lags = []
    for k, t_sse in stats.get("sse_quote_first_seen", {}).items():
        if k in rest_first_seen:
            lags.append(round(rest_first_seen[k] - t_sse, 2))
    cu = stats.get("candle_updates", {})
    stats.update(finished_at=iso(), rest_polls=n_polls, sse_events=stats.get("sse_events", 0),
                 quote_states_seen_both=len(lags), rest_minus_sse_lag_s={"median": sorted(lags)[len(lags) // 2] if lags else None,
                                                                         "min": min(lags) if lags else None, "max": max(lags) if lags else None},
                 candle_updates_per_candle={"candles": len(cu), "updates_total": sum(cu.values()),
                                            "max_updates_one_candle": max(cu.values()) if cu else 0,
                                            "sample": dict(list(cu.items())[:10])})
    stats.pop("sse_quote_first_seen", None); stats.pop("candle_updates", None)
    (out / "summary.json").write_text(json.dumps(stats, indent=2, default=str))
    print(json.dumps(stats, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

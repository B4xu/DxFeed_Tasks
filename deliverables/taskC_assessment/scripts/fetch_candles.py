"""Task C Part 1 — historical candle pull (pass 1 before the weekend, pass 2 after).

Why chunked: the demo REST silently caps a response at 8000 candles (observed 11:33Z on
2026-10-16: a 2-week 1m request returned exactly 8000 candles starting 2026-10-05T18:36Z
with status OK and no truncation flag). Each request therefore covers at most one day for
1m (<= 1440 candles), four days for 5m, and 60 days for 1h.

    python fetch_candles.py --pass pass1 [--start 2026-10-02T00:00:00Z] [--end now]

Outputs (per instrument and period) under evidence/candles/<pass>/:
    <KEY>_<period>.json      merged, de-duplicated by `time`, sorted
    <KEY>_<period>.csv       same as CSV (time_iso, open, high, low, close, volume, count, vwap, ...)
    chunks.jsonl             one line per request: range asked, candles returned, first/last time, latency
Raw bodies go to evidence/candles/<pass>/raw/, request log to evidence/candles/<pass>/requests.jsonl.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVIDENCE, INSTRUMENTS, PERIODS, DxClient, iso, ms_to_iso, utcnow  # noqa: E402

CHUNK_DAYS = {"1m": 1, "5m": 4, "1h": 60}
CAP = 8000
FIELDS = ["time", "time_iso", "open", "high", "low", "close", "volume", "count", "vwap", "bidVolume",
          "askVolume", "impVolatility", "openInterest", "eventFlags", "sequence", "index", "eventSymbol"]


def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def fmt(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="pass_name", required=True)
    ap.add_argument("--start", default="2026-10-02T00:00:00Z", help="start for 1m/5m")
    ap.add_argument("--start-1h", default="2026-01-01T00:00:00Z", help="start for 1h (holiday coverage)")
    ap.add_argument("--end", default=None, help="default: now")
    ap.add_argument("--instruments", default=",".join(INSTRUMENTS))
    ap.add_argument("--periods", default=",".join(PERIODS))
    a = ap.parse_args()

    out = EVIDENCE / "candles" / a.pass_name
    out.mkdir(parents=True, exist_ok=True)
    client = DxClient(out / "requests.jsonl", raw_dir=out / "raw", min_interval_s=1.0)
    end = parse_ts(a.end) if a.end else utcnow().replace(microsecond=0)
    chunks_f = (out / "chunks.jsonl").open("a", encoding="utf-8")
    summary = {}
    for key in a.instruments.split(","):
        sym, attrs, cls, _ = INSTRUMENTS[key]
        for period in a.periods.split(","):
            start = parse_ts(a.start_1h if period == "1h" else a.start)
            merged: dict[int, dict] = {}
            t = start
            n_req = 0
            boundary_dups = 0
            conflicts = 0
            while t < end:
                t2 = min(end, t + dt.timedelta(days=CHUNK_DAYS[period]))
                r = client.candles(sym, period, fmt(t), fmt(t2), extra_attrs=attrs, tag=f"{a.pass_name}_{key}_{period}")
                cs = r.get("candles") or []
                n_req += 1
                rec = {"requested_at": r["requested_at"], "instrument": key, "symbol": r["candle_symbol_requested"],
                       "period": period, "from": fmt(t), "to": fmt(t2), "n": len(cs), "dx_status": r["dx_status"],
                       "http": r["status_code"], "latency_s": round(r["latency_s"], 3), "bytes": r.get("bytes"),
                       "first": ms_to_iso(min(c["time"] for c in cs)) if cs else None,
                       "last": ms_to_iso(max(c["time"] for c in cs)) if cs else None,
                       "hit_cap": len(cs) >= CAP, "raw_path": r.get("raw_path")}
                chunks_f.write(json.dumps(rec) + "\n"); chunks_f.flush()
                for c in cs:
                    prev = merged.get(c["time"])
                    if prev is not None:
                        boundary_dups += 1
                    if prev is not None and {k: prev.get(k) for k in ("open", "high", "low", "close", "volume")} != \
                            {k: c.get(k) for k in ("open", "high", "low", "close", "volume")}:
                        # same timestamp returned twice with different values across chunk boundaries -> keep both facts
                        conflicts += 1
                        c = dict(c, _dup_conflict_with=prev)
                    merged[c["time"]] = c
                print(f"[{iso()}] {key} {period} {fmt(t)}..{fmt(t2)} n={len(cs)} status={r['dx_status']} {r['latency_s']:.2f}s", flush=True)
                t = t2
            rows = [merged[k] for k in sorted(merged)]
            for c in rows:
                c["time_iso"] = ms_to_iso(c["time"])
            (out / f"{key}_{period}.json").write_text(json.dumps(rows))
            with (out / f"{key}_{period}.csv").open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                w.writeheader(); w.writerows(rows)
            summary[f"{key}_{period}"] = {"requests": n_req, "candles": len(rows),
                                          "boundary_duplicates": boundary_dups, "boundary_conflicts": conflicts,
                                          "first": rows[0]["time_iso"] if rows else None,
                                          "last": rows[-1]["time_iso"] if rows else None}
    (out / "summary.json").write_text(json.dumps({"pass": a.pass_name, "fetched_at": iso(), "end": fmt(end),
                                                  "start_1m_5m": a.start, "start_1h": a.start_1h, "series": summary}, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

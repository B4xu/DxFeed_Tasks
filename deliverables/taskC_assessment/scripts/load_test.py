"""Task C Part 2 — controlled, polite load test of the public demo REST endpoint.

    python load_test.py --run market_open_fri --steps 1,5,10,25,50 --step-seconds 30

Design
- One aiohttp session, N concurrent workers per step, each worker issues one request at a
  time with a short think time, so concurrency == N in-flight requests at most.
- Request mix per worker (round-robin): Quote snapshot for a symbol; Candle 1m "last 60 min"
  for a symbol (freshness probe); a FIXED historical Candle window (consistency probe: the
  body must be byte-identical every time).
- Hard safety limits: stop the whole run on the first 429, on 3 consecutive 5xx/network
  errors, if a step's error rate exceeds 20 % after 20 requests, if p50 latency in a step
  exceeds 8 s, or when the total request budget is spent.
- Everything is recorded per request to evidence/load/<run>/requests.jsonl; summary and
  plots are produced by analyze_load.py.

This measures what ONE client sees from a SHARED public demo service; it says nothing about
dxFeed production capacity.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dxclient import EVENTS_URL, EVIDENCE, UA, iso, utcnow  # noqa: E402

SYMBOLS = ["AAPL", "TSLA", "SPY", "MSFT", "IBM", "GOOG", "AMZN", "DIA"]
FX = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]
FUT = ["/ESZ26:XCME"]
ALL_QUOTE = SYMBOLS + FX + FUT
CANDLE_SYMS = [(s, "") for s in SYMBOLS] + [(s, ",price=bid") for s in FX] + [(s, "") for s in FUT]
# fixed historical window for the consistency probe (yesterday's regular session hour)
FIXED_FROM, FIXED_TO = "2026-10-15T14:00:00Z", "2026-10-15T15:00:00Z"
HDR_KEEP = ("date", "server", "cache-control", "age", "etag", "expires", "retry-after", "x-ratelimit-limit",
            "x-ratelimit-remaining", "x-ratelimit-reset", "x-origin-nginx", "via", "x-cache", "content-encoding",
            "connection", "transfer-encoding", "content-length")


class Stop(Exception):
    pass


class Runner:
    def __init__(self, out: Path, budget: int, think_s: float):
        self.out = out
        self.f = (out / "requests.jsonl").open("a", encoding="utf-8")
        self.budget = budget
        self.think_s = think_s
        self.total = 0
        self.consec_err = 0
        self.stop_reason: str | None = None
        self.step_stats: dict[str, list] = {}
        self.lock = asyncio.Lock()

    def build(self, worker: int, i: int) -> tuple[str, dict, str]:
        kind = ("quote", "candle_fresh", "candle_fixed")[i % 3]
        if kind == "quote":
            sym = ALL_QUOTE[(worker + i) % len(ALL_QUOTE)]
            return kind, {"events": "Quote", "symbols": sym}, sym
        if kind == "candle_fresh":
            sym, attrs = CANDLE_SYMS[(worker + i) % len(CANDLE_SYMS)]
            frm = (utcnow() - dt.timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
            return kind, {"events": "Candle", "symbols": f"{sym}{{=1m{attrs}}}", "fromTime": frm}, sym
        sym = SYMBOLS[(worker + i) % 2]  # AAPL / TSLA only -> many identical queries
        return kind, {"events": "Candle", "symbols": f"{sym}{{=1m}}", "fromTime": FIXED_FROM, "toTime": FIXED_TO}, sym

    async def one(self, session: aiohttp.ClientSession, step: int, conc: int, worker: int, i: int):
        kind, params, sym = self.build(worker, i)
        rec = {"ts": iso(), "step": step, "concurrency": conc, "worker": worker, "kind": kind, "symbol": sym, "params": params}
        t0 = time.perf_counter()
        try:
            async with session.get(EVENTS_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as r:
                body = await r.read()
                lat = time.perf_counter() - t0
                rec.update(http=r.status, latency_s=round(lat, 4), bytes=len(body), sha1=hashlib.sha1(body).hexdigest(),
                           headers={k: v for k, v in r.headers.items() if k.lower() in HDR_KEEP})
                try:
                    j = json.loads(body)
                    rec["dx_status"] = j.get("status")
                    now_ms = time.time() * 1000
                    if kind == "quote":
                        q = (j.get("Quote") or {}).get(sym)
                        if q:
                            qt = max(q.get("bidTime") or 0, q.get("askTime") or 0)
                            rec["data_time_ms"] = qt; rec["age_s"] = round((now_ms - qt) / 1000, 1) if qt else None
                        else:
                            rec["empty"] = True
                    else:
                        cs = [c for lst in (j.get("Candle") or {}).values() for c in lst]
                        rec["n_candles"] = len(cs)
                        if cs:
                            last = max(c["time"] for c in cs)
                            rec["data_time_ms"] = last; rec["age_s"] = round((now_ms - last) / 1000, 1)
                        else:
                            rec["empty"] = True
                except ValueError:
                    rec["json_error"] = True
                ok = r.status == 200 and not rec.get("json_error")
                if r.status == 429:
                    self.stop_reason = f"HTTP 429 received at step {step} (concurrency {conc})"
                if r.status >= 500:
                    self.consec_err += 1
                elif ok:
                    self.consec_err = 0
        except Exception as e:  # noqa: BLE001
            lat = time.perf_counter() - t0
            rec.update(error=repr(e), latency_s=round(lat, 4), http=None)
            self.consec_err += 1
            ok = False
        rec["ok"] = ok
        async with self.lock:
            self.total += 1
            self.f.write(json.dumps(rec) + "\n")
            st = self.step_stats.setdefault(str(step), [])
            st.append(rec)
            if self.consec_err >= 3:
                self.stop_reason = self.stop_reason or f"3 consecutive 5xx/network errors at step {step}"
            if len(st) >= 20:
                err = sum(1 for x in st if not x["ok"]) / len(st)
                if err > 0.20:
                    self.stop_reason = self.stop_reason or f"error rate {err:.0%} at step {step}"
                lats = sorted(x["latency_s"] for x in st)
                if statistics.median(lats) > 8.0:
                    self.stop_reason = self.stop_reason or f"p50 latency {statistics.median(lats):.1f}s at step {step}"
            if self.total >= self.budget:
                self.stop_reason = self.stop_reason or f"request budget {self.budget} spent"
        if self.stop_reason:
            raise Stop(self.stop_reason)

    async def worker(self, session, step, conc, worker, deadline):
        i = 0
        while time.monotonic() < deadline:
            await self.one(session, step, conc, worker, i)
            i += 1
            await asyncio.sleep(self.think_s)

    async def run(self, steps: list[int], step_seconds: float, pause_s: float):
        connector = aiohttp.TCPConnector(limit=max(steps) + 2)
        async with aiohttp.ClientSession(headers={"User-Agent": UA}, connector=connector) as session:
            for si, conc in enumerate(steps):
                t_start = iso()
                print(f"[{t_start}] step {si}: concurrency={conc} for {step_seconds}s", flush=True)
                deadline = time.monotonic() + step_seconds
                tasks = [asyncio.create_task(self.worker(session, si, conc, w, deadline)) for w in range(conc)]
                try:
                    await asyncio.gather(*tasks)
                except Stop as e:
                    # cancel the other workers so in-flight requests are not silently left running
                    # (and their later completions do not leak into the next step's statistics)
                    for t in tasks:
                        t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    print(f"[{iso()}] STOP: {e}", flush=True)
                    self._step_summary(si, conc, t_start)
                    return
                self._step_summary(si, conc, t_start)
                await asyncio.sleep(pause_s)

    def _step_summary(self, si, conc, t_start):
        st = self.step_stats.get(str(si), [])
        if not st:
            return
        lats = sorted(x["latency_s"] for x in st)
        q = lambda p: lats[min(len(lats) - 1, int(p * len(lats)))]  # noqa: E731
        errs = sum(1 for x in st if not x["ok"])
        codes = {}
        for x in st:
            codes[str(x.get("http"))] = codes.get(str(x.get("http")), 0) + 1
        summ = {"step": si, "concurrency": conc, "start": t_start, "end": iso(), "n": len(st), "errors": errs,
                "http_codes": codes, "p50": q(.5), "p95": q(.95), "p99": q(.99), "max": lats[-1],
                "rps": round(len(st) / max(1e-6, (dt.datetime.fromisoformat(iso()[:-1]) - dt.datetime.fromisoformat(t_start[:-1])).total_seconds()), 2),
                "note": "rps = completed requests / wall clock from step start to step end (through completion)"}
        print(json.dumps(summ), flush=True)
        with (self.out / "steps.jsonl").open("a") as f:
            f.write(json.dumps(summ) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run label, e.g. market_open_fri")
    ap.add_argument("--steps", default="1,5,10,25,50")
    ap.add_argument("--step-seconds", type=float, default=30.0)
    ap.add_argument("--pause-seconds", type=float, default=10.0)
    ap.add_argument("--think-seconds", type=float, default=0.25)
    ap.add_argument("--budget", type=int, default=3500, help="hard cap on total requests")
    a = ap.parse_args()
    out = EVIDENCE / "load" / a.run
    out.mkdir(parents=True, exist_ok=True)
    meta = {"run": a.run, "started_at": iso(), "steps": a.steps, "step_seconds": a.step_seconds,
            "pause_seconds": a.pause_seconds, "think_seconds": a.think_seconds, "budget": a.budget,
            "endpoint": EVENTS_URL, "symbols_quote": ALL_QUOTE, "fixed_window": [FIXED_FROM, FIXED_TO]}
    runner = Runner(out, a.budget, a.think_seconds)
    asyncio.run(runner.run([int(s) for s in a.steps.split(",")], a.step_seconds, a.pause_seconds))
    meta.update(finished_at=iso(), total_requests=runner.total, stop_reason=runner.stop_reason)
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

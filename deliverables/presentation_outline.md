# dxFeed demo services — 45-minute presentation outline

Audience: dxFeed support and engineering interviewers. Goal: show investigation method,
evidence discipline and operational judgement, not just a list of bugs. Every slide number
maps to a file in `deliverables/` so any claim can be opened live.

Timing: 5 min context and method · 15 min data consistency · 8 min load behaviour ·
7 min risk and incident simulation · 5 min improvements · 5 min questions.

---

## 0. Opening (1 min)

Slide: title, date of data collection (Fri 2026-10-16, pass 1; Mon 2026-10-19, pass 2),
one sentence: "Everything you will see is reproducible from `evidence/` with the scripts in
`scripts/`; where I could not verify something I will say so."

## 1. Context and method (4 min)

Slide 1 — What I was given and how I planned around the market calendar: historical pulls any
time; real-time/load planned for 13:30–20:00Z but **executed pre-market** (11:42–12:11Z) at
the user's request — labelled as such; weekend as a freeze window; logger started Friday.
Speaker notes: mention Tbilisi/New York offset explicitly; this is the first thing a support
engineer gets wrong on a Monday morning.

Slide 2 — Endpoint discovery: `tools.dxfeed.com → demo.dxfeed.com/webservice/rest`, candle
syntax from the Javadoc, three traps found in the first 10 minutes (curl braces, `{=m}`
normalisation, TIMED_OUT for unknown symbols = HTTP 200).
Speaker notes: "If it took me three experiments, it takes every prospect three experiments."

Slide 3 — Instruments and why: AAPL (liquid, extended hours), EUR/USD (bid candles only),
TSLA (no crypto on the demo — show the TIMED_OUT list), /ESZ26 as 23-hour control.
Speaker notes: be upfront that the brief's "crypto" could not be honoured and why.

Slide 4 — Evidence discipline: request log line format (UTC time, URL, latency, status, body
hash), raw bodies, chunked downloads, two passes, politeness rules (1 req/s sequential,
auto-stop on 429/5xx/p50 > 8 s).

## 2. Data consistency findings (15 min)

Slide 5 — The feed is 15-minute delayed: 900.8 s quote age on every instrument (logger
plot `evidence/plots/logger/data_age_timeline.png`). Frame: "fresh means 900 s old; every
freshness SLO must be written relative to that."

Slide 6 — What is right: 58,315 candles, 0 misaligned, 0 out-of-order, 21 boundary duplicates
with 0 conflicts, holidays match the Task A calendar (`per_day_1m_counts.png`), 5m == 1m on
complete buckets. What is not perfect: OHLC differs on 6 hourly-from-5m candles (AAPL close
333.35 vs 333.3015). First hourly bar is 00:00 ET; AAPL serves 00:00-19:59 ET.
Speaker notes: say this first; credibility comes from reporting what works.

Slide 7 — **Strongest finding 1: silent 8000-candle cap and 1m retention.** Show the chunk log:
a 2-week request returns about 8000 newest candles (8000 or 8001), status OK. Impact: backtests lose a
week without an error. Hypotheses A/B and the discriminating test.

Slide 8 — **Strongest finding 2: hourly stock volume ≠ Σ5m volume (mostly ETH).**
Plot `agg_AAPL_1h_from_5m.png`; counts: AAPL **130 ETH + 1 RTH**, TSLA **118 ETH + 2 RTH**;
RTH exception 2026-10-08 11:00 ET (~+2 %, opposite sign). Re-fetch: 1h bars **stable** after
+11.5 min (no continuing late update). TimeAndSale blocked on demo REST. Hypotheses only —
not conclusions.

Slide 9 — **Strongest finding 3: FX candles outside the FX session (50 of 8000 1m, 39 5m).**
Split: 7 Friday after 17:00 ET close, 0 Saturday, 43 Sunday pre-open sparse prints. The old
"214 weekend" figure included the legitimate Sunday reopen (withdrawn). ES: 0 outside session. Impact on daily
bars and "is the market open" logic.

Slide 10 — Smaller edge cases in one table: FX `price=bid` only and volume = tick count;
daily candle stamped at 00:00 UTC; inclusive `toTime`; unknown symbols ~3.3 s idle (29 s under load); Radar vs REST
symbol universe (NVDA in Radar, TIMED_OUT in REST); forming candle unflagged.

Slide 11 — Radar vs REST and SSE vs REST (pre-market **and** market hours): Radar 1m OHL
matches the delayed REST bar; SSE lag median 0.72 s pre-market / 0.26 s RTH; quote age ~900 s
both; NaN/2038 control messages if `fromTime` is inside the delay window.
Speaker notes: the 2038 timestamp is the best "would your client code survive this?" slide.

Slide 12 — Pass 2 (Monday after 15:30Z): forming-candle finalisation, closed-candle stability,
Monday reopen alignment, weekend logger transitions. Logger restarted Sat 13:01Z (PID 15513;
gap Fri 14:49Z→Sat restart). If pass 2 not run yet: show commands and what they answer.

## 3. Load behaviour (8 min)

Slide 13 — Setup: aiohttp, steps 1/5/10/25/50 × 30 s, hard stops. Runs: pre-market **and**
market hours (13:47Z). Little's law: L≈c at c=5/10, but the pool limit (52) >= max c (50), so it could
never bind; per-IP throttle vs shared capacity unresolved (second client not run).
Speaker notes: "One client, shared demo; not a production capacity claim. Market hours had
about twice the throughput of pre-market; shared-demo load varies. Percentiles use completed
requests only (censored)."

Slide 14 — Comparison table: pre-market thr ~1.55-1.68 rps / p50 0.76→8.27; market hours thr
3.18/3.19/3.02/2.78 rps at c=5/10/25/50 (flat, not rising) / p50 0.45→5.28 at c=25 (reached c=50). Quote age ~900 s both. 0 errors, no 429.
Plot `evidence/plots/load/*_latency.png`.

Slide 15 — What failed first / degraded first: nothing failed; latency degraded first; at c>=25 candle requests queue far longer than quotes (11-12 s vs 2.6 s);
server-side TIMED_OUT also stretched (3.3 s at c=1 → ~29 s at c=50) because
the queue wait is added before the timeout starts; symbol-specific: AUD/USD bid candles
time out while its quote works; first request of a cold run 26 s (one observation,
hypothesis: cold start).

Slide 16 — Consistency and caching: fixed-window bodies byte-identical across all repeats;
no cache headers; repeated-query latency not lower than first query → no evidence of an HTTP
cache; data age unchanged under load (the delay is upstream of the web service).

Slide 17 — Monitoring, SLOs, triggers (table from report Part 2).

## 4. Risk review and incident simulation (7 min)

Slide 18 — Risk table (Part 3), ranked; one line each on detection/mitigation/escalation.
Emphasise the two silent ones (cap, cross-timeframe volume).

Slide 19 — Incident simulation INC-SIM-01: timeline, what the client sees, what L2 verifies in
the first 15 minutes, the escalation note (show the evidence paragraph), the client message
(show that it contains no speculation and a next-update time).

Slide 20 — Post-mortem outline and the three action items with owners.

## 5. Improvements (5 min)

Slide 21 — Technical: response envelope with truncated/serverTime/delay/lastEventTime,
flagged forming candle, immediate UNKNOWN_SYMBOL. Complexity M, why.
Slide 22 — Monitoring: synthetic probes per asset class with SLOs; complexity S–M; the
trade-off that probes cost real capacity on this service.
Slide 23 — Documentation: "demo service facts" page; complexity S; this report is the draft.

## 6. Questions (5 min)

---

## Live-demo candidates (with fallbacks)

1. **Show the cap live.** In a browser or terminal: `events.json?events=Candle&symbols=AAPL{=1m}&fromTime=<14 days ago>`
   and count the candles (8000) and the first timestamp. Fallback: open
   `evidence/candles/pass1/chunks.jsonl` and the saved raw body (hash recorded).
2. **Rebuild 1h from 5m live.** Run `python scripts/validate_candles.py --pass pass1` (4 s,
   offline) and open the AAPL 18:00 ET row in `agg_AAPL_1h_from_5m.csv`. Fallback: the PNG and
   the CSV are already in the repo.
3. (Optional, market hours only) Radar "Last Candle 1m" for AAPL next to a REST `{=1m}` call;
   fallback: `evidence/radar/` screenshots and `compare_*.json`.

## Likely tough questions and answers

*"Isn't the 8000 cap just the demo's quota?"* Probably, and that is fine; the issue is that the
response says OK. A `truncated` flag or documentation fixes it at near-zero cost.

*"Your hourly-volume finding could be late prints; why do you call it an inconsistency?"*
On the one day with a daily candle the hourly sum is closer to daily than the 1m sum — which series is the reference is not yet determined. ETH pattern is systematic; AAPL has
1 RTH exception (opposite sign), TSLA 2. Re-fetch of that 1h bar is stable after +11.5 min.
TimeAndSale is TIMED_OUT on demo REST, so sale-condition cause stays a hypothesis.

*"You load-tested a free shared demo. What does that prove about production?"* Nothing about
production capacity. It proves how this service behaves for one client: queueing instead of
rejecting, and no signalling. The monitoring and SLO design transfers; the numbers do not.

*"Why TSLA and not a crypto pair?"* The demo serves no crypto; I probed 6 symbol variants and
recorded the TIMED_OUT responses. TSLA is the most volatile liquid instrument served; ES was
added as a near-24-hour control for the weekend question.

*"What did you not verify?"* The Google Drive upload (no account; DRY_RUN only), the Playwright
fallback for nasdaq.com (not exercised), the CME calendar (site blocks automation; manual
input), pass 2/Monday reopen (scheduled), and the root causes of Anomalies 1–3 (hypotheses
with proposed tests).

*"How would you prioritise the three anomalies?"* Cap first (silent, affects every history
request), hourly volume second (silent, affects analytics), FX weekend ticks third (visible,
cosmetic unless used for session detection).

*"Was your load test polite?"* Max 50 planned, stopped automatically at 25 when p50 exceeded
8 s; think time between requests; 144 requests total pre-market; no 429 ever seen; full
request logs available.

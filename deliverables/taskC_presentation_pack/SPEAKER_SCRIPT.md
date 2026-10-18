# Speaker script — Task C 45-minute live presentation

**Slides:** 28 · **Target:** 45 minutes  
**Pacing:** ~5 min context · 15 min data · 8 min load · 7 min risk/incident · 5 min improvements · 5 min Q&A

## Global rules while speaking
- Lead with method and validation, then findings.
- Say **verified** vs **hypothesis** out loud.
- Never say “0 RTH mismatches”, “OHLC always agrees”, “214 weekend candles”, or throughput “rising to 4.6”.
- If demo network fails: use offline fallbacks in SUPPORTING_MATERIALS.md.

---

## Slide 1 — Title

OPENING (about 45 seconds). This deck is the evidence from Friday 16 October 2026. Green means I measured it. Amber means I have a pattern and a hypothesis, not a root cause. Coral means the work was not done, and I will say why. Pass 2 is still waiting for Monday 19 October after 15:30 UTC.

---

## Slide 2 — At a glance

One slide of numbers before any detail. Read them left to right; each one has its own slide later. Latencies everywhere in this deck are seconds, not milliseconds.

---

## Slide 3 — Done, partial, and not done

Spend two minutes here. Interviewers will ask what you did not verify. Answer from the coral column before they ask. Do not upgrade amber items to conclusions.

---

## Slide 4 — Section: Task A

Thirty seconds. The calendar is the input to the gap analysis in Task C.

---

## Slide 5 — Task A chart

Task A in one minute. 60 data rows. NYSE matched NASDAQ on every 2026 date. CME is empty because scraping is forbidden.

---

## Slide 6 — Section: data consistency

Fifteen minutes for this section. Lead with what works, then the silent defects.

---

## Slide 7 — 15-minute delay

Quote age sits on 900 seconds for every symbol. Fresh means fifteen minutes old.

---

## Slide 8 — Price integrity

Lead with what works: 58,315 candles, 0 misaligned, holidays match. Then say OHLC is not 100% clean.

---

## Slide 9 — OHLC mismatches

Six candles, three complete, all under 0.03 percent. Earlier claim of perfect agreement withdrawn.

---

## Slide 10 — Volume split summary

AAPL 130 ETH plus 1 RTH. TSLA 118 ETH plus 2 RTH. Cause not proven.

---

## Slide 11 — AAPL heatmap

Red outside regular hours, white inside, one blue exception.

---

## Slide 12 — AAPL volume chart

Blue dots below zero are extended-hours volume gaps. One regular-hours hour goes the other way.

---

## Slide 13 — TSLA volume chart

Same extended-hours pattern. Two regular-hours exceptions. TimeAndSale blocked.

---

## Slide 14 — Volume reconciliation

Hourly is closer to daily on the one day we have. No workaround is offered.

---

## Slide 15 — EURUSD weekend

50 outside-session minutes (not 214). Not proven to be trades.

---

## Slide 16 — Silent 8000

Live demo: request 14 days of AAPL 1-minute candles, or open chunks.jsonl. Count 8000. Show the empty older window. Do not claim this is a production bug.

---

## Slide 17 — Candle totals

Identical 8,000 ceiling across four very different instruments: a server limit, silent.

---

## Slide 18 — Section: load

Eight minutes. Every latency is seconds.

---

## Slide 19 — Load p50 chart

Throughput flat (~1.6 pre, ~3.2 market). Pool could not bind; second client not run. No 429.

---

## Slide 20 — Throughput

Flat at about 1.6 and 3 requests per second. The 4.6 figure was a measurement artefact.

---

## Slide 21 — Latency by type

Quotes stay fast, candles queue. TIMED_OUT stretches to 29 seconds.

---

## Slide 22 — Latency plots

Point at p95, not the error rate. The error rate stayed zero while the experience died.

---

## Slide 23 — Radar

OHL matches. 2038 NaN candles are a client footgun. NVDA is a different symbol list.

---

## Slide 24 — Open items

If asked 'what did you not verify', read this slide. Pass 2 and the logger analysis are the only ones that are simply waiting on the clock.

---

## Slide 25 — Section: risk and incident

Twelve minutes for risk, incident and improvements together.

---

## Slide 26 — Risks and incident

Seven minutes for risk and the incident. The external email must not assert a root cause.

---

## Slide 27 — Improvements

Five minutes. Lead with the response envelope because it fixes the silent cap.

---

## Slide 28 — Questions

Q&A. If they ask whether the 8000 cap is just a quota: yes, possibly, and the defect is still the missing signal. If they ask about production RPS: the monitoring design transfers, the numbers do not.

---

## Anticipated Q&A (grounded answers)

**Q: Isn’t the 8000 cap just the demo’s quota?**  
A: Probably intentional. The defect is `status: OK` with no truncation signal, and older windows look like holidays. A flag or one docs sentence fixes the client-visible failure mode.

**Q: Could hourly volume just be late prints?**  
A: On the one daily candle we have (2026-10-14) the hourly sum is closer to daily than the 1m sum, so we do not say which series is the reference. ETH pattern is systematic. AAPL and TSLA RTH exceptions fall on the same day/hour with the opposite sign; re-fetch stable after +11.5 min. TimeAndSale is TIMED_OUT; SPY/MSFT and tho=true not tested.

**Q: What does the load test prove about production?**  
A: Nothing about production capacity. It shows *this* shared demo queues without 429 for one client. Monitoring design transfers; absolute RPS numbers do not.

**Q: Why not crypto?**  
A: Demo returns TIMED_OUT for BTC/USD and variants. TSLA substituted; ES added as a session control. Probe logs kept.

**Q: Did you find zero RTH volume mismatches?**  
A: No. AAPL 1, TSLA 2 in the sample. Wording was corrected; pattern remains overwhelmingly ETH.

**Q: Is the load plateau your aiohttp pool?**  
A: The pool limit (52) is above the max concurrency (50), so it could never bind. Whether the cap is per-IP or shared capacity is unresolved; a second client was not run.

**Q: What did you not verify?**  
A: Pass 2 / complete weekend analysis (Monday); TimeAndSale root cause; second client for load; Task A Drive/CME are separate.

**Q: Was the load test polite?**  
A: Auto-stop p50>8s, think time, budgets, no 429 observed; full request logs in evidence/load/.

## Closing line

“Happy to open any evidence file live. The transferable outcome is how we investigate silent failures — retention OK, cross-timeframe volume, and queueing without back-pressure — not a claim about production capacity.”

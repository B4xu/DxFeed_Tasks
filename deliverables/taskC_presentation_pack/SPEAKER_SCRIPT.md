# Speaker script — Task C 45-minute live presentation

**Slides:** 26 · **Target:** 45 minutes  
**Pacing:** ~3 min context · 3 min Task A · 15 min data · 9 min load · 10 min risk/incident/improvements · 5 min Q&A

## Global rules while speaking
- Lead with method and validation, then findings.
- Say **verified** vs **hypothesis** out loud.
- Never say “0 RTH mismatches”, “OHLC always agrees”, “214 weekend candles”, or throughput “rising to 4.6”.
- If demo network fails: use offline fallbacks in SUPPORTING_MATERIALS.md.

---

## Slide 1 — Title

Hi, I'm Irakli. For Task C I treated the demo feed the way I would treat a client saying 'your data looks wrong'. I pulled enough history to test it properly, rebuilt the bigger candles from the smaller ones, compared everything, and then put some polite load on it. All of this was on Friday 16 October. Everything I show today can be recomputed from the saved files without touching the demo again.

---

## Slide 2 — Agenda

Four parts. Most of the time goes to data consistency, because that is where the interesting problems are. Every slide has a tag in the corner: verified means I reproduced it from the saved data, hypothesis means it fits but I could not prove it, not done means exactly that.

---

## Slide 3 — The short version

If you remember one slide, this is it. The feed is delayed by exactly fifteen minutes. History silently stops at about eight thousand candles. Hourly volume for US stocks doesn't match the five-minute candles outside regular hours. FX prints a few candles when the market is closed. And under load the service queues instead of saying slow down. All latencies today are in seconds, not milliseconds.

---

## Slide 4 — How I worked

This is the pipeline. I pulled history in chunks, validated each series, rebuilt the bigger timeframes from the smaller ones, cross-checked against the stream and Radar, then ran the load test. At the end I re-ran every headline number offline, and that re-check corrected four of my own earlier claims. I'll point them out when we get there. Crypto was in the brief, but every crypto symbol timed out on the demo, so TSLA is my high-volatility instrument.

---

## Slide 5 — Section: Task A: holiday calendar

Task A: holiday calendar. About 3 minutes. The calendar Task C uses to tell a holiday from a gap

---

## Slide 6 — NYSE and NASDAQ agree on every 2026 date

I built a small scraper with one adapter per exchange. It writes one CSV per exchange plus a combined file, and validates them. NYSE and NASDAQ match on every closed day and early close in 2026. The overall result is WARN, not FAIL. CME is a deliberate gap: its site terms forbid scraping, so the adapter only reads files dropped in by hand. OPRA has only published the 2025 PDF; the 2026 one returned 403. I uploaded the CSVs to Drive myself. The automated Drive upload is written but has not run with real credentials.

---

## Slide 7 — Section: Data consistency

Data consistency. About 15 minutes. What is right, and the problems that do not raise an error

---

## Slide 8 — What is right: the basics are clean

I want to say what works before the problems. Across all twelve series there are no misaligned timestamps, nothing out of order, no NaN prices. Equities are empty on every NYSE holiday, matching Task A, and EUR/USD trades through them, which is correct. The 21 duplicates come from toTime being inclusive, and they carry identical values, so dropping them is safe.

---

## Slide 9 — Every quote is exactly 15 minutes old

Quote age sits on nine hundred seconds for every symbol, on every surface. That's fine for a demo, but nothing in the response says it is delayed. A client who builds a 'data is stale' alert from zero will page all day. I'd want the delay in the payload.

---

## Slide 10 — History stops at 8,000 candles and still says OK

This is the one I'd escalate first. I asked for two weeks of one-minute AAPL and got the newest eight thousand, with status OK. The decisive test was a window completely before that edge: OK again, empty body. It may well be an intentional demo quota, and that's fine. The problem is the silence. A truncated flag, or one sentence in the docs, fixes it. I can show this live with chunks.jsonl.

---

## Slide 11 — Hourly volume breaks outside regular hours

This is the most interesting finding. Each cell is one hour; red means the served hourly bar has more volume than its five-minute bars add up to. The boxed regular-hours block is white, and outside it the difference goes up to 99 percent. There is one blue cell inside regular hours, 8 October 11:00 ET, plus 2 percent the other way. TSLA has two exceptions on the same day and hours, which points to a market-wide event, not an AAPL thing. Re-fetching 11 minutes later gave the same values. The test that would explain it needs TimeAndSale, and that timed out on the demo. So: real pattern, cause open.

---

## Slide 12 — Which volume is right? Not decided yet

This slide changed my advice. My first draft said 'build extended-hours analytics from one-minute data'. The data doesn't support that: on the only day with a daily candle, the hourly sum is slightly closer. One data point, so I don't pick a winner. tho=true might be a workaround but I never tested it.

---

## Slide 13 — Prices are almost, not perfectly, consistent

I'm correcting myself here. An earlier draft said prices always agree. They nearly do. Three of the six differences are the bar that was still forming, which is expected. Three are complete hours, and two of those are TSLA on 8 October, the same block as the volume exception. Small, but I'd rather say it.

---

## Slide 14 — EUR/USD prints 50 candles while FX is closed

FX trades Sunday 17:00 to Friday 17:00 New York time. My first count used the UTC weekday and got 214, but 170 of those are just the Sunday reopen. Against the real session it's 50. They might be indicative quotes or a heartbeat; I set up a weekend logger to tell them apart, but it stopped on Saturday, so that stays open. The client risk is session logic: 'last candle is fresh' would call FX open on Sunday morning.

---

## Slide 15 — Edge cases

These are the small ones. None of them throws an error, which is exactly why they turn into tickets. My favourite is the 2038 date: if you open the stream inside the delay window you get NaN candles dated 2038. A parser that ignores the flags stores them. Radar versus REST is just different symbol lists, but support will hear 'it works in Radar' a lot.

---

## Slide 16 — Section: Behaviour under load

Behaviour under load. About 9 minutes. What happens when one client adds parallel requests

---

## Slide 17 — More workers did not buy more throughput

Market-hours run. Left: throughput measured through completion. It jumps from one to five workers and then stays flat around three requests a second, and drops a little at fifty. Right: latency. Median goes from half a second to eight seconds, p95 to twenty-six. I want to be careful about two things. An earlier version said throughput rose to 4.6; that number ignored requests still in flight, and it's wrong. And these are seconds. Zero errors, no 429, no Retry-After: the service queues, it never tells the client to back off.

---

## Slide 18 — Latency by request type

Queueing isn't uniform. Quotes stay fairly quick while both candle requests wait eleven or twelve seconds. That fits per-request cost or separate queues, not one simple line. On the right, the timeout for an unknown symbol: three seconds alone, twenty-nine under load, because queue time is added before the server's own timeout starts. A dashboard mixing quotes and candles will look half alive.

---

## Slide 19 — Bottleneck

The first question I asked myself was whether I was the bottleneck. Little's law says no: at five and ten workers the average in flight equals the setting, so they were all waiting on the server. The pool allowed 52 connections and I never ran more than 50. What I can't say is whether the cap is per IP or shared with other demo users. That needs a second client at the same time, and I didn't run it. If anyone asks for a production number: I won't extrapolate one from a free demo.

---

## Slide 20 — Section: Risk, incident and improvements

Risk, incident and improvements. About 10 minutes. What I would escalate, how I'd run the incident, what I'd fix

---

## Slide 21 — Risks

I ranked risks by how often I actually saw them and how much damage they do if nobody notices. Silent ones go to the top: the 8,000 cap, the volume difference, and staleness that looks like a closed market. Queueing without a 429 is next. The FX prints are real but low impact if clients use a proper session calendar.

---

## Slide 22 — Incident drill

The scenario is invented, the numbers are real. A quant client's nightly reconciliation flags the 18:00 hour. In the first fifteen minutes I reproduce it from public endpoints, count how many hours are affected, check five-minute against one-minute, and escalate with the CSV and one clear question. The client message gives facts and a next-update time. It doesn't guess a cause and it doesn't offer tho=true, because I never tested it.

---

## Slide 23 — Improvements

Three proposals. The technical one matters most, because a truncated flag fixes the silent cap with an additive JSON field. Monitoring: the scripts I wrote are most of a probe already; what's missing is wiring and a session calendar. Documentation is the cheapest: one page, and my report is the draft.

---

## Slide 24 — Corrections

I'd rather show you this than have you find it. Each of these was in an earlier draft. The offline re-check caught all four, and every slide today uses the corrected numbers.

---

## Slide 25 — Open items

If you ask what I didn't verify, this is the answer. Pass 2 and the logger are only waiting on the clock. The volume cause is blocked because the demo doesn't serve TimeAndSale history. The rest I simply didn't run, and I'm not going to present them as results.

---

## Slide 26 — Questions

That's it from me. If you ask whether the 8,000 cap is just a quota: possibly, and the missing signal is still the defect. If you ask about production capacity: the monitoring design transfers, the numbers don't.

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

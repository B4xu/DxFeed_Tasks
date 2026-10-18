# Executive summary — dxFeed Support Engineer assessment (Tasks A, B, C)

Work done Friday 2026-10-16, 11:00–12:20 UTC, from Tbilisi (UTC+4), using only public dxFeed
demo endpoints and public exchange pages. Everything below is reproducible from the scripts
and raw evidence in `deliverables/`; the running `worklog.md` records decisions and dead ends.

## What was delivered

**Task A — trading-holiday scraper** (`taskA_holidays/`). Four adapters (NYSE, NASDAQ, OPRA,
CME) producing one schema with UTC conversion via `zoneinfo`, a validation suite (weekday,
duplicates, plausible counts, NYSE = NASDAQ, OPRA vs equities, Good Friday = Easter − 2,
run-to-run diff), Google Drive upload by file ID with a Sheets conversion, a GitHub Actions
workflow (weekly cron + manual, retries, Slack alert), 10 offline tests, README and recon notes.
Live run: NYSE 34 rows (2026–2028), NASDAQ 12 rows (2026), OPRA 14 rows (2025 + 1 Jan 2026),
NYSE = NASDAQ with 0 differences, all checks PASS except documented WARNs.

**Task B — incident investigation** (`taskB_incident/answer.md`). Ordered investigation
plan with five ranked hypotheses and the signal that confirms or rejects each, mitigations
with risks, an escalation decision at T+30 (yes: service owner, DB/platform on-call, incident
commander; with the exact content), and three preventive improvements classified by
detection / impact / recurrence.

**Task C — demo assessment** (`taskC_assessment/report.md`, five parts) and
`presentation_outline.md` for the 45-minute session.

## What was verified (strongest findings)

1. The demo feed is **15-minute delayed** (quote age 900.8 s median on every instrument,
   identical on REST, SSE and Radar).
2. **Retention is silently limited to ~8000 candles per symbol and period** (≈ 8 trading
   days of 1m, ≈ 7 weeks of 5m); older windows return `status: OK` with zero candles, which
   looks exactly like a holiday.
3. **Hourly US-stock candles disagree with Σ1m/5m volume, mostly outside regular hours**
   (AAPL: 131/208 = **130 ETH + 1 RTH**; TSLA: 120/208 = **118 ETH + 2 RTH**; the AAPL and
   TSLA RTH exceptions fall on the same day and hour, 2026-10-08 11:00 ET, opposite sign). On
   the one day with a daily candle (2026-10-14) the **hourly** sum (-0.13 %) is closer to the
   daily total than the 1m sum (-0.15 %), so we do **not** yet say which series is the
   reference. TimeAndSale is unavailable; the SPY/MSFT check and a `tho=true` test were
   **not done** (need live API). Cause is a hypothesis.
4. **EUR/USD has 50 of 8000 one-minute candles outside the FX session** (39 of 5m), the
   headline metric. Split (New York clock): 7 after the Friday 17:00 ET close, 0 on Saturday, 43
   Sunday pre-open sparse prints (14:00-17:00 ET plus one single tick). The earlier "214
   weekend" figure counted the legitimate Sunday reopen and is withdrawn; ES has 0 outside
   session.
5. **Load: the service queues instead of rejecting.** Throughput through request completion
   is flat: pre-market ~1.55-1.68 req/s (c=5/10/25), market hours ~3.18/3.19/3.02/2.78 req/s
   at c=5/10/25/50 (about 2x pre-market, not rising to 4.6). The client pool limit (52) is
   above the max concurrency (50) so it could never bind; per-IP throttle versus shared
   capacity is **unresolved** (second client not run). Candle requests queue longer than
   quotes at high c; percentiles are censored (completed requests only). 0 HTTP errors, no
   429, quote age ~900 s.
6. Price integrity is **good but not perfect**: 58,315 candles, 21 boundary duplicates with 0
   conflicts, 0 out-of-order; 1h-from-5m OHLC differs on 6 candles (AAPL close 333.35 vs
   333.3015 on 2026-10-02T21:00Z; TSLA open/close; ES and EUR/USD close on the forming
   candle). The first hourly bar is 00:00 ET (AAPL serves 00:00-19:59 ET).
7. Edge cases clients must know: FX candles only with `price=bid` and `volume` = tick count;
   daily candles stamped 00:00 UTC; `toTime` inclusive; unknown symbols wait ~3.3 s (29 s under load) and return
   HTTP 200 `TIMED_OUT`; SSE candle subscriptions inside the delay window emit NaN control
   events dated 2038-01-19; Radar lists symbols (NVDA, TSM) the REST demo does not serve.

## What was not verified / labelled hypothesis

- Root causes of findings 2–4 are hypotheses with proposed discriminating tests
  (`report.md`, Part 1).
- Market-hours load/SSE/Radar **completed** 13:47–13:58Z (in addition to the earlier
  pre-market runs). RTH volume-mismatch root cause and TimeAndSale sale conditions remain
  unverified on this demo.
- Pass 2 (post-weekend candle re-pull) and the weekend logger analysis are scheduled for
  **Monday 2026-10-19 after 15:30Z** (not run yet — still Saturday). Logger restarted
  2026-10-17T13:01Z via `setsid` (PID **15513**; prior PID 32829 had stopped); logs append;
  collection gap ~Fri 14:49Z→Sat 12:57Z.
- Google Drive upload ran in `DRY_RUN` only (no Google account available).
- Playwright fallback for nasdaq.com was not exercised (nasdaqtrader.com succeeded).
- CME holidays: cmegroup.com blocks automated clients and its terms forbid scraping, so the
  adapter reads operator-downloaded files; no CME rows were produced.
- OPRA has not published its 2026 PDF, so OPRA-vs-equities could only be checked for 2025.

## What the user must do manually

1. **Google credentials:** create a service account, share a Drive folder with it, set
   `GOOGLE_SERVICE_ACCOUNT_JSON` (or `GOOGLE_APPLICATION_CREDENTIALS`) and `GDRIVE_FOLDER_ID`,
   then run `python -m scraper.run --upload` in `taskA_holidays/` (and add the same secrets plus
   `SLACK_WEBHOOK_URL` to the GitHub repository for the workflow).
2. **CME:** download the equity-index holiday PDFs or fill the CSV template into
   `taskA_holidays/input/cme/` and rerun.
3. **Monday after 15:30Z:** run pass 2 and the logger analysis
   (`taskC_assessment/report.md`, "Open items") and paste the results into Part 1's weekend
   section.
4. **Presentation:** rehearse the two live demos in `presentation_outline.md`; both have
   offline fallbacks in `evidence/`.

No credentials or secrets are stored anywhere in `deliverables/` (checked with a grep for key
material and tokens before finishing).

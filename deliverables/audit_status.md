# Audit status — dxFeed Support Engineer application package

Audited 2026-10-16 ~12:30 UTC against `Support_engineer_Assesment.pdf`, `Incident_investigation.pdf`, and the Task A holidays brief in the original agent prompt. Deliverables were read and cheap offline scripts were re-run on stored evidence; **no new requests were sent to the dxFeed demo service**.

---

## Summary

The package is **substantially complete for Tasks B and C Parts 1–5 and for Task A core scrape/validate**. Remaining gaps: **pass 2 / weekend freeze analysis** (logger restarted Sat 2026-10-17 ~13:01Z via `setsid`, PID **15513**, until Mon 2026-10-19 15:30Z; gap Fri 14:49Z→Sat restart), Drive DRY_RUN, CME 0 rows, OPRA 2026 PDF absent (CDN 403 as of Sat probe). Market-hours load/SSE/Radar **done** 13:47–13:58Z.

**Follow-up pass (2026-10-16 ~13:45–14:00Z, minimal demo traffic):**
1. Little's law: L≈configured c at c=5/10; aiohttp `TCPConnector(limit=52)`, `limit_per_host=0` — limit 52 >= max c 50, so the pool could never bind; **per-IP vs shared capacity unresolved** (second client not run) (`evidence/load/*/littles_law.md`).
2. Re-fetch AAPL+TSLA 1h @ 2026-10-08 15:00Z at 13:46Z and 13:57Z (+11.5 min): **stable** vs pass1 (no continuing late update).
3. TimeAndSale/Trade narrow probes: TIMED_OUT or empty — **limitation**; hypotheses not testable on demo REST.
4. Market-hours load (504 req), SSE (1308 events), Radar 1m compare; pre-market vs RTH table in `report.md`.
5. RTH mismatch counts: AAPL **1**, TSLA **2**.

---

## Checklist table

Status legend: **DONE** | **PARTIAL** | **MISSING** | **UNVERIFIED**

### Format / cross-cutting

| requirement | status | evidence location |
|---|---|---|
| Written report | DONE | `taskC_assessment/report.md` (Parts 1–5); `taskB_incident/answer.md`; Task A README + outputs |
| Supporting materials (scripts, screenshots, diagrams) | DONE | `taskC_assessment/scripts/`, `evidence/plots/`, `evidence/radar/*.png` |
| 45-minute live presentation outline | DONE | `presentation_outline.md` (timing + speaker notes + demos + Q&A) |
| Executive summary | DONE | `executive_summary.md` |
| Worklog of decisions / dead ends | DONE | `worklog.md` |
| Public demo tools only (no fabricated results) | DONE (with caveats below) | Open items and hypotheses labelled; one numeric overclaim flagged |

### Task A — trading holidays scraper

| requirement | status | evidence location |
|---|---|---|
| Recon of NASDAQ, NYSE, CME, OPRA (URL, type, years, robots/terms) | DONE | `taskA_holidays/recon.md`, `raw/_recon_2026-10-16/` |
| One adapter per exchange, common schema | DONE | `scraper/adapters/{nyse,nasdaq,opra,cme}.py`, `schema.py` |
| Parse/normalize (footnotes, early close, DST→UTC) | DONE | `normalize.py`; UTC DST check in tests |
| Validation report (weekday, dups, counts, NYSE≈NASDAQ, OPRA flag, Good Friday, run diff) | DONE | `output/validation_report.md` (Overall WARN) |
| Sample output CSV (combined + per exchange) | DONE | `output/trading_holidays_*.csv` (60 data rows + header) |
| Upload to Google Drive (CSV + Sheet, overwrite by ID) | PARTIAL | Code in `upload_drive.py`; only `DRY_RUN` in `output/upload_manifest.json` |
| Automate (cron/Actions, retries, failure alert) | DONE | `.github/workflows/holidays.yml` (cron + Slack secret) |
| Tests | DONE | `tests/` — 10 passed offline (re-run this audit) |
| README (setup, scope, limits, add exchange) | DONE | `taskA_holidays/README.md` |
| CME calendar scraped live | MISSING / intentional | CME 0 rows; `MANUAL_INPUT_REQUIRED`; Terms forbid scraping |
| NASDAQ via nasdaq.com Playwright fallback | UNVERIFIED | Documented; nasdaqtrader.com used live (12 rows) |
| OPRA 2026 calendar | PARTIAL | 2025 PDF + Jan 1 2026 spill only; no 2026 PDF |

### Task B — incident investigation

| requirement | status | evidence location |
|---|---|---|
| 1. Investigation plan (order, first checks, scope/impact, hypotheses, why) | DONE | `taskB_incident/answer.md` §1 |
| 2. Escalation decision at T+30 (yes/no, whom, when, what to include) | DONE | §2 |
| 3. 1–3 preventive improvements (problem, why, impact/detection/recurrence) | DONE | §3 (three items) |

### Task C Part 1 — Data consistency

| requirement | status | evidence location |
|---|---|---|
| 3 instruments: US stock, FX, high-vol | DONE | AAPL, EUR/USD (`price=bid`), TSLA (+ ES control) — `report.md` Part 1 Methodology |
| Crypto as high-vol if required by brief | PARTIAL | Demo serves no crypto; TIMED_OUT documented; TSLA substituted |
| Retrieve 1m, 5m, 1h | DONE | `evidence/candles/pass1/*_{1m,5m,1h}.*` |
| 5m consistent with aggregated 1m | DONE | `evidence/validation/pass1/report.md` (~0.1% edge-bucket mismatches) |
| 1h consistent with aggregated 5m | DONE (finding) | Same report: AAPL 131/208, TSLA 120/208 volume mismatches |
| Gaps | DONE | Series checks + missing runs in validation report |
| Timestamp irregularities | DONE | 0 misaligned / 0 out-of-order in pass1; 21 boundary duplicates, 0 conflicts (`recheck.json`) |
| Weekends handled consistently | DONE / PARTIAL | EURUSD **50 outside-session 1m** (39 5m; was mis-stated as 214 UTC-weekday), ES 0, equities 1m = 0; weekend **freeze** over Sat–Mon still pending logger+pass2 |
| Partial candles returned | DONE | `last open at fetch` column; forming-candle SSE/REST notes |
| ≥3 anomalies + hypotheses + impact | DONE | Anomalies 1–5 in `report.md`; impact section |
| Report structure: Methodology, Tools, Findings, Screenshots, Hypotheses, Impact | PARTIAL | Has Methodology / Tools / Findings / Impact / plots; hypotheses embedded in anomalies (no top-level Hypotheses heading) |
| Historical vs Radar/streaming | DONE (pre-market) | `evidence/radar/`, `evidence/sse/`; market-hours repeat not done |
| Second pass after weekend | MISSING | No `evidence/candles/pass2/` |
| Use Task A holidays in gap/holiday analysis | DONE | Holidays section in validation report |

### Task C Part 2 — Load

| requirement | status | evidence location |
|---|---|---|
| Burst / parallel traffic multi-symbol | DONE | `scripts/load_test.py`, `evidence/load/premarket_fri/` |
| Latency distribution | DONE | p50/p95/p99/max per step |
| Error rate | DONE | 0 HTTP errors; some `TIMED_OUT` (AUD/USD) |
| Response consistency | DONE | Fixed-window bodies byte-identical |
| Rate limiting / caching / stale / symbol quirks | DONE | No RL headers; no cache headers; freshness ~900s; AUD/USD TIMED_OUT |
| What fails / degrades first; graceful?; linear vs exponential | DONE | Latency first; graceful success / ungraceful no backoff; p50 linear R² 0.867 |
| Monitoring metrics, SLOs, escalation triggers | DONE | `report.md` Part 2 end |
| Run during US market hours | PARTIAL | Explicitly **pre-market**; open item documents RTH repeat |
| Politeness / not DoS | DONE | Caps, auto-stop p50>8s, think time, limits stated in report |

### Task C Part 3 — Risk review

| requirement | status | evidence location |
|---|---|---|
| Risks: integrity, latency, staleness, silent failure, monitoring blind spots | DONE | Part 3 table (7 rows covering all) |
| Each: detection, mitigation, escalation | DONE | Same table columns |

### Task C Part 4 — Incident simulation

| requirement | status | evidence location |
|---|---|---|
| Realistic scenario from findings | DONE | INC-SIM-01 from Anomaly 2 |
| Incident analysis | DONE | §4.1 |
| Client communication | DONE | §4.2 |
| Internal escalation note | DONE | §4.3 |
| Post-mortem outline | DONE | §4.4 |

### Task C Part 5 — Improvements

| requirement | status | evidence location |
|---|---|---|
| Exactly 3: technical, monitoring, documentation | DONE | Part 5 |
| Each: problem, solution, complexity, business impact | DONE | All four present (+ trade-offs) |

---

## Findings robustness table

Offline re-runs: `validate_candles.py --pass pass1`, `analyze_load.py --run premarket_fri`, direct CSV/JSONL checks. Numbers that match are marked **reproduced**.

| finding (from executive_summary) | raw support | numbers match? | strongest alternative explanation | report addresses alternative? |
|---|---|---|---|---|
| 15-min delay (~900 s quote age) | `evidence/weekend_logger/poll_log.jsonl`; SSE ages ~900–930 s | **reproduced** (AAPL median ~906 s over 78 polls in this audit) | Client clock skew; measuring delayed *demo* product by design | Yes — labelled expected demo delay |
| ~8000-candle silent retention | `candles/pass1` series n≈8000; `probe` `cap_test` / `cap_test_before_edge` (bytes 15 = empty OK) | **reproduced** | Client window too large; chunking artifact; demo quota separately from retention | Yes — before-edge empty OK distinguishes retention; still OK that it may be intentional quota |
| Hourly US stock volume ≠ Σ5m/1m mostly outside RTH (AAPL 131/208 = 130 ETH + 1 RTH, up to ~−98%) | `validation/pass1/agg_AAPL_1h_from_5m.csv`; raw `candles/pass1/AAPL_{1m,5m,1h}.csv`; report.md Anomaly 2 | **131 mismatches reproduced**; RTH row 2026-10-08 11:00 ET: OHLC match; vol_rb 2 191 318 > vol_sv 2 148 474 (~+1.99%); 1m≡5m; bid+ask=volume both sides | Per-period ETH filters; late prints/corrections (opposite RTH sign); `tho`/price-type artefact (weak) | **Yes** — exception stated; three hypotheses with for/against; Alternatives paragraph |
| EUR/USD out-of-session 1m candles (Fri 7 / Sat 0 / Sun pre-open 43 = 50; earlier "214" withdrawn) | `EURUSD_1m.csv`; validation `candles_outside_session` | **reproduced** (50 / 39 for 5m; 214 is the UTC-weekday tag incl. 170 legitimate Sunday-reopen candles) | Indicative/off-hours liquidity; bid-candle from quote updates; timezone labelling | Yes — hypotheses A/B; logger test proposed |
| Load: queueing; client pool ruled out by Little's law; RTH faster than pre-market | `load/premarket_fri/` + `market_hours_fri/` + `littles_law.md` | **reproduced**; L≈c at c=5/10; MH thr 3.18/3.19/3.02/2.78 rps through completion (3.3–4.6 withdrawn: start-to-start artefact) | Server/shared-demo capacity (varies by time of day); cold start; think time | Yes — pool limit 52 >= c 50 so not binding; per-IP vs shared unresolved; comparison table |
| Price integrity / holidays / DST | validation report | **partly reproduced**: 58,315 candles, 0 misaligned; OHLC differs on 6 hourly-from-5m candles; first 1h bar 00:00 ET | Expected session calendars | Yes |
| FX `price=bid` only; volume≈count | Methodology + validation NaN fields | Supported | Documented CandlePrice semantics | Yes |
| SSE NaN / 2038-01-19 sentinel | `sse/20261016T120829Z/sse_events.jsonl` (2× 2038 candles); earlier run 6× | **reproduced** | Snapshot/REMOVE control events (`eventFlags` 14/2); subscribe `fromTime` inside delay window | Yes — framed as control messages + client footgun |
| Radar == REST last candle (delayed) | `evidence/radar/compare_1m_*.json` + screenshots | Supported for sampled symbols | Radar UI rounding; different session | Yes for 1D/1m samples |
| “Equity series have no weekend candles” | 1m: 0; **1h validation lists 9 AAPL weekend** | **PARTIAL** | Those 1h “weekend” rows are **UTC Saturday 00:00** = Friday evening ET — calendar artifact, not Sat trading | Report oversimplifies; validation UTC weekend flag not explained |

---

## Quality and risk review

**Absolute-claim sweep (corrected this pass)**

| claim (before) | where | verdict | change |
|---|---|---|---|
| “0 of 208 during 09:00–15:00 ET” / “all … match exactly” / “none were observed” / “RTH never differs” | report Anomaly 2, §4.1–4.3, exec summary, presentation slide 8 + Q&A, worklog | **False** — 1 AAPL RTH mismatch; TSLA has 2 | Rewrote to 130 ETH + 1 RTH; exception investigated |
| “5m always matches 1m” | report Anomaly 2 | **Overstated** — 2 edge buckets per series | Softened to “complete buckets” |
| “Equity series have no weekend candles” | report findings | **Overstated for 1h** — UTC Sat 00:00 = Fri ET | Clarified 1m vs 1h UTC labelling |
| “Latency grows linearly with concurrency” | report Part 2, Part 3 risk #3, exec #5, presentation slide 14, worklog | **Overstated** — roughly linear to c=10, sublinear at c=25; p95 not linear | Reworded + throughput numbers + server vs client cap |
| Real-time/load “only 13:30–20:00Z” | presentation slide 1 | **False for executed work** | Aligned with pre-market execution |
| Methodology “Both comparisons are repeated during US market hours” | report §1.5 | **False** — not done | Changed to pre-market + Open items |
| “never says so in the response” (truncation) | Anomaly 1 | **Kept** — verified OK/empty | — |
| “service never tells the client to slow down” | Part 2 | **Kept** — no 429 / Retry-After in runs | — |
| “0 duplicates / 0 misaligned / 0 NaN OHLC” | findings, exec | **Kept** — validation reproduced | — |
| Task A “Credentials never live in the repo” | README | **Kept** — procedural | — |

**Previously flagged overstatements — status:** items 1–3 above are **fixed**. Remaining risks are open work (pass 2, market-hours load), not wording.

**Hypotheses presented carefully enough?** Yes — Anomalies 1–3 and the RTH exception labelled hypothesis; Alternatives paragraphs on all five headline findings.

**Not fully reproducible yet**

- Pass 2 / Monday reopen / weekend freeze behaviour.
- Live Google Drive upload; Playwright nasdaq.com path; CME rows.
- Market-hours load comparison dataset.

**Inconsistencies between files**

- Exec summary delay “900.8 s median” vs logger analysis regenerating over longer polls (~905–906 s) — same order; cite a specific analysis snapshot.
- Validation `AAPL 1h` weekend=9 vs prose “equities have no weekend candles” — clarify ET vs UTC.
- Report Methodology §5 says Radar/SSE “repeated during US market hours” — that repeat did **not** happen.

**Load-test abuse risk**

- Report states shared-demo limits, auto-stop, request counts (~144 + 35 + 24), no 429, politeness. Risk of being read as abusive is **low** if you lead with those numbers; avoid implying production capacity.

**Structural nit for PDF Part 1 deliverable**

- Add a short **Hypotheses** subsection or rename “Anomalies” to include “Hypotheses” so the rubric maps 1:1.

---

## Remaining work (prioritized)

| # | what | why | effort | needs you manually? | deadline |
|---|---|---|---|---|---|
| 1 | ~~Correct Anomaly 2 RTH wording~~ | **DONE** (this pass) | — | — | — |
| 2 | ~~Align presentation slide 1 / load linear claim / Alternatives ×5~~ | **DONE** (this pass) | — | — | — |
| 3 | **Keep logger running**; after **2026-10-19 15:30Z** run pass2 + `validate_candles` + `analyze_logger` | Weekend freeze / reopen / pass1 vs pass2 | 1–2 h compute + write-up | Yes | **Mon 2026-10-19 after 15:30Z** |
| 4 | ~~Market-hours load + SSE + Radar~~ | **DONE** 13:47–13:58Z | — | — | — |
| 5 | **Google Drive real upload** (credentials + folder ID) | Completes Task A Step 5 | 30–60 min once creds exist | Yes (service account) | Whenever creds available |
| 6 | **CME manual files** into `input/cme/` + rerun | Removes CME WARN; shows honesty on Terms | 30–60 min | Yes (download PDFs/CSV by hand) | Nice-to-have |
| 7 | **OPRA 2026 PDF** when published | Enables OPRA vs equity year overlap | Low when PDF exists | Yes (re-run scraper) | When OPRA publishes |
| 8 | **Exercise Playwright fallback** once (optional) | Closes UNVERIFIED nasdaq.com path | 30–60 min + Chromium install | Optional | Low priority |
| 9 | Rehearse two live demos + fallbacks offline | Presentation readiness | 1–2 h | Yes | Before interview |
| 10 | Optional: Anomaly 2 TimeAndSale / re-fetch discriminating test | Strengthens RTH-exception root cause | 1–3 h | May need live demo API | After Mon open items |

Known open items status at audit:

| open item | status now |
|---|---|
| Logger until Mon 15:30Z | **Restarted** 2026-10-17T13:01Z via `setsid -f` — PID **15513** (pidfile `tmp/weekend_logger.pid`); append-only; gap ~Fri 14:49Z→Sat 12:57Z; poll_log 704+ |
| Pass2 / analyze_logger after logger | **Waiting** — do Mon 2026-10-19 after 15:30Z (today is Sat) |
| Market-hours load/SSE/Radar | **DONE** (`market_hours_fri`, SSE `20261016T135132Z`, Radar compare) |
| Drive upload | **DRY_RUN only** — no `GDRIVE_FOLDER_ID` / SA creds in env |
| Playwright nasdaq.com | **Skipped** — `playwright` not installed in `dxfeed` env |
| CME manual files | **Empty / README only** — no operator PDFs provided |
| OPRA 2026 PDF | **Absent** — HEAD `2026_HOLIDAY_SCHEDULE.pdf` → 403; 2025 → 200 (2026-10-17) |

---

## Presentation readiness

**Fit to 45 minutes:** Outline allocates 5+15+8+7+5+5 = 45. Content-dense (23 slides + demos); risk of overrun on Part 1. Cut slide 10 edge-case table if short on time; keep Anomalies 1–3.

**Live demos with fallbacks:**

| demo | live path | fallback | ready? |
|---|---|---|---|
| 8000 retention | REST long `fromTime` | `chunks.jsonl` + raw bodies | Yes |
| 1h vs 5m rebuild | `validate_candles.py --pass pass1` offline | PNG + `agg_AAPL_1h_from_5m.csv` | Yes — **use CSV row that shows ETH −98% and acknowledge the one RTH row** |
| Radar 1m (optional) | radar.dxfeed.com | `evidence/radar/*` | Yes for screenshots |

**Slide 12 (pass 2)** will be empty until Monday — say so up front.

### Ten hardest questions (one-line answers grounded in evidence)

1. **Isn’t the 8000 limit just demo quota?** — Observation is silent `OK` + empty older windows (`cap_test_before_edge` bytes=15); whether quota or retention, the client-visible defect is no truncation signal.
2. **Did you really find zero RTH volume mismatches?** — No: one AAPL hour 2026-10-08 11:00 ET differs (~2%, opposite sign); wording corrected to 130 ETH + 1 RTH.
3. **Could ETH volume gaps be `tho` / session attributes?** — Possible; default symbols were used without `tho=true`; discriminating test is re-request with `tho=true` and TimeAndSale sale conditions (proposed, not run).
4. **Are weekend EUR/USD bars real trades?** — Unknown; they are bid-candle ticks (`price=bid`); may be indicative quotes — labelled hypothesis.
5. **Why trust linear latency with n=6 at c=1 and a 26 s cold start?** — p50 roughly linear to c=10, sublinear at c=25; could be server-side cap or client-side limit; p95 is not linear.
6. **Doesn’t load-testing a public demo look abusive?** — Hard stops (p50>8s, budget), 144+ requests, no 429, think time; report states shared-demo limits.
7. **You skipped US market hours — isn’t that fatal?** — Weakens Part 2 representativeness; historical Part 1 stands; RTH repeat is the next experiment.
8. **Where is freeze behaviour over the weekend?** — Logger is still collecting; analysis after Mon 15:30Z — not in the report yet.
9. **Radar shows NVDA; REST times out — which is wrong?** — Different demo symbol universes; documented, not called a data bug.
10. **Would this matter in production?** — Delay/retention may be demo-only; **silent OK**, **cross-timeframe volume**, and **queue-without-429** are the transferable operational lessons.

---

## Audit method note

- Re-ran offline: `pytest taskA_holidays/tests` (10 passed), `validate_candles.py --pass pass1`, `analyze_load.py --run premarket_fri`, CSV/JSONL spot checks including AAPL 2026-10-08 11:00 ET raw 1m/5m/1h rows.
- Did **not** call demo endpoints (claim-correction pass also offline-only).
- Files updated this correction pass: `taskC_assessment/report.md`, `executive_summary.md`, `presentation_outline.md`, `worklog.md`, `audit_status.md`.

### Could not verify offline

- Root cause of the RTH exception (needs TimeAndSale / re-fetch — not run; no demo traffic).
- Whether load plateau is server- vs client-side (needs a second client — not run).
- Market-hours load/SSE/Radar behaviour; pass 2 / weekend freeze (logger still running).
- TSLA RTH hours fully dissected at 1m/5m row level (counts confirmed in agg CSV only).


## Correction log (offline recheck, 2026-10-18)

See `taskC_assessment/evidence/recheck/recheck.json`. Corrected: weekend headline 214 -> 50 outside-session (39 5m); OHLC not 100 % clean (6 hourly-from-5m differences); ETH defined as outside 09:30-16:00 ET with AAPL hours 00:00-19:59 ET; volume advice withdrawn pending reference-series decision (hourly closer to daily on 2026-10-14); throughput through completion (market hours 3.18/3.19/3.02/2.78; pre-market 1.63/1.56/1.68); Little's law softened; candle count 58,315; retention about 8000 (8000/8001). Not done (needs live API): SPY/MSFT RTH check, `tho=true`, burst, batching, second client.

# dxFeed demo services — L2 Support Engineer assessment report

Author: acting L2 Support Engineer candidate. Work performed 2026-10-16 (Friday) from Tbilisi
(UTC+4); all timestamps below are UTC unless marked ET (America/New_York, UTC−4 until
2026-11-01). Every number in this report is produced by a script in `scripts/` from raw
responses stored in `evidence/`; the request log for each activity (`requests.jsonl`) records
the exact URL, parameters, UTC time, latency and body hash of every call.

Status legend used throughout: **verified** = reproduced from saved evidence; **hypothesis** =
plausible explanation not yet proven; **unverified** = could not be checked in this environment.

---

## Part 1 — Data consistency and integrity

### Methodology

1. **Endpoint discovery.** `https://tools.dxfeed.com/webservice/rest/help` redirects (301) to
   `https://demo.dxfeed.com/webservice/rest/help`, which documents two resources: `events.json`
   (snapshot; parameters `events`, `symbols`, `fromTime`, `toTime`, `timeout`) and `eventSource`
   (Server-Sent Events). Candle symbol syntax comes from the public Javadoc
   (`CandleSymbol`): `<base>{=<period>[,price=bid|ask|mark|s][,tho=true][,a=s]}` — e.g.
   `AAPL{=5m}`, `EUR/USD{=m,price=bid}`. The Javadoc also warns that "the demo system is
   limited to a subset of symbols and aggregation periods". Saved copies: `evidence/docs/`.
   Practical notes found while probing (verified): curl strips the `{}` from the symbol unless
   `-g` is used; the server normalises `{=1m}` to `{=m}` in `eventSymbol`; a symbol the demo
   does not serve makes the request wait for the server-side timeout (~3.3 s idle, up to ~29 s under load) and return
   `{"status":"TIMED_OUT"}` with HTTP 200; `timeout=0` on a fresh subscription returns
   `{"status":"NOT_SUBSCRIBED"}`.
2. **Instrument selection** (verified against `Quote` snapshots, `evidence/probe/`):
   - **AAPL** — US stock: most liquid US equity, served with full extended hours
     (the demo serves hourly bars from **00:00 to 19:59 ET**, see "Session model" below), so both
   regular and extended-session behaviour can be studied.
   - **EUR/USD** — FX pair: most liquid pair. The demo returns **zero candles** for
     `EUR/USD{=1m}` (status OK) and data only for `EUR/USD{=1m,price=bid}`; this itself is an
     edge case (see Anomaly 4).
   - **TSLA** — high-volatility instrument: the demo serves **no crypto** (BTC/USD, ETH/USD and
     exchange-suffixed variants all `TIMED_OUT`), nor NVDA, META, QQQ, TQQQ, UVXY, IBIT, GME,
     COIN or MSTR. TSLA is the most volatile liquid name that is served.
   - **/ESZ26:XCME** — added as a near-24-hour control (CME E-mini S&P, Sun 18:00 → Fri 17:00 ET)
     because no 24/7 instrument exists on the demo.
3. **Two-pass retrieval.** Pass 1 (`scripts/fetch_candles.py --pass pass1`, 11:34–11:37Z,
   96 requests) pulled 1m, 5m and 1h candles for all four instruments. Requests are chunked
   (1 day for 1m, 4 days for 5m, 60 days for 1h) because of the 8000-candle cap described in
   Anomaly 1. Range: 1m/5m from 2026-10-02 (covering the weekends of Oct 3–4 and Oct 10–11 and
   Columbus Day, Oct 12, on which equities trade), 1h from 2026-01-01 (covering all seven NYSE
   2026 holidays to date, taken from the Task A calendar, and the US DST change of
   2026-03-08). Pass 2 is to be run after the weekend logger finishes (Monday 2026-10-19 after
   15:30Z) with `--pass pass2`; see "Open items".
4. **Validation** (`scripts/validate_candles.py`): duplicate and out-of-order timestamps
   (both after merging and inside each raw response), alignment to interval boundaries, gaps
   inside the expected session, candles outside the session (the headline anomaly count; the
   UTC-weekday "weekend" tag is kept as a legacy column only), zero-volume candles, frozen OHLC runs, NaN fields, partial last candle, holiday behaviour, DST, and
   aggregation consistency (5m rebuilt from 1m — open of first, max high, min low, close of
   last, sum of volume — versus served 5m; 1h rebuilt from 5m versus served 1h). Output:
   `evidence/validation/pass1/report.md|json`, per-candle comparison CSVs, plots in
   `evidence/plots/pass1/`.
5. **Streaming and Radar comparison.** `scripts/sse_compare.py` subscribes via `eventSource`
   and polls REST in parallel; Radar (`https://radar.dxfeed.com`, "Last Candle" preset) was read
   manually and compared with REST daily candles (`evidence/radar/`). Repeated
   **pre-market and during US RTH** (13:47–13:58Z load/SSE/Radar).
6. **Weekend logger** (`scripts/weekend_logger.py`, started 11:11:20Z, 60 s cadence, runs until
   2026-10-19 15:30Z) records the latest quote and 1m candle age for all four instruments; it is
   analysed by `scripts/analyze_logger.py`.

### Tools

Python 3.12 (`requests`, `aiohttp`, `pandas`, `matplotlib`), the demo REST and SSE endpoints,
Radar in a browser, the Task A holiday calendar (`taskA_holidays/output/trading_holidays_combined.csv`).
No credentials; a single client; ≥1 s spacing for sequential pulls; automatic stop on repeated
429/5xx.

### Findings

The five headline findings (feed delay; silent 8000 retention; 1h-vs-5m volume; FX weekend
ticks; load queueing) each end with an **Alternative explanations considered** paragraph
covering documented behaviour, request parameters (session / price type), client-side limits,
and pre-market timing. Supporting checks (series integrity, DST, aggregation table, Radar)
follow without that paragraph.

**Feed delay (verified).** The quote age measured against the wall clock is 900.8–904.9 s
(p10–median) for every instrument over 41 polls (`evidence/weekend_logger/analysis.md`), and the
newest 1m candle is ~15–16 minutes old. The demo feed is therefore **15-minute delayed**
(dxFeed staff describe the Radar demo publicly as "delayed data"; the exact 900 s figure is our
measurement). This is expected behaviour, but it matters for every
freshness number below: "fresh" on the demo means "about 900 s old".
*Alternative explanations considered:* Documented demo delay (Radar marketing) fits the data;
clock skew on the client would not produce the same ~900 s floor on every symbol and on both
REST and SSE; request parameters (`timeout`, `fromTime`) do not affect Quote `bidTime`;
pre-market timing does not change the delay magnitude (same ~900 s in logger and load runs).

**Series integrity (verified, pass 1).** Across 12 series (4 instruments × 3 periods, **58 315**
candles; `evidence/recheck/recheck.json`): 0 duplicate timestamps, 0 timestamps off the
interval boundary, 0 responses with out-of-order candles, 0 zero-volume candles, 0 candles with
high < low or open/close outside [low, high], 0 NaN OHLC. **Timestamp and structure integrity is
clean; price agreement across timeframes is almost, but not perfectly, clean** (see the
aggregation table: a few complete-bucket OHLC differences exist in extended hours). Frozen OHLC
runs exist only where expected (thin pre-market trading; longest run 4 one-minute candles on
AAPL). Equity **1m** series have no UTC-weekend candles; the validation report's "9 weekend"
AAPL **1h** rows are UTC Saturday 00:00 (= Friday evening ET), not Saturday trading. AAPL and TSLA have **zero** hourly candles on all seven NYSE holidays so
far in 2026 (MLK Day, Presidents' Day, Good Friday, Memorial Day, Juneteenth, 3 July, Labor
Day), matching the Task A calendar; EUR/USD trades through all of them (24 hourly candles on
Monday holidays, 18–19 on Friday holidays because FX closes at 17:00 ET on Fridays). The ES
Dec-26 contract has sparse hourly candles before September 2026 because it was not the front
month — missing hours there are absence of trades, not a feed gap (see "Distinguishing defects
from expected behaviour").

**DST handling and session model (verified; corrects an earlier reading).** The first hourly
candle of the New York day for AAPL/TSLA is at 05:00Z on Friday 2026-03-06 (EST, UTC−5) and at
04:00Z on Monday 2026-03-09 (EDT, UTC−4). **Both are 00:00 ET, not 04:00 ET.** AAPL has hourly
bars at every ET hour from **00:00 to 19:00** (20 per day; first candle at 00:00 ET on 195 of
198 days, `evidence/recheck/recheck.json`), so the demo carries an **overnight tail 00:00–04:00
ET** that a "04:00–20:00" pre-market model would wrongly call out-of-session, and has **no
20:00–24:00 ET hours**. Both facts are findings about the demo's session coverage and are not
mentioned in its documentation that we saw. DST is handled consistently (the UTC hour moves by
one, the ET hour does not). 1h candles are aligned to the ET hour boundary and the 1h candle
containing the 09:30 ET open is the 09:00 ET candle (`a=s` session alignment is not the
default).

**Session model used in this report.** *RTH* = Monday–Friday 09:30–16:00 ET. *ETH* (extended
hours) = every other served candle, including the 00:00–04:00 ET tail. Earlier drafts defined
ETH as 04:00–20:00 ET; every ETH/RTH count below uses the corrected definition. The 1h bar
that straddles the 09:30 open (09:00–10:00 ET) is counted as RTH in the AAPL/TSLA mismatch
counts, which is the conservative choice (it can only add RTH mismatches).

**Aggregation consistency (verified).**

| check | compared | candles with any difference | note |
|---|---|---|---|
| check | compared | candles with any difference | candles with an **OHLC** difference | note |
|---|---|---|---|---|
| AAPL 5m from 1m | 1987 | 2 (0.10 %) | 1 | both buckets have `n_src` < 5 (incomplete source) |
| TSLA 5m from 1m | 1818 | 2 (0.11 %) | 2 | both buckets have `n_src` < 5 |
| EUR/USD 5m from 1m | 1617 | 2 (0.12 %) | 2 | both buckets have `n_src` < 5 |
| ES 5m from 1m | 1601 | 2 (0.12 %) | 2 | both buckets have `n_src` < 5 |
| AAPL 1h from 5m | 208 | **131 (63 %)** | **1** | volume: **130** outside RTH, **1** inside RTH (Anomaly 2). OHLC: `2026-10-02T21:00Z` (17:00 ET), **complete** bucket (`n_src` = 12): close 333.35 rebuilt vs 333.3015 served |
| TSLA 1h from 5m | 208 | **120 (58 %)** | **3** | volume: 118 ETH + 2 RTH. OHLC: `2026-10-08T15:00Z` close 371.99 vs 371.9033 and `16:00Z` open 371.90 vs 371.94 (both complete, `n_src` = 12, RTH hours); `2026-10-16T11:00Z` close 374.73 vs 374.74 (forming, `n_src` = 5) |
| EUR/USD 1h from 5m | 265 | 1 (0.38 %) | 1 | `2026-10-16T11:00Z` last (forming) candle, `n_src` = 5: close 1.12581 vs 1.12579 |
| ES 1h from 5m | 242 | 1 (0.41 %) | 1 | last (forming) candle: close 7802.00 vs 7801.75 |

(The OHLC column is recomputed by the patched `validate_candles.py`; the earlier per-field table
in `report.json` shows the same figures: close mismatches AAPL 1, TSLA 2, ES 1, EUR/USD 1 in the
1h-from-5m check, plus one TSLA open.) Where the 1h bar is built from a **complete** bucket,
OHLC does **not** always agree: AAPL has 1 complete-bucket close difference (in extended hours)
and TSLA has 2 (in regular hours on 2026-10-08, the same hour block as the AAPL volume
exception). These are small, real price-level discrepancies (largest relative gap ≈ 0.023 %),
not a clean 100 % agreement. The ES and EUR/USD differences are on the forming 11:00Z candle
(`n_src` = 5) and are expected there.

For 5m versus 1m, the two differences per series are the first bucket (the 1m history starts
mid-bucket because of the retention, so the rebuilt bucket has 1–4 of 5 minutes) and the last
bucket (the 5m series was fetched ~40 s after the 1m series and already contained one more
minute, or the candle was still forming). Every 5m-vs-1m difference sits on a bucket with
`n_src` < 5, so **5m equals Σ1m on every complete bucket**. The hourly volume differences for the
two stocks are a genuine finding (Anomaly 2).

**Partial candles (verified).** The last candle of every series is still forming at fetch time
and is returned without any flag: e.g. the AAPL 1h candle for 11:00Z was returned at 11:34Z
(`last_candle_open_at_fetch = True`). The SSE stream delivers repeated updates for the forming
1m candle (`candle_updates_per_candle` in `evidence/sse/*/summary.json`). `eventFlags` is 0 on
every REST candle; the SSE stream carries `eventFlags=14` (snapshot begin/end + tx-pending bits)
on its first candle message.

**Radar versus REST (verified for 1D at 11:48Z; 1m pre-market 12:05Z and market hours ~13:57Z).**
Radar "Last Candle 1D" values for AAPL, MSFT, AMZN, GOOG and META are identical to the REST
`{=d}` candle for 2026-10-15 (Radar rounds to 3 decimals, e.g. 541.133 vs 541.1331). Radar
lists **NVDA, TSM, SPCX** with candle data while the REST demo returns `TIMED_OUT` for NVDA and
TSM: the two demo tools do not share a symbol universe (`evidence/radar/compare_1D_*.json`,
`compare_1m_market_hours_*.json`).

### Anomalies and edge cases

**Anomaly 1 — silent retention of about 8000 candles per symbol and period (verified).** A 1m
request for 2026-10-02→2026-10-16 returns about 8000 candles (AAPL and EUR/USD exactly 8000;
TSLA and ES 8001 in the merged series), the newest ones, starting 2026-10-05
18:37Z, with `status: OK` and no truncation indicator. The same happens for 5m: EUR/USD 5m
from 2026-08-01 returns exactly 8000 candles starting 2026-09-09, AAPL 5m from 2026-06-01
returns 8000 starting 2026-08-28. Requests for windows entirely before that edge
(AAPL 1m Oct 1–5, EUR/USD 5m Aug 20–Sep 8) return `status: OK` with **zero** candles —
indistinguishable from "market closed". 1h returns 3943 candles back to 2026-01-05, i.e.
a time-based limit applies there. So the demo keeps roughly the newest 8000 candles per
symbol and period (≈ 8 trading days of 1m for stocks, ≈ 5.5 days for FX, ≈ 7 weeks of 5m)
and never says so in the response (`evidence/probe/requests.jsonl`, tags `cap_test*`).
*Hypothesis A* (response-size cap) and *B* (retention) were discriminated by the "before the
edge" requests: B is confirmed; whether an additional response cap exists cannot be tested
because no series holds more than 8000 candles. *Impact:* a backtest or chart that requests
"last two weeks of 1m" silently loses the first week, and a request for older data looks
exactly like a holiday; because every response says OK, nothing alerts the client.
*Alternative explanations considered:* Documented demo limits (Javadoc “subset of …
aggregation periods”) are consistent with a retention bound, but the silent `OK` + empty
body is not documented. Request parameters (`fromTime`/`toTime`, no `tho`) do not create the
cap — windows entirely before the edge still return OK/empty. Client-side truncation is ruled
out (raw bodies contain exactly 8000 events). Pre-market timing is irrelevant (historical
windows).

**Anomaly 2 — hourly stock candles disagree with Σ5m/1m volume, mostly outside regular hours
(verified; one RTH exception).** Of 208 AAPL 1h candles compared to rebuilt-from-5m,
**131 mismatch on volume**. OHLC agrees on all but **one** complete bucket for AAPL (a close
difference of 0.0146 % at `2026-10-02T21:00Z`, 17:00 ET, see the aggregation table), so the
volume split is not accompanied by a price split but price agreement is not perfect either.
**130/131** volume mismatches are outside 09:30–16:00 ET (hours 00:00–09:00 and 16:00–20:00 ET;
every one of the 11 AAPL bars at 00:00, 01:00, 02:00, 03:00 and 04:00 ET mismatches, which is
the overnight tail) and have served 1h volume **greater** than rebuilt (worst −99.1 % at
`2026-10-07T21:00Z` = 17:00 ET: served 743 918 vs rebuilt 6 422; another large case −98.4 % at
18:00 ET on 2026-10-02: served 845 299 vs rebuilt 13 744, `count` 415 vs 271). **1/131 is inside
RTH** — see exception below. TSLA: 120/208 mismatches, **118 ETH + 2 RTH** (the RTH ones are
the 11:00 and 12:00 ET bars on 2026-10-08). 5m matches 1m on every complete bucket (the only
5m-vs-1m disagreements are on incomplete edge buckets).

*Which series is the reference? (volume reconciliation, `scripts/offline_recheck.py`, AAPL).* The
only trading day for which we hold a daily candle is 2026-10-14: daily candle volume **50 061 053**;
Σ1h (served) **49 994 234** (−0.13 % vs daily); Σ1m = Σ5m **49 983 889** (−0.15 % vs daily).
On every other full AAPL day Σ1h is also ≥ Σ1m (by 0.0 %–6 %; largest 2026-10-08 35.26 M vs
33.27 M). On the ETH-hour mismatches the served 1h bar is higher than the rebuilt one in
**130 of 131** hours. Taken together, the served hourly series is **closer to the daily total
on the one day we can check**, and the 1m/5m series looks like the **more likely incomplete**
one (late-reported or consolidated prints that only reach the hourly record). This is a
**hypothesis from one daily point, not a conclusion**; we have not determined which series is
the reference. Consequently we do **not** advise building extended-hours analytics from 1m or
5m volume without checking against hourly/daily totals first.

*RTH exception (AAPL 2026-10-08 11:00 ET = 15:00–16:00Z), from saved pass1 CSVs only:*
| series | n bars | open | high | low | close | volume | count | bidVol | askVol |
|---|---|---|---|---|---|---|---|---|---|
| 1m (sum) | 60 | 337.80 | 338.34 | 337.17 | 338.13 | **2 191 317.95** | **108 531** | 1 093 399.44 | 1 097 918.51 |
| 5m (sum) | 12 | 337.80 | 338.34 | 337.17 | 338.13 | **2 191 317.95** | **108 531** | 1 093 399.44 | 1 097 918.51 |
| 1h served | 1 | 337.80 | 338.34 | 337.17 | 338.13 | **2 148 473.90** | **106 811** | 1 073 655.27 | 1 074 818.63 |

Timestamps agree (candle open `2026-10-08T15:00:00.000Z`). OHLC identical. 1m ≡ 5m on
volume and count. Served 1h is **lower** by 42 844 shares (~**+1.99 %** rebuilt vs served)
and 1 720 trades — **opposite sign** from the ETH pattern. `volume = bidVolume + askVolume`
on both 1m and 1h (both sides lower on 1h). `n_src = 12` (complete hour).

*RTH mismatch counts (pass1 agg CSVs, RTH = 09:30–16:00 ET; the 09:00 ET bar has zero
mismatches so the count is the same under the older 09:00 convention):* AAPL **1** of 208
(11:00 ET on 2026-10-08); TSLA **2** of 208 (11:00 and 12:00 ET on 2026-10-08). **AAPL and TSLA
fall on the same day and overlapping hours**, which points to a market-wide or venue-wide event
or a shared processing quirk rather than a symbol-specific one. Checking SPY and MSFT for the
same hours is **not done** (needs live API calls; open item).

*Stability re-fetch (verified, 2026-10-16).* AAPL and TSLA `{=h}` for `2026-10-08T15:00:00Z`
were re-requested at 13:46:09Z and again at 13:57:36Z (+11.5 min). Volume and count are
**identical** to pass1 (AAPL 2 148 473.90 / 106 811; TSLA 2 053 134.29 / 117 527) on both
re-fetches (`evidence/refetch/refetch_compare.json`). The closed 1h bars are **stable** over
this window — no evidence of continuing late updates after pass1. That neither proves nor
disproves corrections between trade time and the first fetch.

*TimeAndSale probe (limitation).* Narrow REST probes (`TimeAndSale` 2 s window; `TimeAndSale`
without range; `Trade` 2 s window) returned `TIMED_OUT` or OK-with-0-events; a Candle control
for the same hour returned OK. Sale-condition hypotheses **cannot** be tested via demo REST
(`evidence/refetch/timeandsale_probe.json`).

*Hypotheses (≤3) for the RTH exception — not conclusions:*
1. **Per-period inclusion rules** (hypothesis). *For:* ETH pattern systematic; separate
   `Trade.<period>` records in Javadoc; bid/ask/count all lower on 1h. *Against:* does not
   alone predict rebuilt > served inside RTH.
2. **Late prints / corrections before pass1** (hypothesis). *For:* opposite sign; same-day
   TSLA RTH mismatches. *Against:* bars stable on re-fetch after pass1; OHLC identical across
   periods; rare in sample.
3. **Request/session artefact** (hypothesis, weak). *Against:* complete buckets; 1m≡5m; other
   RTH hours match under the same parameters.

*ETH-pattern hypotheses remain open* (different ETH filters vs late ticks). Discriminating
`TimeAndSale` test is blocked on this demo. *Impact:* timeframe-dependent volume (especially
ETH); RTH reconciliations usually clean but not guaranteed (AAPL 1, TSLA 2 in this sample).
*Alternative explanations considered:* Documented separate `Trade.<period>` records support
per-period rules; `tho=true` was not requested; client-side sum errors ruled out (1m≡5m;
bid+ask identity); pre-market fetch timing does not affect these closed bars.

**Anomaly 3 — FX candles outside the FX session: Friday after-close prints and Sunday pre-open
sparse prints (verified; count corrected).** An earlier draft headlined "214 weekend
candles". That number came from tagging candles by **UTC** weekday and is inflated by the
method: **170 of the 214** are Sunday 17:00–19:59 ET (21:00Z onward), when FX **legitimately
reopens**. The correct anomaly count is the validator's `candles_outside_session`:
**50 one-minute candles** (and **39** five-minute candles; hourly is 238 and is dominated by
hourly bars that straddle the session edge, so it is not a headline). The 50 split as:

| bucket (New York clock) | 1m candles | detail |
|---|---|---|
| Friday after the 17:00 ET close | **7** | six at `2026-10-09T21:00–21:05Z` (17:00–17:05 ET), plus one single-tick candle at `2026-10-10T02:30Z` = **Fri 22:30 ET** (bid 1.1202, count 1; this is the "Saturday single" of the UTC view) |
| Saturday (ET) | **0** | no 1m candle falls on a Saturday in New York time |
| Sunday before the 17:00 ET reopen | **43** | one single-tick candle at `2026-10-11T13:20Z` (09:20 ET), then a sparse ramp from 14:00 ET: 2 candles in the 14:00 ET hour, 14 in 15:00 ET, 26 in 16:00 ET |
| Total outside session | **50** | after 17:00 ET Sunday the series is complete (60/hour) |

The five-minute view has the same shape: 4 Friday after-close, 3 Saturday (ET), 32 Sunday
pre-open = 39 (the 5m series is a different aggregation, so its Saturday count is not derived
from the 1m series; cause not investigated). By contrast **ES has 0 candles
outside its session**: its "120 weekend" 1m candles (48 at 5m) are all the **Sunday 18:00 ET
reopen** (22:00Z) tagged by the UTC-weekday method; it stops at 20:59Z Friday and restarts exactly
at 22:00Z Sunday. Equities have no UTC-weekend 1m candles. *Hypothesis A:* the FX
liquidity provider publishes occasional indicative/reference quotes while the market is
closed and the bid-candle aggregator treats each as a tick. *Alternative B:* a replay or
heartbeat message re-stamps a stale quote. *Test:* subscribe to `Quote` for EUR/USD over the
weekend (the running logger does this) and check whether `bidTime` advances while the price is
unchanged (B) or the price moves (A). *Impact:* a daily/weekly candle built from these ticks
gets a spurious Saturday/Sunday bar; gap-detection logic that uses "last candle age" will
report FX as live on Sunday morning; backtests that filter by weekday are unaffected.
*Alternative explanations considered:* Documented FX hours do not include Friday-evening or
Sunday pre-open prints (a reopen at 17:00 ET Sunday is normal and is **not** counted);
requiring `price=bid` is our parameter choice but does not invent out-of-session bars
(equities with default last-price show none). Client-side date bugs are ruled out (raw
`time_iso` times are as listed). Pre-market timing is irrelevant (historical Oct 9–11).

**Anomaly 4 — FX candles exist only as `price=bid`, and their `volume` is a tick count
(verified).** `EUR/USD{=1m}` returns `status: OK` with no candles (indistinguishable from
"no data in range"), while `{=1m,price=bid}` returns data. In those candles `volume == count`
in 99.8 % of rows, `bidVolume`, `askVolume` and `impVolatility` are `NaN`. *Hypothesis:* FX
has no trades, so the default `price=last` candle has no source events; the bid candle's
volume field is populated with the number of quote updates. *Impact:* a client that treats
`volume` uniformly across asset classes will compute meaningless FX volume analytics, and
"OK but empty" for the default symbol is a silent failure for naive integrations.

**Anomaly 5 — daily candle timestamps are 00:00 UTC of the trading date (verified).** The
AAPL `{=d}` candle whose OHLC matches 2026-10-15 trading has `time = 2026-10-15T00:00:00Z`,
which is 2026-10-14 20:00 ET. A client converting candle times to exchange time labels every
daily bar with the previous date. Daily OHLC equals the regular-session OHLC (open 346.95 =
09:30 ET 1m open; close 342.00 = official close vs last 1m close 341.98) while daily volume
includes extended hours (99.5–99.9 % reconciled with intraday sums), exactly as the Javadoc
describes. Expected behaviour, but a documented footgun.

**Edge case 6 — `toTime` is inclusive.** A 60-minute window 14:00→15:00 returns 61 one-minute
candles; chunked downloads therefore produce boundary duplicates that must be de-duplicated
(21 boundary duplicates across all pass-1 chunks, **0 conflicting values**, 0 duplicates remained
after our merge; recomputed in `evidence/recheck/recheck.json`).

**Edge case 7 — unsupported symbols wait for the server-side timeout and return HTTP 200.** A
request including one unsupported symbol (e.g. NVDA, or AUD/USD bid candles) waits for the
server-side timeout and returns `status: TIMED_OUT`, with partial data for the supported symbols
in the same request. The wait is **~3.3 s on an idle service (c = 1) but grows with queueing**:
p50 of `TIMED_OUT` responses in the market-hours run was 3.3 s (c = 1), 4.3 s (c = 5), 6.3 s
(c = 10), 10.3 s (c = 25) and **29.2 s (c = 50)**. AUD/USD bid-candle requests, which are part of
the load mix, **always** timed out (13 of 13 in the market-hours run, 3 of 3 pre-market) while
the AUD/USD quote worked, so a few percent of the load traffic is slow by construction.

### Distinguishing defects from expected behaviour

Expected and correctly handled: equity holidays and weekends (no candles), FX trading through
US holidays, ES Sunday 18:00 ET reopen, DST change, partial last candle, 15-minute delay, daily
OHLC = regular session. Expected but under-documented: FX `price=bid` requirement, FX volume
semantics, daily timestamp at UTC midnight, inclusive `toTime`, the TIMED_OUT wait for unknown
symbols (3.3 s idle, up to 29 s under load), the 00:00–04:00 ET overnight tail and absence of
20:00–24:00 ET hours. Candidates for real defects or at least undocumented limits: the silent
~8000 cap and 1m retention (Anomaly 1), the 1h-vs-5m volume inconsistency — overwhelmingly ETH,
with a rare RTH exception (Anomaly 2), and the FX out-of-session prints (Anomaly 3: 50 one-minute
candles, not 214).

### Impact assessment

For a charting client the visible issues are Anomaly 3 (out-of-session FX bars, 50 of 8000) and
Anomaly 5 (date labels). For a quantitative or backtesting client Anomaly 1 (silently missing history)
and Anomaly 2 (timeframe-dependent volume) are the dangerous ones because they fail silently
and bias results. For a compliance or billing use case, Anomaly 2 means two reports of "total
after-hours volume" for the same instrument can legitimately disagree depending on the
timeframe used; RTH volume reconciliations are usually exact but not always (1 AAPL exception).
Price integrity is **good but not perfect**: OHLC agrees across timeframes in all but a handful of
candles. In the 1h-from-5m check six candles differ in at least one price field (AAPL 1, TSLA 3,
ES 1, EUR/USD 1; three of them on the forming 11:00Z bucket), including three **complete**
buckets (AAPL 2026-10-02 21:00Z close; TSLA 2026-10-08 15:00Z close and 16:00Z open). The
differences are ≤ 0.023 % but they are real and sit in extended hours (AAPL) and in the
same regular-hours block as the volume exception (TSLA). 5m-vs-1m OHLC differences occur only on
incomplete buckets.

Plots: `evidence/plots/pass1/per_day_1m_counts.png` (weekend handling, all instruments),
`evidence/plots/pass1/agg_AAPL_1h_from_5m.png` (Anomaly 2), `evidence/plots/pass1/weekend_EURUSD_1m.png`
(Anomaly 3), `evidence/radar/*.png` (Radar comparison).

---

## Part 2 — Real-time behaviour under load

### Methodology

`scripts/load_test.py` (aiohttp, one session, N workers each holding at most one request in
flight, 0.25 s think time) ramps concurrency in steps of 1, 5, 10, 25, 50 for 30 s each with
10 s pauses. Each worker rotates through three request types: a `Quote` snapshot (13 symbols
across stocks, FX and futures), a `Candle` 1m "last 60 min" request (freshness probe) and a
**fixed historical window** (`AAPL{=1m}`/`TSLA{=1m}` 2026-10-15 14:00→15:00Z) whose body
must be byte-identical every time (consistency probe). Hard stops: first HTTP 429, three
consecutive 5xx/network errors, step error rate > 20 %, step p50 > 8 s, or a 3500-request
budget. Every request is logged with UTC time, parameters, HTTP status, dxFeed `status`,
latency, size, SHA-1 of the body and the response headers (`evidence/load/<run>/requests.jsonl`);
`scripts/analyze_load.py` produces `analysis.md|json` and the plots in `evidence/plots/load/`.

**Time windows.** Two labelled runs on Friday 2026-10-16, same script/limits:

| run | window (UTC) | session | steps reached | requests | stop reason |
|---|---|---|---|---|---|
| `smoke_premarket` | 11:42:07–11:42:30 | pre-market | c = 1, 2 | 24 | completed |
| `premarket_fri` | 11:52:56–11:55:24 | pre-market | c = 1, 5, 10, 25 (50 not reached) | 144 | auto-stop: p50 8.3 s at c = 25 |
| `premarket_fri_c1_nothink` | 12:04:23–12:04:54 | pre-market | c = 1, zero think time | 35 | completed |
| `market_hours_fri` | 13:47:21–13:51:06 | **US RTH** | c = 1, 5, 10, 25, 50 | 504 | auto-stop: p50 8.3 s at c = 50 |

### Findings

**Client connection pool and Little's law (verified, offline).** `load_test.py` builds
`aiohttp.TCPConnector(limit=max(steps)+2)` → **52** connections for the default step list, with
aiohttp's default `limit_per_host=0` (**unlimited**). Each of N workers holds at most one
in-flight request. Reconciling the pre-market request log with Little's law
(`L = throughput × mean latency`; also sweep-line measured L) — see
`evidence/load/premarket_fri/littles_law.md`:

| c | thr (req/s) | mean lat (s) | L = thr×lat | L measured | vs configured c |
|---|---|---|---|---|---|
| 1 | 0.195 | 4.922 | 0.96 | 0.96 | ≈1 (think-time slack) |
| 5 | 1.628 | 2.693 | 4.38 | 4.38 | ≈5 |
| 10 | 1.559 | 5.766 | 8.99 | 8.99 | ≈10 |
| 25 | 1.682 | 8.184 | 13.76 | 13.76 | ≪25 (early stop) |

At c=5 and c=10, **effective in-flight matched configured concurrency** while throughput
stayed ~1.6 req/s. **Caveat (corrected):** the connector limit (52) is above the highest
concurrency we ever configured (50), so the client pool could **never** have been the binding
constraint, with or without Little's law; the Little's-law table shows that our workers were
actually all in flight, i.e. the wait was not on the client side of the socket. What remains
**unresolved** is *where* the cap sits: a **per-IP/per-client throttle** on the demo versus
**shared server capacity** used by other demo users. Telling these apart needs a second client
or a second IP running concurrently; that was **not run**. Throughput flat in c while L ≈ c is
consistent with both.
Market-hours Little's law (`evidence/load/market_hours_fri/littles_law.md`): L≈c at c=1/5/10,
L = 20.6 at c=25 and 36.1 at c=50 (partial duty cycles), with throughput **flat to slightly
declining** (3.18, 3.19, 3.02, 2.78 req/s for c=5/10/25/50).

**Latency versus concurrency — pre-market (verified).** From
`evidence/load/premarket_fri/analysis.md`:

| concurrency | n | throughput (req/s) | p50 (s) | p95 (s) | p99 (s) | max (s) | HTTP errors |
|---|---|---|---|---|---|---|---|
| 1 | 6 | 0.2 | 0.76 | 20.0 | 25.0 | 26.3 | 0 |
| 5 | 55 | 1.63 | 2.68 | 3.14 | 5.75 | 5.75 | 0 |
| 10 | 55 | 1.56 | 6.20 | 6.71 | 7.95 | 9.33 | 0 |
| 25 | 28 | 1.68 | 8.27 | 14.9 | 15.0 | 15.0 | 0 |

**Throughput is requests / (last completion − first start)**, i.e. through request completion,
as in `steps.jsonl` and `littles_law.md` (analysis files regenerated with the patched
`analyze_load.py`). An earlier version divided by first-to-last request *start* and so dropped
the in-flight tail, which inflated the figures (1.84 / 1.86 and a nonsensical 17 req/s at c=25).
A sequential worker with no think time achieves **1.13 req/s** at p50 0.77 s
(`premarket_fri_c1_nothink`). With think time, throughput plateaus near **~1.55–1.68 req/s**
at c=5/10/25. p50 is **roughly linear up to c=10** (0.76 → 2.68 → 6.20 s) and flattens at
c=25 (→ 8.27 s), but the c=25 step stopped after 28 requests, so it is a censored measurement.
p95 is not linear (cold-start outlier at c=1: 26.3 s, a single request). The first-request
cold-start value of 26 s also pulls the c=1 p99/max.
*Alternative explanations considered:* Documented demo limits do not state a per-client QPS;
request parameters (think time) affect measured rps but not the L≈c observation; the client
pool is ruled out above; pre-market timing does **not** make this a lower bound on latency —
see market-hours comparison (RTH was faster).

**Latency versus concurrency — market hours (verified).** From
`evidence/load/market_hours_fri/analysis.md` (13:47–13:51Z):

| concurrency | n | throughput (req/s) | p50 (s) | p95 (s) | p99 (s) | max (s) | HTTP errors |
|---|---|---|---|---|---|---|---|
| 1 | 39 | 1.31 | 0.45 | 0.81 | 2.37 | 3.32 | 0 |
| 5 | 99 | 3.18 | 1.14 | 2.30 | 3.96 | 4.55 | 0 |
| 10 | 104 | 3.19 | 2.54 | 4.22 | 6.31 | 6.96 | 0 |
| 25 | 124 | 3.02 | 5.28 | 12.17 | 14.19 | 14.76 | 0 |
| 50 | 138 | 2.78 | 8.28 | 26.55 | 28.24 | 29.17 | 0 |

(`steps.jsonl`, which was written live, reports 3.15 / 3.16 / 3.00 / 2.78 req/s for c=5/10/25/50
with a slightly different end-of-step clock; the analysis figures above use last completion.
The two sets agree to within 0.03 req/s.)

p50 fit R² = 0.98 (linear slope 0.16 s/conn); step ratios 2.52 → 2.23 → 2.08 → 1.57.
**Throughput is flat to slightly declining (≈3.2 → 2.8 req/s) as concurrency rises from 5 to
50: the service saturates at about 3 req/s for this client, and extra parallelism only adds
queueing.** The earlier "3.3–4.6 req/s, rising with c" was a measurement artefact (see above)
and is withdrawn. Market hours remain roughly **2× the pre-market throughput** (≈3.2 vs ≈1.6
req/s at c=5/10) and lower latency at equal concurrency. 0 HTTP errors; no 429; fixed-window
bodies still byte-identical (AAPL 66/66, TSLA 62/62). Quote age p50 **900.4 s** (unchanged vs
pre-market). TIMED_OUT only for AUD/USD bid candles (13×).

*Censoring.* The auto-stop and the percentiles use **completed** requests only. At high
concurrency the slowest requests are still in flight when a step ends, so p50/p95 are
**understated** and the stop rule triggers later than the true median would suggest. The
latency clusters near 12 s (c=25) and 26.5 s (c=50) look like **waves or head-of-line
blocking**, not smooth degradation.

**Pre-market vs market-hours comparison (verified).**

| metric | pre-market (`premarket_fri`) | market hours (`market_hours_fri`) |
|---|---|---|
| Window (UTC) | 11:52–11:55Z | 13:47–13:51Z |
| Requests / stop | 144 / p50>8s at c=25 | 504 / p50>8s at c=50 |
| Throughput at c=5 / c=10 (req/s, through completion) | 1.63 / 1.56 | 3.18 / 3.19 (3.02 at c=25, 2.78 at c=50) |
| p50 at c=1 / 5 / 10 / 25 (s) | 0.76 / 2.68 / 6.20 / 8.27 | 0.45 / 1.14 / 2.54 / 5.28 |
| p95 at c=1 / 5 / 10 / 25 (s) | 20.0 / 3.14 / 6.71 / 14.9 | 0.81 / 2.30 / 4.22 / 12.17 |
| p99 at c=5 / 10 / 25 (s) | 5.75 / 7.95 / 15.0 | 3.96 / 6.31 / 14.19 |
| HTTP error rate | 0 % | 0 % |
| Quote age p50 / max (s) | 901.7 / 956.5 | 900.4 / 933.1 |
| Max concurrency reached | 25 | 50 |

Market hours were **faster and roughly twice the throughput** on this shared demo than the pre-market
run — the earlier “pre-market = lower bound on queueing” framing is **not** supported by
these two samples. Shared-demo load varies; both runs still show queueing (p50 rises with c)
and no client back-pressure signal.

**What failed first, what degraded first (verified).** Nothing failed: 0 HTTP errors, no 429
or 5xx across pre-market and market-hours runs (648 load requests). Latency degraded first.
Pre-market at c=10: quote/fresh/fixed p50 ~5.8–6.5 s (similar across kinds). Market hours at
c=10: quote 1.96 s, fresh 3.19 s, fixed 2.50 s. **At higher concurrency the kinds separate**
(market hours, c=25): quote p50 **2.6 s** versus candle requests **11.2 s (fixed) and 11.9 s
(fresh)**; at c=50 fresh-candle p50 is 26.4 s versus quote 7.1 s. So queueing is **not uniform
across request types**: candle requests wait far longer than quotes once the service is
saturated, which fits per-request-type cost or separate queues rather than one FIFO queue.
No hard failures, no rate-limit headers, no `Retry-After`. A naive client can keep adding
parallelism and worsen its own latency.

**Response consistency and caching (verified).** The fixed-window probe returned one
distinct body per symbol across all repeats (AAPL 16/16 identical, 20 013 bytes, 61 candles;
TSLA 17/17 identical, 20 085 bytes): no inconsistency between identical queries. No
`Cache-Control`, `ETag`, `Age` or `X-Cache` headers; the repeated fixed-window query was not
faster than its first execution (1.1 s first, p50 2.7 s under c = 5), so there is no evidence
of an HTTP cache in front of the service — every request hits the backend.

**Stale data under load (verified).** Quote age stayed at 901–957 s and fresh-candle age at
923–2385 s at every concurrency step: load changes latency, not freshness. The delay is
upstream of the web service. The `empty = 2` fresh-candle responses were AUD/USD bid candles,
which the demo does not serve although it serves AUD/USD quotes — a symbol-specific
behaviour (3 `TIMED_OUT` for AUD/USD, 0 for every other symbol).

**Outliers (verified, cause hypothesised).** The very first request of the `premarket_fri`
run (Quote AAPL at 11:52:56Z) took 26.3 s; the same request type took 0.16–1.2 s for the rest
of the step. Hypothesis: cold start of a server-side subscription or connection after an idle
period; it did not recur in the two later runs, so it stays a single observation.

**Streaming versus REST (verified pre-market 12:08–12:11Z and market hours 13:51–13:54Z).**
Same method both times (`sse_compare.py`, Quote + 1m Candle, 180 s, REST poll 5 s).

| | pre-market `20261016T120829Z` | market hours `20261016T135132Z` |
|---|---|---|
| SSE events / REST polls | 646 / 36 | 1308 / 36 |
| REST−SSE lag median / max (s) — **lower bound** | 0.72 / 4.82 | 0.26 / 1.59 |
| Quote age | ~900–931 s (same 15-min delay) | same (~900 s; load-run quote p50 900.4 s) |

The REST side was polled every 5 s, so the lag figures are bounded by that polling interval
and should be read as a **lower bound** on SSE-vs-REST difference, not a precise latency.

Forming-candle updates and the NaN/2038 control-message footgun (subscribe `fromTime` inside
the delay window) were first seen pre-market and remain relevant. Evidence under
`evidence/sse/`.

**Radar versus REST (verified pre-market and market hours).** Pre-market 12:05Z: Radar
"Last Candle 1m" OHLCV matched the REST 11:50Z bar for AAPL/MSFT. Market hours ~13:57Z: Radar
Last Candle 1m **open/high/low matched** the REST 13:41Z bar exactly for AAPL, MSFT, TSLA
(GOOG/AMZN within rounding); Radar "Price" can differ slightly from REST close while the bar
is still updating under the shared ~15-min delay. NVDA still appears on Radar and
`TIMED_OUT` on REST. Evidence: `evidence/radar/compare_1m_*.json`,
`compare_1m_market_hours_20261016T1357Z.json`.

**Limits of this test.** One client, one IP, one geography (Tbilisi), a shared free demo,
648 load requests across pre-market + market hours, auto-stopped on p50>8 s (completed requests
only, so censored at high concurrency). The aiohttp pool limit (52) exceeds the maximum
concurrency (50) and so could not have bound; per-IP throttling versus shared capacity is
unresolved because a second independent client was not run. **Burst traffic** (a one-shot
50-parallel burst) and **batching** (13 symbols in one request vs 13 requests) were **not
tested**; the brief's burst scenario is only approximated by the ramp, and any "batch symbols"
recommendation below is untested advice.
TimeAndSale history is not available on demo REST. The numbers describe what this client
sees; they say nothing about dxFeed production capacity.

### Monitoring, SLOs and escalation triggers

Metrics to collect (per endpoint and per symbol class, 1-minute resolution):
request latency p50/p95/p99 by request type; throughput and in-flight count; HTTP and
dxFeed-`status` error rates (`TIMED_OUT`, `NOT_SUBSCRIBED`, empty-OK); **data freshness lag**
= wall clock − newest event time, compared with the expected ~900 s delay and the session
calendar; **candle completeness** = candles received per expected interval during the
session; **cross-source divergence** = SSE-vs-REST state lag and Radar-vs-REST last-candle
equality; **cross-timeframe reconciliation** = 1h vs Σ1m price (must be exact) and volume
(threshold); saturation proxies = latency slope against our own concurrency, and `TIMED_OUT`
duration stretch (3.3 s baseline at c = 1; 29 s at c = 50 in our run).

Suggested SLOs for the demo service (numbers from this report; production would be tighter):

| SLI | SLO |
|---|---|
| Availability (HTTP 200 and parsable JSON) | 99.5 % of requests per month |
| Latency, single request, `Quote` or ≤ 1 day of candles | p95 ≤ 2 s over 5 min |
| Freshness, liquid US stock during RTH, FX during its session | newest event age ≤ 900 s + 120 s for 99 % of minutes |
| Candle completeness, AAPL 1m during RTH | ≥ 99.5 % of expected minutes present within 20 min of their close |
| Cross-timeframe price consistency (1h vs Σ1m OHLC, complete buckets) | ≥ 99.9 % within 0.03 %; investigate any larger gap (sample: 3 complete-bucket differences ≤ 0.023 %) |
| Cross-timeframe volume consistency during RTH | investigate any mismatch (sample had AAPL 1 / TSLA 2); ETH documented tolerance |
| Streaming/REST agreement | REST reflects SSE state within 5 s for 99 % of samples |

Escalation triggers (duration-qualified, to avoid paging on single blips):
p95 latency > 5 s for 5 min at client concurrency ≤ 2 → page L2; freshness lag > 1 200 s for
a liquid symbol during its session for 3 consecutive minutes while another class is fresh →
page L2 and open a feed incident; freshness lag growing for all classes simultaneously →
upstream feed incident, escalate to feed on-call immediately; candle completeness < 98 % for
an hour → ticket to aggregation team; any 1h-vs-1m price gap above 0.03 % on a complete bucket → immediate escalation
(data integrity); error rate > 1 % for 5 min or any 5xx burst → platform on-call.

---

## Part 3 — Operational risk review

Ranking combines likelihood (how often we actually saw it) and client impact (silent and
decision-affecting ranks above loud and cosmetic). Each row is grounded in a Part 1 or Part 2
observation.

| # | risk | category | observed evidence | likelihood | client impact | detection | mitigation | escalate when |
|---|---|---|---|---|---|---|---|---|
| 1 | Silent truncation / limited retention of 1m history (about 8000 candles, status OK) | silent failure, data integrity | Anomaly 1; pass-1 chunks | high (every long request) | high: backtests and charts lose history without any error | client-side: expected-vs-received count per request, alert if `n >= 8000` or first candle later than `fromTime`; server-side: count of capped responses | document the cap; chunk requests; return a truncation flag or 206-style status | any capped response for a paying client; retention shrinking run-to-run |
| 2 | Cross-timeframe volume inconsistency (1h vs 1m/5m) in extended hours | data integrity | Anomaly 2: 63 % of AAPL 1h candles, up to −99 % | high (daily, every ETH hour) | medium–high: volume analytics and reconciliations disagree by timeframe; silent | nightly job rebuilding 1h from 1m per symbol and alerting on volume deviation > 1 % during ETH, > 0 % during RTH | publish aggregation rules per period; or make 1h a strict roll-up of 1m | deviation appears in regular hours, or price fields start to differ |
| 3 | Saturating, queueing request handling: p50 roughly linear to c=10; throughput flat at ~1.6 req/s pre-market and ~3.2 req/s (falling to 2.8 at c=50) in market hours; candle requests queue longer than quotes | latency | Part 2: p50 0.8→6.2→8.3 s pre-market; 3.18/3.19/3.02/2.78 rps at c=5/10/25/50 in market hours; 0 errors | high under any parallel client | medium: dashboards time out, polling loops back up; no error to react to | p50/p95 per endpoint and request type, in-flight request count, time-in-queue; alert when p95 > 5 s for 2 min | client: cap concurrency ≤ 5, back off on latency, consider batching symbols per request (**untested** here); server: return 429/503 with Retry-After instead of queueing indefinitely | p95 > 10 s for 5 min or queueing visible for single-request clients |
| 4 | Staleness not distinguishable from "closed": 15-min delay, no freshness metadata, forming candle unflagged | staleness, silent failure | 900 s quote age on all instruments; `eventFlags = 0`; `last_candle_open_at_fetch = True` | high (always) | high for anything near-real-time; a stuck feed looks like a quiet market | data-age gauge per symbol vs session calendar (Task A) — alert if age > 900 s + 2 × period while session open; cross-check against SSE | expose `eventTime`/server time and a "delayed" marker; document the 15 min delay next to the endpoint | age > 20 min for a liquid symbol during RTH, or age diverging between symbols of the same class |
| 5 | Symbol-universe and asset-class quirks: unknown symbols wait 3.3 s idle (up to 29 s under load) and return HTTP 200; FX needs `price=bid`; Radar ≠ REST universe | silent failure, latency | Edge cases 4, 7; Radar comparison; AUD/USD bid candles TIMED_OUT | medium | medium: integrations misinterpret "OK, empty" as "no trades" | monitor `TIMED_OUT`/empty ratio per symbol; symbol-list diff between tools | publish the demo symbol list and per-class candle defaults; return a distinct status for unknown symbols | a previously served symbol starts timing out |
| 6 | Out-of-session artefacts (FX prints after the Friday 17:00 ET close and before the Sunday 17:00 ET reopen: 50 of 8000 one-minute candles; daily bar dated at UTC midnight) | data integrity | Anomaly 3 (corrected from "214 weekend"), 5 | medium (every weekend) | low–medium: spurious bars, mislabelled dates, false "market open" signals | **outside-session** candle counter per symbol against the session calendar (not UTC-weekday, which flags the legitimate Sunday reopen); compare session calendar vs first/last candle time | filter indicative quotes; document alignment | out-of-session candles appear on equities or futures, or FX out-of-session prints move price |
| 7 | Monitoring blind spot: `status: OK` on partial/odd results; no rate-limit headers; health of "the feed" invisible to clients | monitoring | Part 2 header inventory; TIMED_OUT with partial payloads | high | medium: no early warning, support learns from clients | synthetic probes per asset class (quote age, candle count per hour, 1h/1m reconciliation) with SLOs below | add `Retry-After`/rate-limit headers, a `/status` resource with feed delay and last-update times | synthetic probe failing for 2 consecutive runs |

---

## Part 4 — Incident simulation

**This is a simulation.** It is constructed from the behaviour observed in Part 1 (Anomaly 2:
hourly candles for US stocks carry more volume than the 1m/5m candles for the same hour in
extended trading) and Part 2 (serialised request handling). Timestamps are invented for the
scenario; the measurements quoted are real and reproducible from `evidence/`.

### 4.1 Incident analysis

*Title:* INC-SIM-01 — Hourly candle volume diverges from minute candles for US equities
(mostly outside regular hours).

*Timeline (UTC, scenario).* Thu 20:30 a quant client's nightly reconciliation flags AAPL
hourly volume 845 299 vs 13 744 from their 1m roll-up for the 18:00 ET hour and opens a P1
ticket at 21:05 ("volume data corrupted"). 21:15 L2 reproduces with the demo REST: for
2026-10-02 the 18:00 ET candle differs by −98.4 %; **130 of 131** AAPL mismatches are outside
09:30–16:00 ET (served 1h > Σ5m); **1 RTH exception** at 2026-10-08 11:00 ET where Σ5m/1m
exceeds served 1h by ~2 % (OHLC identical; opposite sign). 5m matches 1m on complete buckets;
FX and futures hourly volumes match. 21:40 L2 confirms the ETH pattern holds for TSLA
(118 ETH + 2 RTH mismatches) and that, on the one day with a daily candle (2026-10-14), the
**hourly** sum (−0.13 %) is closer to the daily total than the 1m sum (−0.15 %), so no volume
looks lost and the two series attribute it differently. 22:00 escalation to the aggregation
(dxPrice/candle) team with the evidence and the question of which series is the reference.
22:30 first client update. Fri 09:00 (scenario) engineering is still confirming the rule; the
RTH exception, which falls on the same day as a TSLA exception, remains under investigation.

*Detection.* By the client, not by monitoring: there is no cross-timeframe reconciliation
probe on the service.

*Impact.* Consumers of hourly candles for US equities — overwhelmingly outside 09:30–16:00 ET;
price fields essentially unaffected (OHLC agrees except a few ≤ 0.023 % differences); volume-based
indicators (VWAP, relative volume) and any reconciliation between timeframes affected. Regular-hours volume usually
matches but is not guaranteed (1 AAPL + 2 TSLA exceptions in the sample).

*Root-cause hypothesis.* Different aggregation records per period (`Trade.1m`, `Trade.5m`,
`Trade.1h`) with different inclusion rules for extended-hours sale conditions; alternative:
late prints / corrections applied differently per period. The ETH pattern (130/130 served >
rebuilt) favours inclusion-rule differences; the RTH exception’s **opposite** sign means
“late prints only into the open hourly bucket” is a weak fit for that hour
(**hypothesis** — see Anomaly 2).

*Mitigation.* Short term: **do not tell clients which series to trust yet.** The hourly series is
closer to the daily total on the one day we can check, so rebuilding hourly bars from 1m would
give the *lower* number; we are confirming which series is the reference. Until then advise
clients to reconcile ETH volume against the hourly and daily totals and to treat ETH volume as
timeframe-dependent; publish a known-issue note. The `tho=true` attribute (regular-hours-only
candles) is a candidate for regular-hours analysis but was **never tested** here, so it is not
offered as a confirmed workaround. Medium term: align the inclusion rules or document them per
period; add the reconciliation probe (4.4).

### 4.2 Client communication (external)

Subject: Hourly candle volume for US stocks in extended hours — what we found and what we are
doing

Hello,

Thank you for the detailed report. We reproduced the difference you observed between hourly
candle volume and your own roll-up of 1-minute candles for AAPL on 2 October between 18:00 and
19:00 New York time.

What we know: the difference mainly affects the volume field of hourly candles for US stocks
during extended trading hours (before 09:30 and after 16:00 New York time) — 130 of 131 AAPL
mismatches in our sample. Open, high, low and close agree across timeframes apart from a few
very small differences (≤ 0.03 %), and 1-minute and 5-minute candles agree on complete
buckets. Regular-hours hours usually agree; we also see one AAPL regular-hours exception
(~2 % volume, opposite sign) that we are investigating. On the one day where we could compare,
the daily total is within 0.2 % of both the hourly and the 1-minute sums, with the hourly sum
slightly closer.

Who is affected: clients using hourly candles for US stocks to compute volume-based
measures outside regular hours.

What we are doing: our data engineering team is confirming the aggregation rule that causes
the difference and which series is the reference. Until we have confirmed it, please do not
switch your extended-hours volume source on our account; if you need a number today, reconcile
it against the hourly and daily totals and tell us which one you are using.

Next update: by 10:00 UTC tomorrow, or sooner if the cause is confirmed.

Kind regards, dxFeed Support (L2)

### 4.3 Internal escalation note

To: candle/aggregation on-call; cc: support lead. Severity proposed: S3 (data-quality,
no outage, one client affected so far, likely systemic).

Summary: hourly candles for US equities usually report higher volume than Σ5m/1m in extended
hours. Reproduced on demo REST for AAPL and TSLA
(`evidence/validation/pass1/agg_AAPL_1h_from_5m.csv`): 131/208 AAPL hours differ — **130 ETH**
(served > rebuilt) and **1 RTH** at 2026-10-08 11:00 ET (rebuilt > served by ~2 %, OHLC
identical); median −4 % … −28 % per ETH hour, max −99.1 % (2026-10-07 17:00 ET: 743 918 vs
6 422; also 2026-10-02 18:00 ET: 845 299 vs 13 744, count 415 vs 271). 5m == 1m on complete
buckets. FX and ES hourly volumes match. 2026-10-14: daily 50 061 053, Σ1h 49 994 234, Σ1m
49 983 889. AAPL and TSLA RTH exceptions fall on 2026-10-08 in overlapping hours (SPY/MSFT
not checked).

Hypotheses: (1) per-period aggregators apply different ETH sale-condition filters;
(2) late prints / corrections land differently per period. (1) favoured for ETH; RTH
exception has opposite sign so (2) alone is incomplete (**hypothesis** — Anomaly 2).

Ask: confirm which prints the 1h aggregator includes that 1m excludes, whether this is
intended, and whether 1m/5m or 1h is the reference for ETH volume (our data suggests 1m/5m is
the incomplete one; we are not asserting it). Need an answer for the
client update at 10:00 UTC.

### 4.4 Post-mortem outline

1. Summary — one paragraph, severity, duration from first client report to published
   explanation.
2. Impact — affected symbol class, periods, fields, number of clients (from API logs: who
   requested 1h candles for US equities), no price impact.
3. Timeline — detection (client), reproduction, escalation, communication, fix/decision.
4. Root cause — the confirmed aggregation rule, why it differed per period, why it was not
   documented.
5. What went well — reproducible in 10 minutes from public endpoints; daily reconciliation
   ruled out data loss; clear client message without speculation.
6. What went badly — detected by the client; no cross-timeframe probe; documentation did not
   state per-period inclusion rules; the `status: OK` response gives no hint.
7. Action items (owner, due) — (a) nightly 1h-vs-1m reconciliation probe per asset class with
   alert thresholds (monitoring team); (b) document aggregation rules per period and session
   in the Candle page (docs team); (c) decide and implement a single inclusion rule or expose a
   per-period attribute (aggregation team); (d) add a known-issues section to the demo page
   (support).
8. Lessons — "same symbol, different timeframe" is a reconciliation surface clients use;
   silent divergence costs more trust than a visible error.

---

## Part 5 — Product improvement proposals

**Technical — explicit truncation and freshness metadata in REST responses.**
*Problem (evidence):* responses are capped at about 8000 candles with `status: OK` and no indicator
(Anomaly 1); forming candles are returned with `eventFlags = 0`; the 15-minute delay is not
stated in the payload; unknown symbols return HTTP 200 `TIMED_OUT` after 3.3 s idle (up to
29 s under load). *Proposal:*
add a response envelope with `truncated: true/false`, `limit`, `serverTime`, `delaySeconds`
and per-symbol `lastEventTime`; set `eventFlags` for the forming candle; return
`status: UNKNOWN_SYMBOL` immediately for symbols not in the demo universe. *Complexity:* M —
additive JSON fields are backward compatible, but the cap and the unknown-symbol path live in
the web service while delay/last-update come from the feed layer; needs coordination and a
schema (`xsd/dxfeed-service.xsd`) update. *Trade-off:* slightly larger payloads; XML schema
versioning. *Business impact:* removes the two silent-failure modes most likely to produce
"your data is wrong" tickets and makes freshness SLOs measurable from the client side.

**Monitoring — synthetic data-quality probes with SLOs per asset class.**
*Problem (evidence):* nothing on the service side would have caught Anomaly 2, 3 or the
serialised latency growth; all were found by a single client script. *Proposal:* a probe
fleet (one small instrument per class — US stock, FX, futures) that every minute measures
quote/candle age vs the session calendar, candle completeness per hour, 1h-vs-1m
reconciliation (price exact, volume within 1 %), p50/p95 latency at concurrency 1 and 5, and
TIMED_OUT ratio; with the SLOs from Part 2 and alerts routed to L2. *Complexity:* S–M — the
scripts in this report already implement most measurements; wiring to Prometheus/Grafana
and a session calendar (Task A) is the remaining work. *Trade-off:* adds ~2 req/s of synthetic
load, which on this service is not negligible (it is the whole capacity of one client);
probes must run at low concurrency. *Business impact:* turns client-reported incidents into
internally detected ones and gives L2 numbers to put in escalations.

**Documentation — a "demo service facts" page next to the REST help.**
*Problem (evidence):* finding the candle syntax, the FX `price=bid` requirement, the 15-min
delay, the symbol universe, the 8000 cap, the inclusive `toTime`, the UTC-midnight daily
timestamp and the extended-hours default each required experiments; `tools.dxfeed.com/radar`
redirects to the marketing site and several KB URLs 404. *Proposal:* one page listing the
endpoints, the exact symbol list served, per-asset-class candle defaults and attributes,
delay, retention/caps, session and alignment semantics with worked examples, and the known
differences between Radar and REST. *Complexity:* S — content is known (this report is a
draft of it); maintenance needs an owner. *Trade-off:* documenting limits of a free demo may
invite questions, but it prevents misuse and support load. *Business impact:* fewer
first-contact tickets, faster evaluations by prospects, and a reference L2 can link to.

---

## Open items and how to complete them

- **Market-hours load / SSE / Radar — DONE 2026-10-16 13:47–13:58Z** (`market_hours_fri`,
  SSE `20261016T135132Z`, Radar `compare_1m_market_hours_20261016T1357Z.json`). Comparison
  table is in Part 2 above.
- **1h candle stability re-fetch — DONE** (AAPL + TSLA 2026-10-08 15:00Z stable across pass1 /
  13:46Z / 13:57Z). TimeAndSale sale-condition test — **blocked** on demo REST (TIMED_OUT /
  empty); see `evidence/refetch/`.
- **Weekend logger — stopped.** Restarted 2026-10-17T13:01Z after a first gap
  (~2026-10-16T14:49Z → 2026-10-17T12:57Z); the restarted process stopped again after its last
  poll at **2026-10-17T14:28Z** (868 poll lines in `evidence/weekend_logger/poll_log.jsonl`).
  Sunday reopen and Monday are therefore **not** covered by the logger; restart it with
  `python scripts/weekend_logger.py --interval 60 --until <Monday 15:30Z>` if needed.
- **Pass 2 and weekend analysis — WAITING until Monday 2026-10-19 after 15:30Z:**
  `python scripts/fetch_candles.py --pass pass2 && python scripts/validate_candles.py --pass pass2 && python scripts/analyze_logger.py`.
  Then compare `evidence/validation/pass1/report.json` with `pass2` for the Oct 16 candles
  (were pass-1 "forming" candles finalised with the same values? did any closed candle change?),
  check that Monday's first AAPL/TSLA candles sit on the 00:00 ET / 09:30 ET boundaries, and
  read the EUR/USD weekend behaviour from `evidence/weekend_logger/analysis.md`.
- **Anomaly 2 remaining:** re-fetch AAPL 5m for an ETH mismatch hour in pass 2 and diff against
  pass 1; TimeAndSale needs a non-demo endpoint or different event type if one exists.
- **Not done, needs live API calls (documented, not run):** SPY and MSFT 1h/5m for 2026-10-08
  11:00–12:00 ET (is the AAPL/TSLA RTH exception market-wide?); `tho=true` re-request; a one-shot
  50-parallel **burst**; a **batching** comparison (13 symbols in one request vs 13 requests); a
  second client or IP for the per-IP-throttle-versus-shared-capacity question; more daily
  candles to test "hourly vs daily" on more than one day.
- **Offline extras added:** `scripts/offline_recheck.py` (writes `evidence/recheck/recheck.json`)
  recomputes the totals, FX/ES session split, OHLC mismatches, ET hours, daily/1h/1m volume
  reconciliation, realised 1m volatility and load throughput through completion. Realised 1m
  volatility (contiguous returns, including extended hours): AAPL 5.1 bp per minute (~16 %
  annualised), TSLA 5.9 bp (~19 %), i.e. TSLA is ~16 % more volatile per minute than AAPL,
  which supports but only mildly justifies TSLA as the "high-volatility" pick (the demo
  offers no crypto).
- **Task A still blocked without operator input:** CME `input/cme/` empty; Drive credentials
  unset (DRY_RUN); OPRA 2026 PDF still 403 on CDN (probed 2026-10-17).

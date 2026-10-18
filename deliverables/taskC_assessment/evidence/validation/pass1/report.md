# Candle validation — pass1 (data as of 2026-10-16 11:34:12+00:00)

## Series checks

Headline anomaly count = **outside session** (session model: equities 09:30-16:00 ET; FX Sun 17:00 ET - Fri 17:00 ET; ES Sun 18:00 ET - Fri 17:00 ET minus 17:00-18:00 break). The `weekend (UTC, legacy)` column tags UTC Saturday/Sunday and counts the legitimate Sunday reopen; it is informational only.

| series | n | first | last | dup | misaligned | missing in session | **outside session** | weekend (UTC, legacy) | zero-vol | frozen runs (longest) | last open at fetch | resp. not ascending |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AAPL 1m | 8000 | 2026-10-05T18:37 | 2026-10-16T11:19 | 0 | 0 | 0/3203 (0.0%) | 4797 (59.96%) | 0 | 0 | 75 (4) | False (912.0s) | 0/10 |
| AAPL 5m | 2380 | 2026-10-02T04:00 | 2026-10-16T11:15 | 0 | 0 | 0/780 (0.0%) | 1600 (67.23%) | 0 | 0 | 6 (2) | False (1152.0s) | 0/4 |
| AAPL 1h | 3943 | 2026-01-05T05:00 | 2026-10-16T11:00 | 0 | 0 | 42/1224 (3.43%) | 2761 (70.02%) | 9 | 0 | 1 (2) | True (2052.0s) | 0/5 |
| EURUSD 1m | 8000 | 2026-10-08T22:41 | 2026-10-16T11:20 | 0 | 0 | 10/7960 (0.13%) | 50 (0.62%) | 214 | 0 | 14 (2) | False (852.0s) | 0/9 |
| EURUSD 5m | 3056 | 2026-10-02T00:00 | 2026-10-16T11:20 | 0 | 0 | 0/3017 (0.0%) | 39 (1.28%) | 108 | 0 | 2 (2) | False (852.0s) | 0/4 |
| EURUSD 1h | 5148 | 2026-01-04T18:00 | 2026-10-16T11:00 | 0 | 0 | 1/4911 (0.02%) | 238 (4.62%) | 312 | 0 | 4 (2) | True (2052.0s) | 0/5 |
| TSLA 1m | 8001 | 2026-10-06T19:16 | 2026-10-16T11:21 | 0 | 0 | 0/2774 (0.0%) | 5227 (65.33%) | 0 | 0 | 43 (3) | False (792.0s) | 0/9 |
| TSLA 5m | 2479 | 2026-10-02T04:00 | 2026-10-16T11:20 | 0 | 0 | 0/780 (0.0%) | 1699 (68.54%) | 0 | 0 | 2 (2) | False (852.0s) | 0/4 |
| TSLA 1h | 3948 | 2026-01-05T05:00 | 2026-10-16T11:00 | 0 | 0 | 42/1224 (3.43%) | 2766 (70.06%) | 9 | 0 | 1 (2) | True (2052.0s) | 0/5 |
| ES 1m | 8001 | 2026-10-08T16:02 | 2026-10-16T11:22 | 0 | 0 | 0/8001 (0.0%) | 0 (0.0%) | 120 | 0 | 25 (3) | False (732.0s) | 0/8 |
| ES 5m | 2897 | 2026-10-02T00:00 | 2026-10-16T11:20 | 0 | 0 | 0/2897 (0.0%) | 0 (0.0%) | 48 | 0 | 1 (2) | False (852.0s) | 0/4 |
| ES 1h | 2462 | 2026-01-08T05:00 | 2026-10-16T11:00 | 0 | 0 | 2169/4631 (46.84%) | 0 (0.0%) | 48 | 0 | 9 (2) | True (2052.0s) | 0/5 |

## Aggregation consistency

| check | compared | any mismatch | open | high | low | close | volume | served w/o source | rebuilt w/o served |
|---|---|---|---|---|---|---|---|---|---|
| AAPL 5m from 1m | 1987 | 2 (0.1%) | 1 | 0 | 0 | 0 | 2 (max 40.3283%) | 0 | 0 |
| AAPL 1h from 5m | 208 | 131 (62.98%) | 0 | 0 | 0 | 1 | 131 (max 99.1367%) | 0 | 0 |
| EURUSD 5m from 1m | 1617 | 2 (0.12%) | 1 | 1 | 0 | 1 | 2 (max 32.5%) | 0 | 0 |
| EURUSD 1h from 5m | 265 | 1 (0.38%) | 0 | 0 | 0 | 1 | 1 (max 0.8297%) | 0 | 0 |
| TSLA 5m from 1m | 1818 | 2 (0.11%) | 1 | 0 | 0 | 1 | 2 (max 21.6541%) | 0 | 0 |
| TSLA 1h from 5m | 208 | 120 (57.69%) | 1 | 0 | 0 | 2 | 120 (max 21.6232%) | 0 | 0 |
| ES 5m from 1m | 1601 | 2 (0.12%) | 1 | 0 | 0 | 1 | 2 (max 43.2387%) | 0 | 0 |
| ES 1h from 5m | 242 | 1 (0.41%) | 0 | 0 | 0 | 1 | 1 (max 0.3176%) | 0 | 0 |

## Holidays in range (NYSE calendar from Task A, 1h series)

- AAPL 2026-01-19 Martin Luther King, Jr. Day (closed): 0 hourly candles
- AAPL 2026-02-16 Washington's Birthday (closed): 0 hourly candles
- AAPL 2026-04-03 Good Friday (closed): 0 hourly candles
- AAPL 2026-05-25 Memorial Day (closed): 0 hourly candles
- AAPL 2026-06-19 Juneteenth National Independence Day (closed): 0 hourly candles
- AAPL 2026-07-03 Independence Day (observed) (closed): 0 hourly candles
- AAPL 2026-09-07 Labor Day (closed): 0 hourly candles
- EURUSD 2026-01-19 Martin Luther King, Jr. Day (closed): 24 hourly candles, 00:00 ET–23:00 ET
- EURUSD 2026-02-16 Washington's Birthday (closed): 24 hourly candles, 00:00 ET–23:00 ET
- EURUSD 2026-04-03 Good Friday (closed): 19 hourly candles, 00:00 ET–21:00 ET
- EURUSD 2026-05-25 Memorial Day (closed): 24 hourly candles, 00:00 ET–23:00 ET
- EURUSD 2026-06-19 Juneteenth National Independence Day (closed): 18 hourly candles, 00:00 ET–17:00 ET
- EURUSD 2026-07-03 Independence Day (observed) (closed): 18 hourly candles, 00:00 ET–17:00 ET
- EURUSD 2026-09-07 Labor Day (closed): 24 hourly candles, 00:00 ET–23:00 ET
- TSLA 2026-01-19 Martin Luther King, Jr. Day (closed): 0 hourly candles
- TSLA 2026-02-16 Washington's Birthday (closed): 0 hourly candles
- TSLA 2026-04-03 Good Friday (closed): 0 hourly candles
- TSLA 2026-05-25 Memorial Day (closed): 0 hourly candles
- TSLA 2026-06-19 Juneteenth National Independence Day (closed): 0 hourly candles
- TSLA 2026-07-03 Independence Day (observed) (closed): 0 hourly candles
- TSLA 2026-09-07 Labor Day (closed): 0 hourly candles
- ES 2026-01-19 Martin Luther King, Jr. Day (closed): 0 hourly candles
- ES 2026-02-16 Washington's Birthday (closed): 0 hourly candles
- ES 2026-04-03 Good Friday (closed): 0 hourly candles
- ES 2026-05-25 Memorial Day (closed): 7 hourly candles, 00:00 ET–23:00 ET
- ES 2026-06-19 Juneteenth National Independence Day (closed): 13 hourly candles, 00:00 ET–12:00 ET
- ES 2026-07-03 Independence Day (observed) (closed): 12 hourly candles, 00:00 ET–12:00 ET
- ES 2026-09-07 Labor Day (closed): 19 hourly candles, 00:00 ET–23:00 ET

## DST (first 1h candle of the New York day, UTC hour histogram)

- AAPL: {4: 153, 5: 43, 6: 2}; Fri 2026-03-06 → 2026-03-06T05:00:00+00:00, Mon 2026-03-09 → 2026-03-09T04:00:00+00:00
- EURUSD: {1: 1, 4: 162, 5: 61, 6: 3, 7: 5, 8: 3, 9: 4, 11: 4, 12: 7, 13: 1, 15: 5, 18: 9, 19: 14, 21: 1}; Fri 2026-03-06 → 2026-03-06T05:00:00+00:00, Mon 2026-03-09 → 2026-03-09T04:00:00+00:00
- TSLA: {4: 155, 5: 43}; Fri 2026-03-06 → 2026-03-06T05:00:00+00:00, Mon 2026-03-09 → 2026-03-09T04:00:00+00:00
- ES: {1: 2, 2: 1, 3: 1, 4: 93, 5: 11, 6: 5, 7: 5, 8: 5, 9: 4, 10: 1, 11: 4, 12: 5, 13: 9, 14: 5, 15: 6, 16: 2, 17: 1, 18: 1, 19: 1, 20: 2, 22: 24, 23: 3}; Fri 2026-03-06 → 2026-03-06T15:00:00+00:00, Mon 2026-03-09 → None

## Missing runs inside expected sessions (first 25 per series)

- AAPL 1h: 7 runs; 2026-01-19T15:00→20:00 (6); 2026-02-16T15:00→20:00 (6); 2026-04-03T14:00→19:00 (6); 2026-05-25T14:00→19:00 (6); 2026-06-19T14:00→19:00 (6); 2026-07-03T14:00→19:00 (6); 2026-09-07T14:00→19:00 (6)
- EURUSD 1m: 5 runs; 2026-10-11T21:25→21:27 (3); 2026-10-11T21:35→21:35 (1); 2026-10-11T21:44→21:44 (1); 2026-10-11T21:48→21:51 (4); 2026-10-11T21:53→21:53 (1)
- EURUSD 1h: 1 runs; 2026-02-26T00:00→00:00 (1)
- TSLA 1h: 7 runs; 2026-01-19T15:00→20:00 (6); 2026-02-16T15:00→20:00 (6); 2026-04-03T14:00→19:00 (6); 2026-05-25T14:00→19:00 (6); 2026-06-19T14:00→19:00 (6); 2026-07-03T14:00→19:00 (6); 2026-09-07T14:00→19:00 (6)
- ES 1h: 332 runs; 2026-01-08T06:00→21:00 (16); 2026-01-08T23:00→21:00 (23); 2026-01-11T23:00→21:00 (23); 2026-01-12T23:00→21:00 (23); 2026-01-13T23:00→21:00 (23); 2026-01-14T23:00→21:00 (23); 2026-01-15T23:00→21:00 (23); 2026-01-18T23:00→21:00 (23); 2026-01-19T23:00→13:00 (15); 2026-01-20T15:00→21:00 (7); 2026-01-20T23:00→21:00 (23); 2026-01-21T23:00→21:00 (23)

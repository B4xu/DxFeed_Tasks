# Load test analysis — premarket_fri_c1_nothink

Window (UTC): 2026-10-16T12:04:23.284Z → 2026-10-16T12:05:04.354Z; requests: 35; stop reason: None

| step | conc | n | rps | errors | p50 s | p95 s | p99 s | max s | http codes | dx status |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 35 | 1.17 | 0 (0.0%) | 0.773 | 1.733 | 2.227 | 2.257 | {'200': 35} | {'OK': 35} |

Per kind (p50/p95 s, staleness p50/max s):

- c=1: candle_fixed: n=11 p50=0.703 p95=1.705 err=0 age=75881.4/75892.7 bytes=20013–20085 empty=0; candle_fresh: n=12 p50=1.207 p95=1.537 err=0 age=948.5/2969.7 bytes=340–14583 empty=0; quote: n=12 p50=0.409 p95=1.587 err=0 age=901.4/951.3 bytes=250–267 empty=0

Fixed-window consistency: {"AAPL": {"n": 6, "distinct_bodies": 1, "distinct_sizes": [20013], "n_candles": [61]}, "TSLA": {"n": 5, "distinct_bodies": 1, "distinct_sizes": [20085], "n_candles": [61]}}

Rate-limit headers present: False; header keys seen: ['connection', 'date', 'server', 'transfer-encoding', 'x-origin-nginx']

Latency fit: {}

TIMED_OUT by symbol: {}


# Load test analysis — smoke_premarket

Window (UTC): 2026-10-16T11:42:07.020Z → 2026-10-16T11:42:30.113Z; requests: 24; stop reason: None

| step | conc | n | rps | errors | p50 s | p95 s | p99 s | max s | http codes | dx status |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 11 | 1.43 | 0 (0.0%) | 0.501 | 1.571 | 1.682 | 1.71 | {'200': 11} | {'OK': 11} |
| 1 | 2 | 13 | 1.63 | 0 (0.0%) | 1.2 | 1.658 | 1.763 | 1.79 | {'200': 13} | {'OK': 13} |

Per kind (p50/p95 s, staleness p50/max s):

- c=1: candle_fixed: n=3 p50=0.618 p95=0.626 err=0 age=74532.1/74534.1 bytes=20013–20085 empty=0; candle_fresh: n=4 p50=0.581 p95=1.556 err=0 age=914.8/1631.2 bytes=919–14545 empty=0; quote: n=4 p50=0.187 p95=1.25 err=0 age=902.0/909.5 bytes=252–257 empty=0
- c=2: candle_fixed: n=4 p50=1.415 p95=1.753 err=0 age=74544.6/74547.5 bytes=20013–20085 empty=0; candle_fresh: n=4 p50=1.179 p95=1.516 err=0 age=953.3/1644.9 bytes=919–14549 empty=0; quote: n=5 p50=1.199 p95=1.3 err=0 age=903.0/919.9 bytes=250–255 empty=0

Fixed-window consistency: {"AAPL": {"n": 4, "distinct_bodies": 1, "distinct_sizes": [20013], "n_candles": [61]}, "TSLA": {"n": 3, "distinct_bodies": 1, "distinct_sizes": [20085], "n_candles": [61]}}

Rate-limit headers present: False; header keys seen: ['connection', 'date', 'server', 'transfer-encoding', 'x-origin-nginx']

Latency fit: {}

TIMED_OUT by symbol: {}


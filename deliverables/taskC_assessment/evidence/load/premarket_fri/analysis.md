# Load test analysis — premarket_fri

Window (UTC): 2026-10-16T11:52:56.667Z → 2026-10-16T11:55:23.951Z; requests: 144; stop reason: p50 latency 8.3s at step 3

| step | conc | n | rps | errors | p50 s | p95 s | p99 s | max s | http codes | dx status |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 6 | 0.19 | 0 (0.0%) | 0.756 | 20.005 | 25.015 | 26.267 | {'200': 6} | {'OK': 6} |
| 1 | 5 | 55 | 1.63 | 0 (0.0%) | 2.684 | 3.14 | 5.753 | 5.754 | {'200': 55} | {'OK': 53, 'TIMED_OUT': 2} |
| 2 | 10 | 55 | 1.56 | 0 (0.0%) | 6.199 | 6.705 | 7.948 | 9.334 | {'200': 55} | {'OK': 54, 'TIMED_OUT': 1} |
| 3 | 25 | 28 | 1.68 | 0 (0.0%) | 8.265 | 14.936 | 15.002 | 15.026 | {'200': 28} | {'OK': 28} |

rps = requests / (last completion - first start), i.e. through request completion. Start-to-start spans (older versions of this file) overstate throughput at high concurrency. p50 is computed from completed requests only; the auto-stop therefore also sees completed requests only (censored at high concurrency).


Per kind (p50/p95 s, staleness p50/max s):

- c=1: candle_fixed: n=2 p50=1.106 p95=1.209 err=0 age=75206.2/75207.5 bytes=20013–20085 empty=0; candle_fresh: n=2 p50=0.446 p95=0.515 err=0 age=1614.8/2306.0 bytes=919–14593 empty=0; quote: n=2 p50=13.213 p95=24.962 err=0 age=932.1/937.4 bytes=251–252 empty=0
- c=5: candle_fixed: n=16 p50=2.727 p95=3.034 err=0 age=75235.2/75248.3 bytes=20013–20085 empty=0; candle_fresh: n=19 p50=2.959 p95=5.753 err=0 age=952.0/2327.5 bytes=22–14728 empty=2; quote: n=20 p50=2.465 p95=2.598 err=0 age=901.3/956.5 bytes=250–265 empty=0
- c=10: candle_fixed: n=15 p50=6.289 p95=6.655 err=0 age=75280.8/75297.0 bytes=20013–20085 empty=0; candle_fresh: n=20 p50=6.536 p95=6.843 err=0 age=953.3/2385.4 bytes=22–14592 empty=1; quote: n=20 p50=5.815 p95=6.25 err=0 age=902.0/923.5 bytes=249–266 empty=0
- c=25: candle_fresh: n=3 p50=14.937 p95=15.017 err=0 age=923.2/1343.9 bytes=6581–14596 empty=0; quote: n=25 p50=7.362 p95=13.846 err=0 age=901.5/950.7 bytes=250–265 empty=0

Fixed-window consistency: {"AAPL": {"n": 16, "distinct_bodies": 1, "distinct_sizes": [20013], "n_candles": [61]}, "TSLA": {"n": 17, "distinct_bodies": 1, "distinct_sizes": [20085], "n_candles": [61]}}

Rate-limit headers present: False; header keys seen: ['connection', 'date', 'server', 'transfer-encoding', 'x-origin-nginx']

Latency fit: {"p50": {"linear_slope_s_per_conn": 0.30015, "linear_r2": 0.867, "exp_rate_per_conn": 0.08496, "exp_r2": 0.452, "step_to_step_ratio": [3.55, 2.31, 1.33], "values": [0.756, 2.684, 6.199, 8.265]}, "p95": {"linear_slope_s_per_conn": 0.0517, "linear_r2": 0.005, "exp_rate_per_conn": 0.01719, "exp_r2": -0.107, "step_to_step_ratio": [0.16, 2.14, 2.23], "values": [20.005, 3.14, 6.705, 14.936]}}

TIMED_OUT by symbol: {'AUD/USD': 3}


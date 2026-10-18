# Load test analysis — market_hours_fri

Window (UTC): 2026-10-16T13:47:21.081Z → 2026-10-16T13:51:06.362Z; requests: 504; stop reason: p50 latency 8.3s at step 4

| step | conc | n | rps | errors | p50 s | p95 s | p99 s | max s | http codes | dx status |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 39 | 1.31 | 0 (0.0%) | 0.453 | 0.81 | 2.367 | 3.317 | {'200': 39} | {'OK': 38, 'TIMED_OUT': 1} |
| 1 | 5 | 99 | 3.18 | 0 (0.0%) | 1.141 | 2.299 | 3.964 | 4.546 | {'200': 99} | {'OK': 97, 'TIMED_OUT': 2} |
| 2 | 10 | 104 | 3.19 | 0 (0.0%) | 2.541 | 4.224 | 6.305 | 6.961 | {'200': 104} | {'OK': 101, 'TIMED_OUT': 3} |
| 3 | 25 | 124 | 3.02 | 0 (0.0%) | 5.279 | 12.172 | 14.186 | 14.762 | {'200': 124} | {'OK': 120, 'TIMED_OUT': 4} |
| 4 | 50 | 138 | 2.78 | 0 (0.0%) | 8.283 | 26.552 | 28.241 | 29.169 | {'200': 138} | {'OK': 135, 'TIMED_OUT': 3} |

rps = requests / (last completion - first start), i.e. through request completion. Start-to-start spans (older versions of this file) overstate throughput at high concurrency. p50 is computed from completed requests only; the auto-stop therefore also sees completed requests only (censored at high concurrency).


Per kind (p50/p95 s, staleness p50/max s):

- c=1: candle_fixed: n=13 p50=0.453 p95=0.716 err=0 age=82055.6/82070.9 bytes=20013–20085 empty=0; candle_fresh: n=13 p50=0.663 p95=1.817 err=0 age=934.0/945.3 bytes=22–14650 empty=1; quote: n=13 p50=0.166 p95=0.467 err=0 age=900.3/924.1 bytes=251–268 empty=0
- c=5: candle_fixed: n=31 p50=1.194 p95=2.065 err=0 age=82097.9/82112.2 bytes=20013–20085 empty=0; candle_fresh: n=34 p50=1.728 p95=3.022 err=0 age=916.9/932.3 bytes=22–14661 empty=2; quote: n=34 p50=0.773 p95=1.483 err=0 age=900.5/930.6 bytes=250–268 empty=0
- c=10: candle_fixed: n=31 p50=2.504 p95=4.129 err=0 age=82141.1/82154.3 bytes=20013–20085 empty=0; candle_fresh: n=35 p50=3.192 p95=5.468 err=0 age=946.6/959.8 bytes=22–14733 empty=3; quote: n=38 p50=1.96 p95=3.655 err=0 age=900.3/925.3 bytes=251–268 empty=0
- c=25: candle_fixed: n=36 p50=11.185 p95=11.927 err=0 age=82192.4/82203.1 bytes=20013–20085 empty=0; candle_fresh: n=39 p50=11.939 p95=12.522 err=0 age=943.2/958.3 bytes=22–14678 empty=4; quote: n=49 p50=2.616 p95=11.437 err=0 age=900.5/933.1 bytes=251–268 empty=0
- c=50: candle_fixed: n=17 p50=3.346 p95=3.993 err=0 age=82236.4/82248.2 bytes=20013–20085 empty=0; candle_fresh: n=57 p50=26.385 p95=26.623 err=0 age=944.4/959.2 bytes=22–14773 empty=3; quote: n=64 p50=7.084 p95=24.114 err=0 age=900.4/931.9 bytes=251–268 empty=0

Fixed-window consistency: {"AAPL": {"n": 66, "distinct_bodies": 1, "distinct_sizes": [20013], "n_candles": [61]}, "TSLA": {"n": 62, "distinct_bodies": 1, "distinct_sizes": [20085], "n_candles": [61]}}

Rate-limit headers present: False; header keys seen: ['connection', 'date', 'server', 'transfer-encoding', 'x-origin-nginx']

Latency fit: {"p50": {"linear_slope_s_per_conn": 0.16028, "linear_r2": 0.98, "exp_rate_per_conn": 0.0519, "exp_r2": 0.582, "step_to_step_ratio": [2.52, 2.23, 2.08, 1.57], "values": [0.453, 1.141, 2.541, 5.279, 8.283]}, "p95": {"linear_slope_s_per_conn": 0.53186, "linear_r2": 0.997, "exp_rate_per_conn": 0.06401, "exp_r2": 0.715, "step_to_step_ratio": [2.84, 1.84, 2.88, 2.18], "values": [0.81, 2.299, 4.224, 12.172, 26.552]}}

TIMED_OUT by symbol: {'AUD/USD': 13}


# Little's law — market_hours_fri

Same client: TCPConnector(limit=max(steps)+2)=52, limit_per_host=0 (unlimited).

| c | n | thr | mean_lat | L=thr×lat | L_meas | vs c |
|---|---|---|---|---|---|---|
| 1 | 39 | 1.309 | 0.519 | 0.680 | 0.680 | ≈c |
| 5 | 99 | 3.176 | 1.304 | 4.143 | 4.143 | ≈c |
| 10 | 104 | 3.188 | 2.752 | 8.771 | 8.771 | ≈c |
| 25 | 124 | 3.023 | 6.802 | 20.561 | 20.561 | partial |
| 50 | 138 | 2.781 | 12.977 | 36.089 | 36.089 | partial |

At c=1..10 L≈configured concurrency; c=25/50 are partial duty cycles.
Throughput (through request completion) is flat to slightly declining: 3.18 / 3.19 / 3.02 /
2.78 req/s at c=5/10/25/50, about 2x the pre-market ~1.6 req/s. (An earlier text said
"3.3–4.6 req/s, rising"; that used first-to-last request *start* and is withdrawn.)

Caveat: the connector limit (52) is >= the highest concurrency (50), so the client pool could
never have bound; this analysis cannot say whether the cap is per-IP or shared server
capacity. A second client/IP was not run.

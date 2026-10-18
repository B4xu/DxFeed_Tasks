# Little's law reconciliation — premarket_fri

In-flight L = throughput × mean latency. Measured L via sweep-line on request start/end intervals.
Client: `aiohttp.TCPConnector(limit=max(steps)+2)` → **52** for steps 1,5,10,25,50;
`limit_per_host` left at aiohttp default **0** (unlimited). One session; one in-flight request per worker;
think time 0.25 s between a worker's requests.

| c | n | duration_s | thr (req/s) | mean_lat_s | L = thr×lat | L_measured | L vs c |
|---|---|---|---|---|---|---|---|
| 1 | 6 | 30.8 | 0.195 | 4.922 | 0.959 | 0.959 | matches (~think-time) |
| 5 | 55 | 33.8 | 1.628 | 2.693 | 4.384 | 4.384 | matches (~think-time) |
| 10 | 55 | 35.3 | 1.559 | 5.766 | 8.990 | 8.990 | matches (~think-time) |
| 25 | 28 | 16.6 | 1.682 | 8.184 | 13.764 | 13.764 | early-stop; L<<c |

## Conclusion

At c=1,5,10 measured average in-flight ≈ configured concurrency (within think-time slack).
At c=25 the run auto-stopped on p50>8s after ~17s with only 28 requests; L≈14 < 25 —
not all workers completed a full duty cycle.

Throughput (through completion) stayed ~1.56–1.68 req/s at c=5/10/25 while L≈c. The connector
limit (52) is >= the highest concurrency (50), so the client pool could never have been the
binding constraint. Unresolved: per-IP throttle versus shared server capacity (a second client
was not run).

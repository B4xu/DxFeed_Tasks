# Task B — On-call incident: API error rate 0.2 % → 7 % at 14:02

Scenario: error rate jumps at 14:02, two of five instances at 95 % CPU, no deploy in 24 h,
normal traffic, one enterprise customer reports intermittent 502s. Logs: 502s after ~5.1–5.3 s
("upstream timeout", "context deadline exceeded"), retries to the internal service, pool at
100 active / 0 idle, a 4 800 ms slow query, `/api/health` 200 in 8 ms. Path: API → internal
service → database.

## 1. Investigation plan

### First 5 minutes: golden signals, per tier

| signal | API | internal service | database |
|---|---|---|---|
| **Errors** | 5xx by endpoint, instance, tenant | error and timeout rate | failed/cancelled statements |
| **Latency** | p50/p95/p99 vs the 5 s upstream timeout | p95/p99, queue wait for a DB connection | slow-query log around 14:01–14:02, lock waits |
| **Traffic** | client req/s (normal) | req/s **including retries** (expect up to 2× client rate) | active sessions, statements/s |
| **Saturation** | CPU 95 % on 2 of 5, threads in flight | pool 100/100/0, threads, GC | CPU/IO, connections vs max, replication lag |

Reading of the evidence: the 5.1–5.3 s failures sit on a 5 s timeout, so the API is giving up
on something downstream; the pool is exhausted, so requests wait for a connection and the wait
becomes the timeout; normal traffic plus retries explains the load; `/api/health` does not
exercise API → service → DB, so a green health check is **not** evidence of health.

### Steps

**Step 0 (min 0–2).** Confirm the alert and the customer report describe the same thing (502s
on `/api/orders`), record the exact start time from the metric, open an incident channel and a
timeline. Every later decision and the escalation message hang off the start time.

**Step 1 (min 2–8): scope before touching anything.** Break errors down by endpoint, instance,
tenant, status. Do errors concentrate on the two hot instances (two bad instances) or spread
evenly (shared dependency slow, hot instances just carry the retries)? One customer or many?
What changed at 14:02 despite no deploy: config or flag push, cron or import, certificate
rotation, autoscaling, cloud maintenance, DB failover, plan change?

**Step 2 (min 8–20): walk the chain outside-in** using the table: API timeouts and retry
config, internal-service request rate vs client rate and pool wait, then DB locks, long
statements, the 4 800 ms query, plan or statistics changes that make an old query slow
without code changes.

**Step 3: ranked hypotheses, each with a confirm/reject signal.**

1. *Slow query exhausting the connection pool.* 50 ms → 4.8 s holds 100 connections ~100×
   longer; everything queues and times out at 5 s. Confirm: pool=100 lines up with slow-query
   entries and lock waits; killing the query drops errors in seconds. Reject: pool saturated
   while DB latency is normal.
2. *Retry amplification.* Timeouts trigger retries that take more pool slots and CPU.
   Confirm: internal request rate ≫ client rate, CPU tracks retry volume. Reject: retries flat.
3. *Two degraded or over-weighted instances* (sticky sessions, LB weight, noisy neighbour).
   Confirm: unequal per-instance counts, draining them fixes it. Reject: errors on all five.
4. *One tenant's expensive pattern* (big page size, unindexed filter, export). Confirm:
   slow-query parameters belong to one account; the complaining customer may be cause and
   victim. Reject: many tenants' parameters.
5. *Silent change or infrastructure* (config push, index drop, failover to smaller replica,
   CPU throttling, GC after heap change). "No deploy" rules out code, not config or data.

**Step 4: quick mitigations and their risks.**

- Drain/restart the two hot instances one at a time: low risk if the other three are healthy;
  if the DB is the cause it only moves load.
- Cap retries (one retry, jitter, idempotent reads only): immediate relief, slightly higher
  visible error rate.
- Kill the long query or block the pattern/tenant: often decisive; risk is aborting a
  legitimate job, so record what was killed and tell the owner.
- Raise pool size or timeout only if the DB has headroom: a bigger pool loads a slow DB more,
  a longer timeout hides the problem.
- Rate-limit the expensive endpoint for the affected tenant to protect others.

Each action gets a timestamp and an observed effect in the timeline: "what we tried and what
happened" is the most useful content of the escalation. **Impact** = error rate × request rate
(failed requests/min), tenants above 1 % errors, the enterprise customer's failure share,
duration, SLA budget burned.

## 2. Escalation decision (T+30)

At T+30 the error rate is still 5–8 %, CPU still high, cause not isolated. **Yes, escalate**
now (prepare at ~T+15 when the first mitigations did not hold): customer-facing errors on an
order endpoint, 30 minutes without a stable fix, and the evidence points to a DB/pool problem
L2 cannot fix alone.

**To whom:** the owning backend on-call (pool, retry policy, the query); database/platform
on-call (locks, sessions, parameter or failover changes); an incident commander or support lead
for customer communication so the investigator keeps debugging.

**Earlier** if errors exceed ~10 %, spread to more endpoints or tenants, SLA is at risk, or a
mitigation worsens things.

**One message, then a bridge, containing:**

- Timeline: 14:02 alert, each check and mitigation with time and effect.
- Impact numbers: endpoints, instances, tenants, failed requests/min, enterprise failure share.
- Evidence: pool 100/100/0, 4 800 ms query (fingerprint), per-instance CPU, 5 s timeouts, retry
  counts, health check green but not exercising the path.
- Hypotheses tested and rejected, with the data.
- Mitigations and measured effect (e.g. draining X: 7 % → 5 % for 4 minutes, then back).
- A specific ask: "inspect/kill sessions for fingerprint Y, tell us if a plan change or lock
  explains 4.8 s, and give a go/no-go on raising the pool."
- Proposed severity (e.g. SEV-2) and the next customer update time.

**What would change the decision:** if killing the query or capping retries returned the rate
to baseline for 15 minutes with CPU normal, I would open a ticket with evidence instead of an
incident; with a non-critical endpoint and no customer reports, lower severity and escalate
only if it persists.

## 3. Preventive improvements

**(a) Dependency-aware observability — detection.** We found pool exhaustion in a log line and
the slow query in a warning while the health check was green. Add per-dependency metrics (pool
utilisation and queue wait, service and DB latency percentiles, retries, timeouts), alert on
pool > 80 % for 2 min and queue wait p95 > 500 ms, add distributed tracing, and make readiness
run a cheap real query through the internal service.

**(b) Resilience in the call path — impact.** Retries amplified load and the 5 s timeout let
requests pile up. Add a retry budget (≤ 10 % of requests, jittered backoff, idempotent calls),
make the DB timeout shorter than the API's (2 s < 5 s), add a circuit breaker and per-tenant
concurrency limits with load shedding, so a 4.8 s query cannot become a 7 % error rate for
everyone.

**(c) Query and capacity hygiene — recurrence.** Alert on statements > 1 s, set DB statement
timeouts, fix the query's index or plan, flag plan changes after statistics refreshes, review
pool size vs DB max connections vs instance count, add a runbook entry for "pool exhausted +
slow query", and hold a post-incident review so the owning team fixes the query.

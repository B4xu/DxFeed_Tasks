"""Build TaskB_Incident_Report.docx with its diagrams.

    python build_report.py

Diagrams are drawn with matplotlib into charts/. The pool-capacity chart is arithmetic from the
scenario (100 connections, 4.8 s query), labelled as illustrative.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import report_kit as rk  # noqa: E402
from report_kit import AMBER, BLUE, CORAL, GREEN, NAVY, SLATE, TEAL, plt  # noqa: E402

CH = HERE / "charts"
OUT = HERE / "TaskB_Incident_Report.docx"


def _box(ax, x, y, w, h, text, color, fs=11, tc="white"):
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=color, ec="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs, fontweight="bold")


def _arrow(ax, x1, y1, x2, y2, color=SLATE, text=None):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=color, lw=2))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, text, ha="center", fontsize=9, color=color)


def chain_diagram():
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    _box(ax, 0.2, 2.6, 1.8, 1.0, "Client\n(enterprise)", SLATE)
    _box(ax, 3.0, 2.6, 2.0, 1.0, "API\n5 instances", NAVY)
    _box(ax, 6.0, 2.6, 2.2, 1.0, "Internal\nservice", TEAL)
    _box(ax, 9.0, 2.6, 1.8, 1.0, "Database", CORAL)
    _arrow(ax, 2.0, 3.1, 3.0, 3.1)
    _arrow(ax, 5.0, 3.1, 6.0, 3.1, text="retries")
    _arrow(ax, 8.2, 3.1, 9.0, 3.1)
    ax.text(8.6, 3.75, "pool 100/100", ha="center", fontsize=9, color=SLATE)
    notes = [
        (1.1, "502 after\n5.1–5.3 s", CORAL),
        (4.0, "2 of 5 at 95 % CPU\n/api/health 200 in 8 ms\n(does not touch DB)", AMBER),
        (7.1, "pool: 100 active, 0 idle\n'context deadline exceeded'", CORAL),
        (9.9, "query 4,800 ms", CORAL),
    ]
    for x, t, c in notes:
        ax.text(x, 1.7, t, ha="center", va="top", fontsize=9.5, color=c, fontweight="bold")
        ax.plot([x, x], [1.8, 2.55], color=c, lw=1, ls=":")
    ax.text(5.5, 4.35, "Symptoms mapped onto the call path", ha="center", fontsize=14, fontweight="bold", color=NAVY)
    ax.text(5.5, 0.25, "Reading: the 5 s timeouts sit at the API but the wait is downstream: a slow query holds the pool, "
            "everything behind it queues.", ha="center", fontsize=9.5, color=SLATE, style="italic")
    p = CH / "call_path.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def timeline():
    steps = [
        (0, 2, "Acknowledge,\nconfirm, channel", SLATE),
        (2, 8, "Scope: endpoint,\ninstance, tenant", BLUE),
        (8, 20, "Walk the chain:\nAPI → service → DB", TEAL),
        (12, 25, "Mitigate:\nkill query, cap retries", AMBER),
        (15, 30, "Prepare escalation", CORAL),
    ]
    fig, ax = plt.subplots(figsize=(11, 3.8))
    for i, (a, b, t, c) in enumerate(steps):
        ax.barh(i, b - a, left=a, color=c, height=0.6)
        inside = b - a >= 5
        ax.text(a + 0.3 if inside else b + 0.3, i, t, va="center", fontsize=9,
                color="white" if inside else c, fontweight="bold")
    ax.axvline(30, color=CORAL, lw=2, ls="--")
    ax.text(30.2, 4.35, "T+30: escalate", color=CORAL, fontweight="bold")
    ax.set_yticks([])
    ax.set_xlim(0, 34)
    ax.set_xlabel("Minutes after the 14:02 alert")
    ax.set_title("First 30 minutes: overlapping workstreams, not a strict sequence")
    ax.invert_yaxis()
    p = CH / "first_30_minutes.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def pool_capacity():
    q = [0.05, 0.2, 0.5, 1.0, 2.0, 4.8]
    cap = [100 / x for x in q]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.bar([f"{int(x * 1000)} ms" for x in q], cap, color=[GREEN, GREEN, AMBER, AMBER, CORAL, CORAL])
    for b, v in zip(bars, cap):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.08, f"{v:,.0f}/s", ha="center", fontsize=9.5, color=NAVY, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylabel("Max queries/s the 100-connection pool can serve (log)")
    ax.set_xlabel("Time each query holds a connection")
    ax.set_title("Illustrative: a 4.8 s query cuts pool capacity to ~21 queries/s")
    p = CH / "pool_capacity.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def decision_tree():
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    _box(ax, 3.6, 4.3, 3.8, 0.8, "T+30: errors still 5–8 %?", NAVY, 11)
    _box(ax, 0.3, 2.6, 4.0, 0.9, "Yes, cause not isolated\n→ ESCALATE now (SEV-2)", CORAL, 10.5)
    _box(ax, 6.7, 2.6, 4.0, 0.9, "No: back to baseline\nfor 15 min after a fix", GREEN, 10.5)
    _arrow(ax, 4.6, 4.3, 2.3, 3.5, CORAL, "yes")
    _arrow(ax, 6.4, 4.3, 8.7, 3.5, GREEN, "no")
    _box(ax, 0.3, 0.4, 4.0, 1.7, "Backend on-call (pool, retries, query)\nDB / platform on-call (locks, sessions)\nIncident commander (comms)\nOne message, then a bridge", NAVY, 9.5)
    _box(ax, 6.7, 0.4, 4.0, 1.7, "Ticket to owning team with evidence\nfor the root-cause fix;\nkeep monitoring;\nlower severity", TEAL, 9.5)
    _arrow(ax, 2.3, 2.6, 2.3, 2.1)
    _arrow(ax, 8.7, 2.6, 8.7, 2.1)
    ax.text(5.5, 2.0, "Escalate earlier if:\n> 10 % errors\nmore endpoints/tenants\nSLA at risk\na mitigation backfires",
            ha="center", va="center", fontsize=9, color=AMBER, fontweight="bold")
    p = CH / "escalation_decision.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def build() -> Path:
    CH.mkdir(exist_ok=True)
    rk.mpl_style()
    for k in ("axes.grid",):
        plt.rcParams[k] = True
    chain = chain_diagram()
    tl = timeline()
    pool = pool_capacity()
    tree = decision_tree()

    rk.reset_figures()
    doc = rk.new_document()
    rk.cover(doc, "On-call incident: API error rate 0.2 % → 7 %",
             "Investigation plan, escalation decision at T+30 and three preventive improvements",
             "Task B · L2 Support Engineer assessment",
             [("Alert", "14:02 — API error rate jumps from 0.2 % to 7 %"),
              ("Signals", "2 of 5 instances at 95 % CPU; no deploy in 24 h; normal traffic"),
              ("Customer", "One enterprise customer reports intermittent 502s"),
              ("Logs", "502 after ~5.1–5.3 s; retries; pool 100 active / 0 idle; 4,800 ms query; /api/health 200 in 8 ms"),
              ("Path", "API → internal service → database")])

    doc.add_heading("1. Summary", level=1)
    rk.para(doc,
            "My reading of the evidence before touching anything: the API is not broken on its own. The 502s land "
            "just after a 5-second upstream timeout, which means the API is giving up on something downstream. The "
            "internal service's database pool is fully used with nothing idle, and a query that should take "
            "milliseconds is taking 4.8 seconds. A slow query holding connections, amplified by retries, is the "
            "most likely story. The green health check is not evidence of health, because it never touches the "
            "database.")
    rk.kpi_strip(doc, [("7 %", "error rate (from 0.2 %)", CORAL), ("5 s", "upstream timeout hit", AMBER),
                       ("100/100", "pool connections busy", CORAL), ("4.8 s", "slow query", NAVY),
                       ("T+30", "escalate", TEAL)])
    rk.figure(doc, chain, "Every symptom from the scenario placed on the call path.")
    doc.add_heading("2. Investigation plan", level=1)
    doc.add_heading("2.1 First five minutes: golden signals per tier", level=2)
    rk.para(doc,
            "I start with the four golden signals (errors, latency, traffic, saturation) for each tier, because a "
            "table like this shows within minutes where the time is going, and it is the same table I will paste "
            "into the escalation.")
    rk.table(doc, ["Signal", "API", "Internal service", "Database"], [
        ["Errors", "5xx by endpoint, instance, tenant", "Error and timeout rate", "Failed or cancelled statements"],
        ["Latency", "p50/p95/p99 vs the 5 s timeout", "p95/p99; queue wait for a DB connection", "Slow-query log 14:01–14:02; lock waits"],
        ["Traffic", "Client req/s (normal)", "Req/s including retries (up to 2× client)", "Active sessions, statements/s"],
        ["Saturation", "CPU 95 % on 2 of 5; threads", "Pool 100/100/0; threads; GC", "CPU/IO; connections vs max; replica lag"],
    ], widths_cm=[2.4, 4.6, 4.8, 4.8])
    doc.add_heading("2.2 The steps", level=2)
    rk.figure(doc, tl, "How the first thirty minutes overlap.")
    rk.para(doc,
            "Confirm the alert and the customer report describe the same thing (502s on /api/orders, not a dashboard "
            "artefact), note the exact start time from the metric and open an incident channel with a running "
            "timeline. Everything later, including the escalation, hangs off that start time.",
            bold_lead="Step 0 (minutes 0–2): acknowledge.")
    rk.para(doc,
            "Break errors down by endpoint, instance, tenant and status code before changing anything. If the 502s "
            "concentrate on the two hot instances, I have two bad instances. If they are spread evenly, a shared "
            "dependency is slow and the hot instances are simply carrying the retries. I also ask what changed at "
            "14:02 even without a deploy: a config or feature-flag push, a cron job or import, certificate rotation, "
            "autoscaling, cloud maintenance, a database failover or a query-plan change.",
            bold_lead="Step 1 (minutes 2–8): scope before touching anything.")
    rk.para(doc,
            "At the API: timeouts, retry configuration and retry counts. At the internal service: request rate "
            "compared with the client rate (retries can double it while traffic 'looks normal'), connection wait time "
            "and pool metrics. At the database: locks, long-running statements, the 4.8-second query, and any plan "
            "or statistics change that makes an old query slow without code changing.",
            bold_lead="Step 2 (minutes 8–20): walk the chain from the outside in.")
    rk.figure(doc, pool, "Why one slow query is enough: a pool's throughput is its size divided by how long each query holds a connection (Little's law).")

    doc.add_heading("2.3 Ranked hypotheses", level=2)
    rk.table(doc, ["#", "Hypothesis", "Confirms it", "Rejects it"], [
        ["1", "Slow query exhausting the pool", "Pool = 100 lines up with slow-query entries and lock waits; killing the query drops errors within seconds", "Pool saturated while DB latency is normal"],
        ["2", "Retry amplification", "Internal request rate ≫ client rate; CPU tracks retry volume", "Retry count flat at 14:02"],
        ["3", "Two degraded or over-weighted instances", "Unequal per-instance request counts; draining them fixes it", "Errors spread across all five"],
        ["4", "One tenant's expensive pattern", "Slow-query parameters belong to one account", "Many tenants' parameters"],
        ["5", "Silent change or infrastructure", "Config, index, failover or throttling event at 14:02", "Nothing in config/DB/cloud history"],
    ], widths_cm=[0.8, 4.2, 6.0, 5.6], font_size=9.5)
    rk.para(doc,
            "'No deployment' rules out application code, not configuration or data. The complaining enterprise "
            "customer may turn out to be the cause as well as the victim (hypothesis 4).")

    doc.add_heading("2.4 Quick mitigations and their risks", level=2)
    rk.table(doc, ["Mitigation", "Expected effect", "Risk"], [
        ["Drain/restart the two hot instances, one at a time", "Relief if the instances are the problem", "If the DB is the cause, load just moves"],
        ["Cap retries (one, jittered, idempotent reads only)", "Immediate relief from amplification", "Slightly higher visible error rate"],
        ["Kill the long query or block the pattern/tenant", "Often fixes it", "May abort a legitimate job; record it and tell the owner"],
        ["Raise pool size or timeout", "Only with clear DB headroom", "Bigger pool loads a slow DB more; longer timeout hides the problem"],
        ["Rate-limit the expensive endpoint for one tenant", "Protects other customers", "That tenant sees more errors"],
    ], widths_cm=[5.4, 5.0, 6.2])
    rk.callout(doc, "Quantifying impact", "Failed requests per minute = error rate × request rate; number of tenants above "
               "1 % errors; the enterprise customer's failure share; duration so far; SLA budget burned. Every "
               "mitigation gets a timestamp and an observed effect in the timeline.", TEAL)
    doc.add_heading("3. Escalation decision at T+30", level=1)
    rk.para(doc,
            "Thirty minutes in, the error rate still swings between 5 and 8 %, CPU is still high on two instances, and "
            "the cause is not isolated. I escalate now, and I would have had the message drafted at T+15 when the "
            "first mitigations did not hold. The reasons are customer impact on an order endpoint, thirty minutes "
            "without a stable fix, and evidence pointing at a database and pool problem that L2 cannot fix alone.")
    rk.figure(doc, tree, "The T+30 decision and what would change it.")
    doc.add_heading("What the escalation message contains", level=2)
    rk.bullets(doc, [
        ("Timeline:", "14:02 alert, then each check and mitigation with time and effect."),
        ("Impact:", "endpoints, instances, tenants, failed requests per minute, the enterprise customer's failure share."),
        ("Evidence:", "pool 100/100/0, the 4.8 s query fingerprint, per-instance CPU, 5 s timeouts, retry counts, the misleading health check."),
        ("Tested and rejected:", "each hypothesis with the data that rejected it."),
        ("Mitigations and effect:", "for example 'draining instance X reduced errors from 7 % to 5 % for four minutes, then they returned'."),
        ("A specific ask:", "inspect and kill sessions for fingerprint Y, say whether a plan change or lock explains 4.8 s, and give a go/no-go on raising the pool."),
        ("Severity and next update:", "proposed SEV-2 and the time of the next customer update."),
    ])
    rk.para(doc,
            "If killing the query or capping retries had returned the error rate to baseline for fifteen minutes with "
            "CPU normal, I would open a ticket with the evidence for the owning team instead of running an incident. "
            "If only a non-critical endpoint were affected with no customer reports, I would hold a lower severity and "
            "escalate only if it persisted past the next check-in.", bold_lead="What would change the decision.")

    doc.add_heading("4. Three preventive improvements", level=1)
    rk.table(doc, ["Improvement", "Improves", "What exactly"], [
        ["Dependency-aware observability", "Detection",
         "Per-dependency metrics (pool use and queue wait, service and DB latency, retries, timeouts); alerts on pool > 80 % for 2 min and queue wait p95 > 500 ms; distributed tracing; a readiness probe that runs a cheap real query through the internal service"],
        ["Resilience in the call path", "Impact",
         "Retry budget (≤ 10 % of requests, jittered backoff, idempotent only); DB timeout shorter than the API's (2 s < 5 s); circuit breaker; per-tenant concurrency limits and load shedding"],
        ["Query and capacity hygiene", "Recurrence",
         "Alert on statements > 1 s; DB statement timeouts; fix the index or pin the plan; flag plan changes after statistics refreshes; pool size vs DB max connections review; runbook entry; post-incident review"],
    ], widths_cm=[4.0, 2.4, 10.2])
    rk.para(doc,
            "Together these turn this incident from 'a customer called us' into 'an alert fired before the error rate "
            "moved', keep a slow query from becoming a 7 % error rate for everyone, and make sure the owning team fixes "
            "the query instead of on-call killing it again next month.")

    rk.footer(doc, "Task B — on-call incident · source: deliverables/taskB_incident/answer.md")
    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())

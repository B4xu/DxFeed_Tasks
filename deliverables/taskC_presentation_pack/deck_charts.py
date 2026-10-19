"""Charts used only by the Task C deck (the report charts live in taskC_assessment/charts/).

The holiday calendars are drawn from the Task A output CSV; the Task A report itself has no charts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import report_kit as rk  # noqa: E402

plt = rk.plt
LOAD = ROOT / "taskC_assessment" / "evidence" / "load"
HOLIDAYS = ROOT / "taskA_holidays" / "output" / "trading_holidays_combined.csv"
OUT = HERE / "charts"


def _steps(run):
    a = json.loads((LOAD / run / "analysis.json").read_text())
    return a["per_step"]


def load_two_panel() -> Path:
    mh = _steps("market_hours_fri")
    c = [s["concurrency"] for s in mh]
    rps = [s["rps"] for s in mh]
    p50 = [s["p50"] for s in mh]
    p95 = [s["p95"] for s in mh]
    x = range(len(c))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.6))
    bars = a1.bar(x, rps, 0.6, color=rk.TEAL)
    for b, v in zip(bars, rps):
        a1.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.2f}", ha="center", fontweight="bold", color=rk.NAVY)
    a1.set_xticks(list(x), [f"{v}" for v in c])
    a1.set_ylim(0, 4)
    a1.set_xlabel("Parallel workers")
    a1.set_ylabel("Requests per second")
    a1.set_title("Throughput: flat after 5 workers")

    a2.plot(x, p95, "o-", color=rk.CORAL, lw=2.6, ms=8, label="p95")
    a2.plot(x, p50, "o-", color=rk.NAVY, lw=2.6, ms=8, label="p50")
    for i, (m, h) in enumerate(zip(p50, p95)):
        a2.annotate(f"{h:.1f} s", (i, h), textcoords="offset points", xytext=(0, 9), ha="center", color=rk.CORAL, fontweight="bold")
        a2.annotate(f"{m:.1f} s", (i, m), textcoords="offset points", xytext=(0, -17), ha="center", color=rk.NAVY, fontweight="bold")
    a2.set_xticks(list(x), [f"{v}" for v in c])
    a2.set_ylim(-2, 31)
    a2.set_xlabel("Parallel workers")
    a2.set_ylabel("Latency (seconds)")
    a2.set_title("Latency: from 0.5 s to 26 s")
    a2.legend(loc="upper left")
    fig.tight_layout(w_pad=3)
    path = OUT / "load_two_panel.png"
    fig.savefig(path)
    plt.close(fig)
    return path


RISKS = [
    # (n, label, likelihood, impact)
    (1, "Silent 8,000 cap", 2.85, 2.85),
    (2, "Volume depends on timeframe", 2.75, 2.35),
    (3, "Queues, never says 429", 2.3, 2.0),
    (4, "Stale looks like closed", 2.95, 2.45),
    (5, "Symbol quirks (TIMED_OUT, FX bid)", 1.9, 1.75),
    (6, "FX prints outside session", 2.2, 1.3),
    (7, "Monitors only watch HTTP errors", 2.65, 1.65),
]


def risk_matrix() -> Path:
    fig, ax = plt.subplots(figsize=(7.4, 5.6))
    ax.set_xlim(1, 3.2)
    ax.set_ylim(1, 3.2)
    for x0, y0, col in [(1, 1, "#EAF6F3"), (2.1, 2.1, "#FDECE7"), (2.1, 1, "#FFF5E3"), (1, 2.1, "#FFF5E3")]:
        ax.add_patch(plt.Rectangle((x0, y0), 1.1, 1.1, color=col, zorder=0))
    for n, _, lk, im in RISKS:
        col = rk.CORAL if lk + im > 5 else rk.AMBER if lk + im > 4 else rk.TEAL
        ax.scatter(lk, im, s=900, color=col, edgecolor="white", linewidth=2, zorder=3)
        ax.text(lk, im, str(n), ha="center", va="center", color="white", fontweight="bold", fontsize=14, zorder=4)
    ax.set_xticks([1.55, 2.65], ["sometimes", "often / always"])
    ax.set_yticks([1.55, 2.65], ["annoying", "wrong decisions"])
    ax.set_xlabel("How often I saw it")
    ax.set_ylabel("Damage if nobody notices")
    ax.grid(False)
    path = OUT / "risk_matrix.png"
    fig.savefig(path)
    plt.close(fig)
    return path


EVENTS = [
    ("Thu 20:30", "Client's nightly\nreconciliation flags it", rk.SLATE),
    ("21:05", "P1 ticket opened", rk.CORAL),
    ("21:15", "Reproduced on demo:\n130 ETH + 1 RTH", rk.TEAL),
    ("21:40", "Same on TSLA;\ndaily total checked", rk.TEAL),
    ("22:00", "Escalated to\naggregation on-call", rk.AMBER),
    ("22:30", "First client update:\nfacts, next-update time", rk.GREEN),
    ("Fri 09:00", "Engineering confirming\nthe reference series", rk.NAVY),
]


def incident_timeline() -> Path:
    fig, ax = plt.subplots(figsize=(12.5, 3.6))
    n = len(EVENTS)
    ax.plot([0, n - 1], [0, 0], color="#C9CED6", lw=3, zorder=1)
    for i, (t, label, col) in enumerate(EVENTS):
        up = i % 2 == 0
        ax.scatter(i, 0, s=260, color=col, zorder=3, edgecolor="white", linewidth=2)
        ax.plot([i, i], [0, 0.42 if up else -0.42], color=col, lw=1.6, zorder=2)
        ax.text(i, 0.5 if up else -0.5, label, ha="center", va="bottom" if up else "top", fontsize=10.5, color=rk.INK)
        ax.text(i, -0.14 if up else 0.14, t, ha="center", va="top" if up else "bottom", fontsize=10.5, fontweight="bold", color=col)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-1.25, 1.25)
    ax.axis("off")
    path = OUT / "incident_timeline.png"
    fig.savefig(path)
    plt.close(fig)
    return path


EX_COLORS = {"NYSE": rk.NAVY, "NASDAQ": rk.TEAL, "OPRA": rk.BLUE, "CME": rk.CORAL}


def holiday_calendar(year: int, exchanges: list[str], title: str, note: str | None = None) -> Path:
    import matplotlib.dates as mdates
    import pandas as pd
    df = pd.read_csv(HOLIDAYS, dtype=str).fillna("")
    df["dt"] = pd.to_datetime(df["date"])
    d = df[df["dt"].dt.year == year]
    fig, ax = plt.subplots(figsize=(11, 0.9 * len(exchanges) + 0.9))
    for i, e in enumerate(exchanges):
        g = d[d.exchange == e]
        for _, r in g.iterrows():
            closed = r.status == "closed"
            ax.scatter(r["dt"], i, s=110, marker="o" if closed else "D",
                       color=EX_COLORS[e] if closed else rk.AMBER, edgecolor="white", zorder=3)
        if g.empty:
            ax.text(pd.Timestamp(f"{year}-07-01"), i, f"no {year} schedule published yet", ha="center",
                    va="center", fontsize=10, color=rk.SLATE, style="italic")
    ax.set_yticks(range(len(exchanges)), exchanges)
    ax.set_ylim(-0.7, len(exchanges) - 0.3)
    ax.invert_yaxis()
    ax.set_xlim(pd.Timestamp(f"{year - 1}-12-20"), pd.Timestamp(f"{year + 1}-01-05"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title(title)
    if note:
        ax.text(pd.Timestamp(f"{year}-06-01"), len(exchanges) - 0.55, note, fontsize=9, color=rk.SLATE, ha="center")
    path = OUT / f"calendar_{year}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    rk.mpl_style()
    return {
        "load": load_two_panel(), "risk": risk_matrix(), "timeline": incident_timeline(),
        "cal2026": holiday_calendar(
            2026, ["NYSE", "NASDAQ", "OPRA"],
            "2026 closures (circles) and early closes (diamonds): NYSE and NASDAQ line up exactly",
            "OPRA source is the 2025 PDF; only 1 Jan 2026 spills into this year"),
        "cal2027": holiday_calendar(
            2027, ["NYSE", "CME", "NASDAQ", "OPRA"],
            "2027 closures (circles) and early closes (diamonds): NYSE and CME line up exactly"),
    }


if __name__ == "__main__":
    for k, v in main().items():
        print(k, v)

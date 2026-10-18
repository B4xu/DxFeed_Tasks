#!/usr/bin/env python3
"""Build the Task C presentation pack: deck, supporting materials, speaker script.

Offline only — uses existing markdown and evidence plots. No demo traffic.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent


def build_supporting_materials():
    text = """# Supporting materials — Task C

Evidence paths are relative to `deliverables/taskC_assessment/evidence/` unless they start with
`taskC_assessment/`. **No new demo traffic required** for the live talk; use offline fallbacks below.

Written reports: `taskC_assessment/TaskC_Assessment_Report.docx`,
`taskB_incident/TaskB_Incident_Report.docx`, `taskA_holidays/TaskA_Holiday_Scraper_Report.docx`.
Rebuild everything with `python deliverables/build_all.py`.

## Finding → script → evidence → visual

| Finding | Script(s) | Evidence | Plot / screenshot |
|---|---|---|---|
| 15-min delay (~900 s) | `weekend_logger.py`, `analyze_logger.py`, `sse_compare.py` | `weekend_logger/`, `sse/` | `plots/logger/data_age_timeline.png` |
| Series integrity / holidays | `validate_candles.py`, `fetch_candles.py` | `validation/pass1/`, `candles/pass1/` | `plots/pass1/per_day_1m_counts.png` |
| Silent 8000 retention | `fetch_candles.py`, probe tags `cap_test*` | `candles/pass1/chunks.jsonl`, `probe/` | (table in report; count=8000 in raw JSON) |
| 1h vs Σ5m volume (ETH + RTH) | `validate_candles.py` | `validation/pass1/agg_AAPL_1h_from_5m.csv`, `agg_TSLA_*` | `plots/pass1/agg_AAPL_1h_from_5m.png` |
| RTH exception detail | offline CSV + `refetch/` | `refetch/refetch_compare.json` | same agg plot |
| FX outside-session candles (50 at 1m) | `validate_candles.py`, `offline_recheck.py` | `candles/pass1/EURUSD_1m.csv`, `validation/pass1/recheck.json` | `taskC_assessment/charts/fx_outside_session.png` |
| Load queueing / Little's law | `load_test.py`, `analyze_load.py` | `load/premarket_fri/`, `load/market_hours_fri/`, `littles_law.md` | `taskC_assessment/charts/throughput_vs_concurrency.png`, `latency_by_request_type.png` |
| SSE vs REST | `sse_compare.py` | `sse/20261016T120829Z/`, `sse/20261016T135132Z/` | summary.json |
| Radar vs REST | manual + REST compare JSON | `radar/compare_*.json` | `radar/radar_last_candle_*.png` |

## Offline reproduce (talk laptop)

```bash
conda activate dxfeed
cd deliverables/taskC_assessment/scripts
python validate_candles.py --pass pass1          # ~seconds, offline
python analyze_load.py --run premarket_fri       # offline
python analyze_load.py --run market_hours_fri    # offline
# Open CSVs/PNGs under evidence/ — do not need network
```

## Live demos (optional) + fallbacks

1. **8000 cap** — live REST long `fromTime` *or* open `evidence/candles/pass1/chunks.jsonl` + raw body.
2. **1h vs 5m** — `validate_candles.py --pass pass1` then open AAPL row 2026-10-02 18:00 ET and RTH 2026-10-08 11:00 ET in the agg CSV; fallback PNG already in pack/report.
3. **Radar** — screenshots in `evidence/radar/` (no need to open radar.dxfeed.com live).

## Honesty checklist (say out loud if asked)

- AAPL **1** RTH volume mismatch, TSLA **2** — not zero
- Pool limit 52 >= max c 50 so it never bound; per-IP vs shared capacity unresolved
- Market hours had ~2x pre-market throughput (through completion); throughput is flat in c, not rising
- Pass 2 / full logger analysis: **Monday after 15:30Z**
- Logger collection gap ~Fri 14:49Z → Sat restart
- TimeAndSale: **blocked** on demo REST
"""
    path = OUT / "SUPPORTING_MATERIALS.md"
    path.write_text(text)
    return path


def build_speaker_script(script_parts, n_slides):
    lines = [
        "# Speaker script — Task C 45-minute live presentation",
        "",
        f"**Slides:** {n_slides} · **Target:** 45 minutes  ",
        "**Pacing:** ~5 min context · 15 min data · 8 min load · 7 min risk/incident · 5 min improvements · 5 min Q&A",
        "",
        "## Global rules while speaking",
        "- Lead with method and validation, then findings.",
        "- Say **verified** vs **hypothesis** out loud.",
        "- Never say “0 RTH mismatches”, “OHLC always agrees”, “214 weekend candles”, or throughput “rising to 4.6”.",
        "- If demo network fails: use offline fallbacks in SUPPORTING_MATERIALS.md.",
        "",
        "---",
        "",
    ]
    # Approximate minutes per section by slide index
    for i, (title, notes) in enumerate(script_parts):
        lines.append(f"## Slide {i + 1} — {title}")
        lines.append("")
        lines.append(notes.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend(
        [
            "## Anticipated Q&A (grounded answers)",
            "",
            "**Q: Isn’t the 8000 cap just the demo’s quota?**  ",
            "A: Probably intentional. The defect is `status: OK` with no truncation signal, and older windows look like holidays. A flag or one docs sentence fixes the client-visible failure mode.",
            "",
            "**Q: Could hourly volume just be late prints?**  ",
            "A: On the one daily candle we have (2026-10-14) the hourly sum is closer to daily than the 1m sum, so we do not say which series is the reference. ETH pattern is systematic. AAPL and TSLA RTH exceptions fall on the same day/hour with the opposite sign; re-fetch stable after +11.5 min. TimeAndSale is TIMED_OUT; SPY/MSFT and tho=true not tested.",
            "",
            "**Q: What does the load test prove about production?**  ",
            "A: Nothing about production capacity. It shows *this* shared demo queues without 429 for one client. Monitoring design transfers; absolute RPS numbers do not.",
            "",
            "**Q: Why not crypto?**  ",
            "A: Demo returns TIMED_OUT for BTC/USD and variants. TSLA substituted; ES added as a session control. Probe logs kept.",
            "",
            "**Q: Did you find zero RTH volume mismatches?**  ",
            "A: No. AAPL 1, TSLA 2 in the sample. Wording was corrected; pattern remains overwhelmingly ETH.",
            "",
            "**Q: Is the load plateau your aiohttp pool?**  ",
            "A: The pool limit (52) is above the max concurrency (50), so it could never bind. Whether the cap is per-IP or shared capacity is unresolved; a second client was not run.",
            "",
            "**Q: What did you not verify?**  ",
            "A: Pass 2 / complete weekend analysis (Monday); TimeAndSale root cause; second client for load; Task A Drive/CME are separate.",
            "",
            "**Q: Was the load test polite?**  ",
            "A: Auto-stop p50>8s, think time, budgets, no 429 observed; full request logs in evidence/load/.",
            "",
            "## Closing line",
            "",
            "“Happy to open any evidence file live. The transferable outcome is how we investigate silent failures — retention OK, cross-timeframe volume, and queueing without back-pressure — not a claim about production capacity.”",
            "",
        ]
    )
    path = OUT / "SPEAKER_SCRIPT.md"
    path.write_text("\n".join(lines))
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    from visual_deck import build_visual_pptx, make_summary_charts

    charts = make_summary_charts()
    pptx_path, parts, n = build_visual_pptx(charts)
    print("  ->", pptx_path, "slides=", n)
    print("  ->", build_supporting_materials())
    print("  ->", build_speaker_script(parts, n))


if __name__ == "__main__":
    main()

# Supporting materials — Task C

Evidence paths are relative to `deliverables/taskC_assessment/evidence/` unless they start with
`taskC_assessment/`. **No new demo traffic required** for the live talk; use offline fallbacks below.

The deck and the written reports (Word and PDF) are in `submission/` at the repository root:
`TaskC_Live_Presentation.pptx`, `TaskC_Assessment_Report.docx`, `TaskB_Incident_Report.docx`,
`TaskA_Holiday_Scraper_Report.docx`.
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

# Validation report — 2026-10-16T11:31:01Z

Overall: **WARN**

| check | level | detail |
|---|---|---|
| NYSE.rows | PASS | NYSE returned 34 rows |
| NASDAQ.rows | PASS | NASDAQ returned 12 rows |
| OPRA.rows | PASS | OPRA returned 14 rows |
| CME.rows | WARN | CME returned 0 rows (manual input required, see notes) |
| weekday | PASS | 0 weekend-dated rows |
| duplicates | PASS | 0 duplicate (exchange,date,status) rows |
| NASDAQ.2026.closures | PASS | 10 full-day closures (plausible 8-11) |
| NYSE.2026.closures | PASS | 10 full-day closures (plausible 8-11) |
| NYSE.2027.closures | PASS | 10 full-day closures (plausible 8-11) |
| NYSE.2028.closures | PASS | 9 full-day closures (plausible 8-11) |
| OPRA.2025.closures | PASS | 10 full-day closures (plausible 8-11) |
| OPRA.2026.closures | PASS | 1 closure(s) spilling from source_year 2025 |
| early_close_time | PASS | 0 early-close rows without a close time |
| NYSE_vs_NASDAQ.closed | PASS | years [2026]: 0 differing dates |
| NYSE_vs_NASDAQ.early_close | PASS | years [2026]: 0 differing dates |
| NYSE_vs_OPRA | WARN | no overlapping source years ([2026, 2027, 2028] vs [2025]); comparison skipped |
| NASDAQ_vs_OPRA | WARN | no overlapping source years ([2026] vs [2025]); comparison skipped |
| good_friday | PASS | 5 Good Friday rows checked against Easter-2 |
| diff_previous | PASS | rows 60 -> 60 (0.0% change, threshold 30.0%); added 0: []; removed 0: [] |

## Row counts

| exchange | closed | early_close | years |
|---|---|---|---|
| NASDAQ | 10 | 2 | [2026] |
| NYSE | 29 | 5 | [2026, 2027, 2028] |
| OPRA | 11 | 3 | [2025, 2026] |

## Adapter notes

- NYSE: NYSE 2028: 'New Year's Day' not observed ('—')
- NASDAQ: source=nasdaqtrader.com rows=12
- OPRA: OPRA PDFs discovered: {2025: 'https://cdn.opraplan.com/documents/notices/2025_HOLIDAY_SCHEDULE.pdf'}
- CME: CME: MANUAL_INPUT_REQUIRED - cmegroup.com blocks automated clients (HTTP 403) and its Data Terms of Use prohibit scraping. Download the equity-index holiday PDFs/CSV manually into /home/irakli/Documents/DxFeed/deliverables/taskA_holidays/input/cme.

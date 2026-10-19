# CME manual input

cmegroup.com returns HTTP 403 to automated clients and its Data Terms of Use prohibit
scraping, so the CME adapter reads files you download by hand into this folder.

## Accepted formats

1. **`*.xlsx`** — Trading Hours → Holidays “Download data” export from
   https://www.cmegroup.com/trading-hours.html (one file per holiday is fine).
   Only the **Equities** asset-class row is parsed (Globex US equity index scope).

2. **`*.csv`** — hand-written table with this header (times are Chicago local, HH:MM):

```
date,holiday_name,status,close_time_local,product_scope,source_url
2026-11-26,Thanksgiving Day,early_close,12:00,CME Globex US Equity Index futures,https://www.cmegroup.com/...
```

`status` is `closed` or `early_close`.

3. **`*.pdf`** — per-holiday PDFs from
   https://www.cmegroup.com/tools-information/holiday-calendar.html (Equity Index section);
   best-effort line parse only.

The downloads are not committed (CME's terms do not allow redistribution): this folder
and the adapter's copies under `raw/cme/` are gitignored. The parsed rows are committed in
`output/trading_holidays_CME.csv`. The scheduled GitHub Action has no input files, so it
publishes 0 CME rows unless the files are provided to the runner. The parser test uses a
small synthetic workbook in the same layout (`tests/fixtures/cme_thanksgiving_2026.xlsx`).

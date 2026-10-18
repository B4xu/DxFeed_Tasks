# Trading-holiday calendar scraper (NYSE, NASDAQ, CME, OPRA)

Scrapes the official holiday / early-close schedules, normalises them into one schema,
validates them, writes CSVs and uploads them to Google Drive as CSV files and as a Google
Sheet. Runs weekly from GitHub Actions.

```
scraper/
  adapters/base.py      polite fetch (retries, backoff, raw snapshots), shared parsing helpers
  adapters/nyse.py      nyse.com table + early-close footnotes (3 years)
  adapters/nasdaq.py    nasdaqtrader.com table; Playwright fallback for nasdaq.com
  adapters/opra.py      opraplan.com yearly PDF notices (pdfplumber)
  adapters/cme.py       operator-downloaded PDFs/CSV (site blocks automation, see below)
  normalize.py          canonical names, dedup, local -> UTC with zoneinfo (DST-safe)
  validate.py           automated checks + run-to-run diff
  upload_drive.py       Drive API v3 via service account; DRY_RUN mode
  run.py                orchestrator / CLI
tests/                  offline parser tests on saved snapshots (tests/fixtures)
raw/<exchange>/<ts>/    raw HTML/PDF of every run
output/                 combined + per-exchange CSV, validation_report.md, run_meta.json
.github/workflows/holidays.yml
```

## Setup

```bash
conda activate dxfeed            # or any Python 3.12 env
pip install -r requirements.txt
python -m playwright install chromium    # only needed for the nasdaq.com fallback
python -m pytest tests -q
DRY_RUN=1 python -m scraper.run --upload   # scrape + validate, mock upload
```

Exit codes: 0 OK/WARN, 1 validation FAIL, 2 an adapter crashed. Logs are JSON lines on stderr.

### Google Drive upload

Credentials never live in the repo. Create a service account with the Drive API enabled,
share the target folder with its e-mail (Editor), then set:

| variable | meaning |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON key content (GitHub secret), **or** |
| `GOOGLE_APPLICATION_CREDENTIALS` | path to the key file |
| `GDRIVE_FOLDER_ID` | Drive folder ID |
| `GDRIVE_SHARE_WITH` | optional, comma-separated e-mails to grant reader access |
| `DRY_RUN=1` | skip the API and write `output/upload_manifest.json` instead |

Uploads are idempotent: files are looked up by name in the folder and updated by file ID.
`trading_holidays_combined.csv` and `trading_holidays_<EXCHANGE>.csv` are uploaded as CSV;
`trading_holidays` is uploaded as an .xlsx with the Google Sheets MIME type so Drive converts
it into a Sheet with tabs `combined`, one per exchange, and `validation`.

**Status in this environment:** no Google account was available, so the upload was executed
in `DRY_RUN` mode only (see `output/upload_manifest.json`). Everything up to the API call is
exercised; the API call itself is unverified.

## Output schema

`exchange, date (ISO 8601), holiday_name, status (closed|early_close), close_time_local (HH:MM),
timezone (IANA), close_time_utc, session_or_product_scope, source_url, scraped_at_utc,
source_year, canonical_name`

`canonical_name` is derived for cross-exchange comparison; `holiday_name` keeps the source text
(footnote markers and whitespace removed). Local → UTC conversion uses `zoneinfo`, so 13:00
America/New_York becomes 17:00Z in July and 18:00Z in December.

## Validation

`output/validation_report.md` lists each check as PASS/WARN/FAIL: weekday-only dates, no
duplicates, plausible closure count per exchange-year (8–11 for US equities/options), NYSE vs
NASDAQ equality, OPRA vs equities (differences are listed, never auto-corrected), Good Friday, a minimum of 1 early close per NYSE/NASDAQ year (WARN if 0)
= Easter − 2 (computed), early closes carry a time, and a diff against the previous run
(FAIL if the row count moves by more than 30 %). A parser returning zero rows is FAIL unless
the adapter explicitly reported `MANUAL_INPUT_REQUIRED` (CME) or `SOURCE_UNAVAILABLE`
(all sources down), which are WARN so the other exchanges still ship.

## Scope decisions and known limitations

- **NASDAQ source.** nasdaq.com rejects non-browser clients (`requests` read-timeout, curl
  HTTP/2 stream reset) although it serves browsers. The adapter uses the official
  operations site **nasdaqtrader.com** (`trader.aspx?id=Calendar`) first, which returned the
  same 2026 table over plain HTTPS. If that fails (it once served an Incapsula challenge),
  nasdaq.com is loaded once in headless Chromium via Playwright — no stealth plugins, no
  header spoofing, no proxies. Network policy for this adapter: connect 10 s / read 10 s,
  max 2 retries with exponential backoff and jitter, no retry on connection resets.
  The Playwright fallback was not exercised in this environment (nasdaqtrader.com
  succeeded, and Playwright/Chromium were not installed), so it is **unverified**.
- **CME is manual input.** cmegroup.com returns 403 to automated clients and its Data Terms
  of Use prohibit scraping, so the adapter reads files you download into `input/cme/`
  (see the README there). Scope: CME Globex US Equity Index futures & options; other product
  groups have different schedules.
- **OPRA publishes one PDF per year** and the 2026 PDF did not exist on 2026-10-16, so the
  OPRA-vs-equities check is reported as skipped (WARN) rather than passed.
- **Only the current year** is available from the NASDAQ sources; NYSE gives three years.
- Early-close rows for options (13:15 ET for 16:15 products) are not emitted separately;
  the scope column carries that note.

## Adding an exchange

1. Create `scraper/adapters/<name>.py` with a class deriving from `BaseAdapter`; set
   `exchange`, `timezone` (IANA), `source_url`, `scope`; implement `scrape()` (use
   `self.fetch`, which snapshots raw bodies) and `parse(body)` returning `HolidayRow`s via
   `self.row(...)`.
2. Register it in `scraper/adapters/__init__.py` and add plausible closure bounds in
   `validate.PLAUSIBLE_CLOSURES`.
3. Save a raw snapshot in `tests/fixtures/` and add a parser test.

## Automation

GitHub Actions only runs workflows that live at the repository root. For this DxFeed
folder that file is `/.github/workflows/trading-holidays.yml`.

Weekly cron (Monday 06:17 UTC) and manual dispatch. The job installs dependencies and
Chromium, runs the offline tests, then scrapes NYSE, NASDAQ, OPRA, and CME. CME still
only reads `input/cme/`; the workflow does not scrape cmegroup.com. Infrastructure
errors are retried three times. A validation FAIL is not retried. Raw snapshots and
CSVs are stored as artifacts for 90 days. On success the fetched CSVs and the
validation report are committed back to the branch. A Slack webhook
(`SLACK_WEBHOOK_URL`) posts the failing checks.

Secrets, all optional until you want a real Drive upload:

| secret or variable | meaning |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | service-account key JSON |
| `GDRIVE_FOLDER_ID` | Drive folder ID; empty forces `DRY_RUN` |
| `GDRIVE_SHARE_WITH` | repository variable, reader e-mails |
| `SLACK_WEBHOOK_URL` | failure alert |

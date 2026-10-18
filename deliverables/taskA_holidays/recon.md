# Task A — reconnaissance (2026-10-16, 11:04–11:29 UTC)

All probes were single `curl`/`requests` GETs with a normal desktop browser User-Agent. Raw
responses are in `raw/_recon_2026-10-16/`; the first pipeline run's snapshots are in
`raw/<exchange>/20261016T112909Z/`.

## Summary

| Exchange | Source used | Type | Years | Access | robots.txt / terms |
|---|---|---|---|---|---|
| NYSE | https://www.nyse.com/markets/hours-calendars (301 → /trade/hours-calendars) | static HTML, 1 table + footnotes | 2026, 2027, 2028 | 200, 109 KB | robots.txt only disallows /cgi-bin/ and /partial/ |
| NASDAQ | https://www.nasdaqtrader.com/trader.aspx?id=Calendar | static HTML, 1 table | 2026 only | 200, 55 KB (one earlier probe got an Incapsula JS stub, 212 B) | robots.txt itself is served through the Incapsula challenge; no crawl-delay visible |
| NASDAQ (fallback) | https://www.nasdaq.com/market-activity/stock-market-holiday-schedule | static HTML behind Akamai; `requests`/curl get ReadTimeout or HTTP/2 INTERNAL_ERROR, a real browser renders it | 2026 only | rejected for non-browser clients | robots.txt: `Crawl-delay: 30` for `*` |
| CME | https://www.cmegroup.com/tools-information/holiday-calendar.html | per-holiday PDFs/XLS behind bot protection | n/a | **403** on every URL incl. /robots.txt: "This IP address is blocked due to suspected web scraping ... Use of scripts ... is strictly prohibited by CME Group's website Data Terms of Use" | Terms prohibit automated access → not scraped |
| OPRA | https://www.opraplan.com/ → cdn.opraplan.com/documents/notices/<year>_HOLIDAY_SCHEDULE.pdf | PDF, one page | 2015–2021 and 2025 published; **no 2026 PDF yet** (probed 5 plausible names, all 403 = not found on that CDN) | 200 | no robots restrictions seen; Cloudflare CDN |
| OCC (considered for OPRA) | https://www.theocc.com/ | bot-protected | — | 403 | not used |

## Details and decisions

**NYSE.** The table has one row per holiday and one column per year. Early closes are not
rows; they are footnotes keyed by `*` markers ("Each market will close early at 1:00 p.m.
(1:15 p.m. for eligible options) on Friday, November 27, 2026, Friday, November 26, 2027, and
Friday, November 24, 2028"). A cell containing `—*` means the holiday is not observed that
year (New Year's Day 2028 falls on a Saturday; NYSE Rule 7.2 means it is not moved to Friday
31 Dec). The adapter therefore parses cells for closures and footnotes for early closes and
records "not observed" in the run notes.

**NASDAQ.** The authoritative operations site is Nasdaq Trader. During the first probe it
served an Incapsula challenge; a second probe ~20 minutes later with a browser UA and
`Accept`/`Accept-Language` headers returned the page. The nasdaq.com page carries the same
2026 data but refuses `requests`/curl (HTTP/2 stream reset or 30 s read timeout) while
serving browsers, so it is only used as a Playwright fallback (plain headless Chromium,
no stealth). Both pages list only the current year. Early-close rows are labelled
"Early Close* - U.S." with the time in the Status column.

**CME.** The holiday schedule differs by product group (equity index, rates, FX, energy,
metals, ags) and venue (Globex vs ClearPort), so there is no single CME calendar. Scope
chosen: **CME Globex US Equity Index futures and options** (ES, NQ, YM, RTY), the products
most relevant to a US-equities data consumer. Because cmegroup.com blocks automated clients
and its terms forbid scraping, the adapter consumes operator-downloaded PDFs or a CSV
(`input/cme/`). Rows are produced only from those files; nothing is inferred. This is the
main known limitation of the deliverable.

**OPRA.** OPRA, LLC (not OCC) publishes the options holiday schedule. Its PDF confirms that
listed options follow the US equity calendar, with early closes stated as "3 hours early"
(13:00 ET for 16:00 products; 13:15 for 16:15 products). The 2025 PDF is the latest one
published, so OPRA cannot yet be compared with the 2026 equity calendars; the validation
report flags this as a skipped comparison instead of silently passing.

## Request log

| time (UTC) | URL | result |
|---|---|---|
| 11:04:1x | nyse.com/markets/hours-calendars | 200 → /trade/hours-calendars |
| 11:04:1x | nasdaq.com/market-activity/stock-market-holiday-schedule (curl, HTTP/2) | 200 (later `requests` probes: ReadTimeout; `curl --http1.1`: stream reset) |
| 11:04:1x | nasdaqtrader.com/Trader.aspx?id=Calendar | 200, 212 B Incapsula stub |
| 11:04:1x | cmegroup.com/tools-information/holiday-calendar.html, /robots.txt, …/files/2026-thanksgiving-holiday-schedule.pdf | 403 JSON block message |
| 11:04:1x | opraplan.com/, /document-library, cdn…/2025_HOLIDAY_SCHEDULE.pdf | 200 |
| 11:05:35 | cdn.opraplan.com/…/2026_HOLIDAY_SCHEDULE.pdf (+4 name variants) | 403 (not published) |
| 11:27:19 | nasdaqtrader.com/trader.aspx?id=Calendar (browser UA) | 200, 54 662 B, table present |
| 11:29:09–13 | pipeline run: nyse.com, nasdaqtrader.com, opraplan.com, cdn.opraplan.com | all 200 |

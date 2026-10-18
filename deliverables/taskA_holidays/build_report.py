#!/usr/bin/env python3
"""Build TaskA_Holiday_Scraper_Report.docx (and its charts) from the saved live run.

    python build_report.py

Reads output/ only — no network. Charts go to charts/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import report_kit as rk  # noqa: E402
from report_kit import AMBER, BLUE, CORAL, GREEN, NAVY, SLATE, TEAL, plt  # noqa: E402

OUTDIR = HERE / "output"
CH = HERE / "charts"
OUT = HERE / "TaskA_Holiday_Scraper_Report.docx"
EX_COLORS = {"NYSE": NAVY, "NASDAQ": TEAL, "OPRA": BLUE, "CME": CORAL}


def _df():
    df = pd.read_csv(OUTDIR / "trading_holidays_combined.csv", dtype=str).fillna("")
    df["dt"] = pd.to_datetime(df["date"])
    df["year"] = df["dt"].dt.year
    return df


def chart_pipeline():
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(11.5, 3.6))
    ax.set_xlim(0, 11.8)
    ax.set_ylim(0, 3.6)
    ax.axis("off")
    stages = [("Sources\nNYSE, NASDAQ,\nOPRA, CME files", SLATE), ("Adapters\npolite fetch\n+ parse", NAVY),
              ("Normalise\nUTC times,\nnames", TEAL), ("Validate\ngrade checks\nPASS/WARN/FAIL", AMBER),
              ("Write\nCSV per\nexchange", GREEN), ("Publish\nDrive · GitHub\nartifact", BLUE)]
    w, gap = 1.72, 0.22
    for i, (t, c) in enumerate(stages):
        x = 0.15 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 1.0), w, 1.6, boxstyle="round,pad=0.02,rounding_size=0.1", fc=c, ec="none"))
        ax.text(x + w / 2, 1.8, t, ha="center", va="center", color="white", fontsize=8.8, fontweight="bold")
        if i < len(stages) - 1:
            ax.annotate("", (x + w + gap - 0.02, 1.8), (x + w + 0.02, 1.8),
                        arrowprops=dict(arrowstyle="-|>", color=SLATE, lw=2))
    ax.text(5.75, 3.25, "One run, one timestamp, six stages", ha="center", fontsize=14, fontweight="bold", color=NAVY)
    ax.text(5.75, 0.45, "raw/ keeps every fetched body · a crash in one adapter never stops the others · "
            "exit 0 PASS/WARN, 1 FAIL, 2 crash", ha="center", fontsize=9.5, color=SLATE, style="italic")
    p = CH / "pipeline.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def chart_rows(df):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    exs = ["NYSE", "NASDAQ", "OPRA", "CME"]
    closed = [int(((df.exchange == e) & (df.status == "closed")).sum()) for e in exs]
    early = [int(((df.exchange == e) & (df.status == "early_close")).sum()) for e in exs]
    ax.bar(exs, closed, color=TEAL, label="Full-day close")
    ax.bar(exs, early, bottom=closed, color=AMBER, label="Early close (13:00 local)")
    for i, (c, e) in enumerate(zip(closed, early)):
        ax.text(i, c + e + 0.6, f"{c + e}", ha="center", fontweight="bold", color=NAVY)
    ax.annotate("0 rows — scraping forbidden,\nmanual input folder empty", (3, 0.3), xytext=(2.5, 22),
                color=CORAL, fontsize=10, ha="center", arrowprops=dict(arrowstyle="->", color=CORAL))
    ax.set_ylabel("Rows in the published CSVs")
    ax.set_title("What the live run on 16 October 2026 returned")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 40)
    p = CH / "rows_by_exchange.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def chart_calendar(df):
    d = df[df.year == 2026]
    fig, ax = plt.subplots(figsize=(11, 3.4))
    exs = ["NYSE", "NASDAQ", "OPRA"]
    for i, e in enumerate(exs):
        g = d[d.exchange == e]
        for _, r in g.iterrows():
            m = "o" if r.status == "closed" else "D"
            ax.scatter(r["dt"], i, s=110, marker=m, color=EX_COLORS[e] if r.status == "closed" else AMBER,
                       edgecolor="white", zorder=3)
    ax.set_yticks(range(len(exs)), exs)
    ax.set_ylim(-0.7, len(exs) - 0.3)
    ax.invert_yaxis()
    ax.set_xlim(pd.Timestamp("2025-12-20"), pd.Timestamp("2027-01-05"))
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title("2026 closures (circles) and early closes (diamonds): NYSE and NASDAQ line up exactly")
    ax.text(pd.Timestamp("2026-06-01"), 2.45, "OPRA source is the 2025 PDF; only 1 Jan 2026 spills into this year",
            fontsize=9, color=SLATE, ha="center")
    p = CH / "calendar_2026.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def chart_checks():
    checks = json.loads((OUTDIR / "validation_checks.json").read_text())
    lv = pd.Series([c["level"] for c in checks]).value_counts()
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    labels = [k for k in ("PASS", "WARN", "FAIL") if k in lv]
    colors = {"PASS": GREEN, "WARN": AMBER, "FAIL": CORAL}
    ax.pie([lv[k] for k in labels], labels=[f"{k}\n{lv[k]}" for k in labels], colors=[colors[k] for k in labels],
           startangle=90, wedgeprops=dict(width=0.38, edgecolor="white"), textprops=dict(fontsize=11, fontweight="bold"))
    ax.text(0, 0, f"{len(checks)}\nchecks", ha="center", va="center", fontsize=14, fontweight="bold", color=NAVY)
    ax.set_title("Validation outcome, live run")
    p = CH / "validation_checks.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def early_close_counts(df):
    rows = []
    for (e, y), g in df[df.exchange.isin(["NYSE", "NASDAQ"])].groupby(["exchange", "year"]):
        n_closed = int((g.status == "closed").sum())
        if n_closed <= 2:
            continue
        n_ec = int((g.status == "early_close").sum())
        rows.append([f"{e}.{y}.early_closes", "PASS" if n_ec >= 1 else "WARN", f"{n_ec} early close(s); minimum 1"])
    return rows


def build() -> Path:
    CH.mkdir(exist_ok=True)
    rk.mpl_style()
    df = _df()
    meta = json.loads((OUTDIR / "run_meta.json").read_text())
    checks = json.loads((OUTDIR / "validation_checks.json").read_text())
    pipe, rows_png, cal, chk = chart_pipeline(), chart_rows(df), chart_calendar(df), chart_checks()
    counts = meta["counts"]

    rk.reset_figures()
    doc = rk.new_document()
    rk.cover(doc, "Trading-holiday scraper",
             "How it was built, every logical step it takes, what the live run produced and what it refuses to do",
             "Task A · L2 Support Engineer assessment",
             [("Live run", f"{meta['run_ts'][:19].replace('T', ' ')} UTC · overall validation {meta['level']}"),
              ("Rows", f"{meta['rows']} — NYSE {counts['NYSE']}, NASDAQ {counts['NASDAQ']}, OPRA {counts['OPRA']}, CME {counts['CME']}"),
              ("Code", "deliverables/taskA_holidays/scraper/ (Python 3.12), 11 offline tests"),
              ("Automation", ".github/workflows/trading-holidays.yml — weekly and on demand"),
              ("Published to", "Google Drive (four CSVs, uploaded by hand on 18 Oct) and the GitHub repository")])

    # ---------------------------------------------------------------- 1
    doc.add_heading("1. Summary", level=1)
    rk.para(doc,
            "The task was to collect trading holidays and early closes for several US exchanges, normalise them into "
            "one schema with UTC times, validate them, and publish them to Google Drive automatically. I treated it "
            "as a small production job rather than a one-off script: every source was inspected before a parser was "
            "written, every response body is kept on disk, every adapter fails independently, and the validation "
            "step reports problems instead of quietly fixing them.")
    rk.kpi_strip(doc, [(str(meta["rows"]), "rows published", NAVY), (str(counts["NYSE"]), "NYSE, 2026–2028", TEAL),
                       ("0", "NYSE vs NASDAQ 2026 differences", GREEN), (meta["level"], "overall validation", AMBER),
                       ("0", "CME rows (by design)", CORAL)])
    rk.figure(doc, rows_png, "Rows per exchange in the live run. CME is empty on purpose — see section 5.4.")
    rk.para(doc,
            "The result is WARN rather than PASS, and that is the honest outcome. The equity calendars pass every "
            "check and agree with each other date for date. The warnings are the three things I could not "
            "legitimately fetch: CME (its terms forbid scraping), and OPRA having only a 2025 schedule online, so it "
            "shares no year with NYSE or NASDAQ for a cross-check.")

    # ---------------------------------------------------------------- 2
    doc.add_heading("2. The files on Google Drive", level=1)
    rk.para(doc,
            "These four CSVs are the deliverable. The uploader finds each file by name and overwrites it, so a weekly "
            "run never creates duplicates — which is why the names must not change.")
    sizes = {p.name: p.stat().st_size for p in OUTDIR.glob("trading_holidays_*.csv")}
    rk.table(doc, ["File", "Contents", "Rows", "Size"], [
        ["trading_holidays_combined.csv", "Every exchange in one table", str(meta["rows"]), f"{sizes.get('trading_holidays_combined.csv', 0):,} B"],
        ["trading_holidays_NYSE.csv", "NYSE 2026–2028", str(counts["NYSE"]), f"{sizes.get('trading_holidays_NYSE.csv', 0):,} B"],
        ["trading_holidays_NASDAQ.csv", "NASDAQ 2026 (only year published)", str(counts["NASDAQ"]), f"{sizes.get('trading_holidays_NASDAQ.csv', 0):,} B"],
        ["trading_holidays_OPRA.csv", "OPRA, from the 2025 schedule PDF", str(counts["OPRA"]), f"{sizes.get('trading_holidays_OPRA.csv', 0):,} B"],
    ], widths_cm=[5.6, 6.2, 1.6, 2.6])
    rk.para(doc,
            "Not uploaded: _previous_combined.csv (the baseline for the run-to-run diff), run_meta.json and "
            "upload_manifest.json (internal bookkeeping), and raw/ (evidence, not the calendar). When the Drive "
            "secrets are configured the job also builds one Google Sheet, trading_holidays, with a tab per exchange "
            "and a validation tab. The live run was a dry run; the four files above were uploaded by hand on "
            "18 October, so the Drive API path itself is still unverified.")
    rk.table(doc, ["Column", "Meaning"], [
        ["exchange", "NYSE, NASDAQ, OPRA or CME"],
        ["date", "Session date, ISO format"],
        ["holiday_name / canonical_name", "Name as published / normalised name used for cross-exchange comparison"],
        ["status", "closed or early_close"],
        ["close_time_local, timezone, close_time_utc", "Early-close time in the exchange's zone and converted to UTC with zoneinfo (DST-correct)"],
        ["session_or_product_scope", "Which session or product the row applies to"],
        ["source_url, scraped_at_utc, source_year", "Provenance: where, when, and which year's publication"],
    ], widths_cm=[6.0, 10.6])

    # ---------------------------------------------------------------- 3
    rk.page_break(doc)
    doc.add_heading("3. How the scraper works", level=1)
    rk.figure(doc, pipe, "The six stages of a run.")
    rk.para(doc,
            "There is one entry point, python -m scraper.run. It stamps a single UTC timestamp for the whole run (so a "
            "slow adapter cannot make one file look like two runs), calls the adapters in order, normalises the rows, "
            "validates them, writes the files and, if asked, uploads. The steps below follow that order.")

    doc.add_heading("Step 1 — Reconnaissance before any parser", level=2)
    rk.para(doc,
            "Each candidate source was opened once and saved under raw/_recon_2026-10-16/ before I trusted it. Two of "
            "the five obvious URLs turned out to be the wrong choice, which is exactly why this step exists.")
    rk.table(doc, ["Source", "What I found", "Decision"], [
        ["nyse.com hours-calendars", "Static HTML table for 2026–2028; early closes only in footnotes", "Scrape the HTML"],
        ["nasdaq.com holiday page", "Non-browser clients time out or get an HTTP/2 reset", "Fallback only (Playwright)"],
        ["nasdaqtrader.com Calendar", "Official operations page, same 2026 table over plain HTTPS", "Primary NASDAQ source"],
        ["opraplan.com", "Yearly holiday PDF linked from the homepage (theocc.com is the clearing house and returns 403)", "Follow the PDF links"],
        ["cmegroup.com", "HTTP 403 even for robots.txt; Data Terms of Use prohibit scripts", "Do not scrape; read operator files"],
    ], widths_cm=[3.8, 8.2, 4.6])

    doc.add_heading("Step 2 — Fetch politely, keep everything", level=2)
    rk.para(doc,
            "All adapters share one fetch method. It sends normal browser headers (to identify the client, not to "
            "evade anything), saves every 200 response under raw/<exchange>/<run>/, and treats status codes "
            "differently on purpose:")
    rk.bullets(doc, [
        ("401, 403, 404:", "saved with an .httpNNN suffix and raised immediately — never retried. A site that has said no is not asked again."),
        ("429 and 5xx:", "wait for Retry-After if given, otherwise 2^attempt plus jitter, then retry."),
        ("Network errors:", "retried the same way, except for NASDAQ, where a connection reset means 'this client is refused'; it gets two quick tries and moves to the next source."),
    ])

    doc.add_heading("Step 3 — Parse each exchange", level=2)
    doc.add_heading("NYSE", level=3)
    rk.para(doc,
            "The page has one table: holiday names down the side and one column per year. A cell with a date becomes a "
            "closed row for that year; a cell with a dash means 'not observed' and produces a note, not an invented "
            "date — New Year's Day 2028 falls on a Saturday and NYSE publishes a dash, so there is no row. Early closes "
            "are not in the table at all; they live in the footnotes ('…will close early at 1:00 p.m. on…'). The "
            "adapter keeps the footnote text, finds the time and the weekday dates in it, and turns each into an "
            f"early_close row. Live result: {int(((df.exchange=='NYSE')&(df.status=='closed')).sum())} closes and "
            f"{int(((df.exchange=='NYSE')&(df.status=='early_close')).sum())} early closes across 2026–2028.")
    doc.add_heading("NASDAQ", level=3)
    rk.para(doc,
            "nasdaqtrader.com is tried first, with short timeouts. Its table is 'year | Holiday | Status'; a status "
            "containing a time is an early close at that local time. If it fails, headless Chromium opens the public "
            "nasdaq.com page and the rendered HTML is parsed instead — no stealth plugins, no proxies. If both fail, "
            "NASDAQ ships zero rows with a SOURCE_UNAVAILABLE note and the other exchanges still publish. Live result: "
            "nasdaqtrader.com answered with 12 rows; the Playwright fallback is tested on a saved page but was not "
            "needed live.")
    doc.add_heading("OPRA", level=3)
    rk.para(doc,
            "OPRA publishes one PDF per year, linked from its homepage. The adapter collects links whose text says "
            "'holiday schedule' with a year from last year onwards, downloads them a second apart, and reads them "
            "with pdfplumber: 'HOLIDAY NAME  Month D' lines are closes, and the asterisked footnote lists the 13:00 ET "
            "early closes. On 16 October only the 2025 PDF was linked (the 2026 URL returned 403), so OPRA ships 14 "
            "rows from 2025, including 1 January 2026 printed on the 2025 notice.")
    doc.add_heading("CME — the step that deliberately does not fetch", level=3)
    rk.para(doc,
            "There is no single CME holiday calendar: equity index, rates, energy and agriculture differ, and Globex "
            "differs from ClearPort. The adapter is scoped to Globex US equity index products (ES, NQ, YM, RTY) and "
            "reads only files an operator has downloaded into input/cme/ — a CSV in a documented format or the "
            "per-holiday PDFs. The folder was empty, so CME returned zero rows with a MANUAL_INPUT_REQUIRED note. "
            "Scraping a site whose terms forbid it is not a trade-off I would make for a client-facing job.")

    doc.add_heading("Step 4 — Normalise", level=2)
    rk.bullets(doc, [
        "Clean names (collapse whitespace, strip footnote marks) and map them to canonical names, so 'JUNTEENTH' in the OPRA PDF still matches 'Juneteenth' elsewhere.",
        "Convert early-close times to UTC using the exchange's IANA time zone: 13:00 New York on 24 December 2026 becomes 18:00Z (EST), on 3 July 2028 it becomes 17:00Z (EDT).",
        "Sort and drop duplicate (exchange, date, status) keys — none on this run.",
        "Trust the published date. An observed-date helper exists and is tested, but it is never used to invent a date the source did not print.",
    ])

    doc.add_heading("Step 5 — Validate, without auto-correcting", level=2)
    rk.para(doc,
            "Validation walks the table once and grades every check PASS, WARN or FAIL. The overall result is the worst "
            "grade. Differences between exchanges are reported, never edited away.")
    rk.figure(doc, chk, "Outcome of the live run's checks.", width_cm=9.0)
    rk.figure(doc, cal, "NYSE and NASDAQ 2026 closures and early closes; the cross-check found 0 differing dates.")
    vrows = [[c["name"], c["level"], c["detail"]] for c in checks]
    rk.table(doc, ["Check", "Result", "Detail"], vrows, widths_cm=[4.4, 1.8, 10.4], status_col=1, font_size=8.5)
    rk.para(doc,
            "After an external review I added one more check: every full NYSE and NASDAQ year must contain at least one "
            "early close. Footnote parsing is the fragile part of the NYSE adapter, and a layout change that silently "
            "yields zero early closes would otherwise pass. Applied to the saved run it gives:",
            bold_lead="New check.")
    rk.table(doc, ["Check", "Result", "Detail"], early_close_counts(df), widths_cm=[4.4, 1.8, 10.4], status_col=1, font_size=9)

    doc.add_heading("Step 6 — Write the files and exit with a meaningful code", level=2)
    rk.para(doc,
            "The combined CSV and one CSV per exchange that returned rows are written (CME has no file because it has "
            "no rows), plus validation_report.md, validation_checks.json and run_meta.json. Before overwriting, the "
            "previous combined file is copied aside so the next run can diff against it; a change of more than 30 % "
            "of rows is a FAIL. Exit code 0 means PASS or WARN, 1 means validation FAIL, 2 means an adapter crashed — "
            "and the automation treats those differently.")

    # ---------------------------------------------------------------- 4
    rk.page_break(doc)
    doc.add_heading("4. Automation on GitHub", level=1)
    rk.para(doc,
            "The workflow lives at .github/workflows/trading-holidays.yml in the repository root, the only place GitHub "
            "executes workflows from.")
    rk.numbered(doc, [
        ("Triggers.", "Every Monday at 06:17 UTC, plus a manual run with an exchange list and an upload switch."),
        ("Setup.", "Python 3.12, requirements.txt and Playwright's Chromium for the NASDAQ fallback."),
        ("Tests first.", "python -m pytest tests -q — 11 tests on saved fixtures, no network."),
        ("Run with retries that make sense.", "Up to three attempts with backoff for a crash (exit 2); a validation FAIL (exit 1) stops immediately because retrying will not fix a bad calendar."),
        ("Report.", "The validation report goes into the run summary; output/ and raw/ are kept as a 90-day artifact."),
        ("Publish.", "With the Drive secrets set the files are uploaded; without them the job runs in DRY_RUN. The refreshed CSVs are committed back to the repository, skipping missing files and empty commits."),
        ("Alert.", "On failure, a Slack message with the run link and the FAIL/WARN lines, if SLACK_WEBHOOK_URL is set."),
    ])
    rk.table(doc, ["Secret", "Purpose", "Required"], [
        ["GOOGLE_SERVICE_ACCOUNT_JSON", "Service-account key content for the Drive API", "For upload"],
        ["GDRIVE_FOLDER_ID", "Target folder; empty means DRY_RUN", "For upload"],
        ["SLACK_WEBHOOK_URL", "Failure alerts", "Optional"],
        ["GDRIVE_SHARE_WITH (variable)", "Comma-separated readers to share with", "Optional"],
    ], widths_cm=[5.6, 7.6, 3.4])
    rk.callout(doc, "What 'fetch everything' can and cannot mean",
               "The job fetches NYSE, NASDAQ and every OPRA PDF linked from opraplan.com. It does not fetch CME and "
               "it does not invent an OPRA 2026 calendar; CME appears automatically once an operator places its files "
               "in input/cme/.", NAVY)

    # ---------------------------------------------------------------- 5
    doc.add_heading("5. What was not done, and why", level=1)
    rk.table(doc, ["Item", "Status", "Why"], [
        ["Drive upload through the API", "Partial", "No service account in this environment; files uploaded by hand, API path unverified"],
        ["CME rows", "Not done", "cmegroup.com returns 403 and its terms forbid scraping; manual input required"],
        ["OPRA 2026", "Blocked", "Not published yet; the 2026 PDF URL returned 403"],
        ["nasdaq.com via Playwright, live", "Partial", "Tested on a saved page; not needed live"],
        ["Cross-check with a third-party holiday library", "Not done", "Considered; the NYSE–NASDAQ cross-check already covers 2026"],
    ], widths_cm=[5.2, 2.4, 9.0], status_col=1)

    doc.add_heading("6. Adding another exchange", level=1)
    rk.numbered(doc, [
        "Create scraper/adapters/<name>.py with the exchange, time zone, source URL and scope, implementing scrape() and parse().",
        "Use self.fetch so raw bodies are kept, and self.row(...) so the schema stays aligned.",
        "Register it in scraper/adapters/__init__.py and give it a plausible closure band in validate.PLAUSIBLE_CLOSURES.",
        "Save a fixture under tests/fixtures/ and add an offline parser test.",
        "Add the name to the workflow's default exchange list.",
    ])

    rk.footer(doc, "Task A — trading-holiday scraper · deliverables/taskA_holidays/")
    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())

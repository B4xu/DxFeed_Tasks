#!/usr/bin/env python3
"""Color chart deck for the live Task C talk.

Offline. Reads evidence plots and writes a few summary charts so the
done / not-done story is visible without opening CSVs.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches as PInches, Pt as PPt

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "taskC_assessment" / "evidence"
PLOTS = EVID / "plots"
RADAR = EVID / "radar"
OUT = Path(__file__).resolve().parent
CHARTS = OUT / "charts"
RCH = ROOT / "taskC_assessment" / "charts"

NAVY = PptRGB(0x12, 0x32, 0x4D)
TEAL = PptRGB(0x0E, 0x7C, 0x86)
CORAL = PptRGB(0xE0, 0x5D, 0x4C)
AMBER = PptRGB(0xE0, 0x9F, 0x3E)
GREEN = PptRGB(0x1F, 0x8A, 0x70)
SLATE = PptRGB(0x24, 0x30, 0x38)
WHITE = PptRGB(0xFF, 0xFF, 0xFF)
CREAM = PptRGB(0xFF, 0xF8, 0xF1)
INK = PptRGB(0x1C, 0x28, 0x33)
MUTED = PptRGB(0x5C, 0x6B, 0x73)

# matplotlib hex twins
C_TEAL = "#0E7C86"
C_CORAL = "#E05D4C"
C_AMBER = "#E09F3E"
C_GREEN = "#1F8A70"
C_NAVY = "#12324D"
C_BLUE = "#3D7EA6"


def make_summary_charts() -> dict[str, Path]:
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.titlesize": 15,
            "axes.titleweight": "semibold",
            "figure.facecolor": "white",
            "axes.facecolor": "#F4FBFC",
            "axes.edgecolor": "#12324D",
            "axes.labelcolor": "#12324D",
            "xtick.color": "#243038",
            "ytick.color": "#243038",
            "axes.grid": True,
            "grid.color": "#D5E3E6",
            "grid.linewidth": 0.8,
        }
    )
    paths = {
        "holidays": _holiday_chart(),
        "volume": _volume_chart(),
        "load": _load_chart(),
    }
    return paths


def _holiday_chart() -> Path:
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    labels = ["NYSE", "NASDAQ", "OPRA", "CME"]
    closed = [29, 10, 11, 0]
    early = [5, 2, 3, 0]
    x = range(len(labels))
    b1 = ax.bar(x, closed, 0.62, label="Full close", color=C_TEAL)
    b2 = ax.bar(x, early, 0.62, bottom=closed, label="Early close", color=C_AMBER)
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Rows in the 2026-10-16 scrape")
    ax.set_title("Task A — rows actually fetched")
    ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(0, 42)
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            if h:
                ax.text(
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_y() + h / 2,
                    str(int(h)),
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=12,
                    fontweight="bold",
                )
    ax.annotate(
        "CME: 0 rows\nnot fetched\n(terms forbid scrape)",
        xy=(3, 0.4),
        xytext=(2.15, 28),
        fontsize=11,
        color=C_CORAL,
        arrowprops=dict(arrowstyle="->", color=C_CORAL),
        ha="center",
    )
    fig.tight_layout()
    path = CHARTS / "holiday_rows.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _volume_chart() -> Path:
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    labels = ["AAPL", "TSLA"]
    match = [77, 88]
    eth = [130, 118]
    rth = [1, 2]
    x = range(len(labels))
    ax.bar(x, match, 0.55, label="1h volume matches Σ5m", color=C_GREEN)
    ax.bar(x, eth, 0.55, bottom=match, label="Mismatch, extended hours", color=C_CORAL)
    ax.bar(
        x,
        rth,
        0.55,
        bottom=[m + e for m, e in zip(match, eth)],
        label="Mismatch, regular hours",
        color=C_AMBER,
    )
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Hourly candles (208 each)")
    ax.set_title("Where hourly volume disagrees with the 5-minute sum")
    ax.set_ylim(0, 255)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    ax.text(0, 36, "77 match", ha="center", color="white", fontweight="bold")
    ax.text(0, 77 + 55, "130 ETH", ha="center", color="white", fontweight="bold")
    ax.text(1, 40, "88 match", ha="center", color="white", fontweight="bold")
    ax.text(1, 88 + 48, "118 ETH", ha="center", color="white", fontweight="bold")
    for i, n in enumerate(rth):
        top = match[i] + eth[i] + rth[i]
        ax.annotate(
            f"{n} regular-hours " + ("bar" if n == 1 else "bars"),
            xy=(i, top),
            xytext=(i, 230),
            ha="center",
            fontsize=11,
            color="#8A5A00",
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_AMBER, lw=1.4),
        )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    path = CHARTS / "volume_split.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _load_chart() -> Path:
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    c_pre = [1, 5, 10, 25]
    p50_pre = [0.756, 2.684, 6.199, 8.265]
    c_mh = [1, 5, 10, 25, 50]
    p50_mh = [0.453, 1.141, 2.541, 5.279, 8.283]
    ax.plot(c_pre, p50_pre, "o-", color=C_AMBER, lw=2.4, ms=8, label="Pre-market p50 (stopped at c=25)")
    ax.plot(c_mh, p50_mh, "o-", color=C_TEAL, lw=2.4, ms=8, label="Market-hours p50 (reached c=50)")
    ax.axhline(8, color=C_CORAL, ls="--", lw=1.2, label="Auto-stop line (p50 = 8 seconds)")
    ax.set_xlabel("Configured concurrency")
    ax.set_ylabel("p50 latency (seconds)")
    ax.set_title("Latency is in seconds, not milliseconds")
    ax.set_xticks([1, 5, 10, 25, 50])
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    path = CHARTS / "load_p50.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _set_run(run, size=16, bold=False, color=INK, font="Calibri"):
    run.font.size = PPt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def _fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _blank(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    _fill(bg, CREAM)
    return slide


def _title_bar(slide, title, subtitle=None):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, PInches(13.333), PInches(0.92))
    _fill(bar, NAVY)
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, PInches(0.92), PInches(13.333), PInches(0.08))
    _fill(accent, CORAL)
    box = slide.shapes.add_textbox(PInches(0.38), PInches(0.12), PInches(12.5), PInches(0.48))
    p = box.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = title
    _set_run(r, 26, True, WHITE)
    if subtitle:
        box2 = slide.shapes.add_textbox(PInches(0.38), PInches(0.52), PInches(12.5), PInches(0.34))
        p2 = box2.text_frame.paragraphs[0]
        r2 = p2.add_run()
        r2.text = subtitle
        _set_run(r2, 13, False, PptRGB(0xD6, 0xEE, 0xF0))


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _fit(slide, path: Path, left, top, max_w, max_h):
    if not path.exists():
        return False
    with Image.open(path) as im:
        aspect = im.width / im.height
    w, h = max_w, max_w / aspect
    if h > max_h:
        h = max_h
        w = h * aspect
    # center inside the box
    x = left + (max_w - w) / 2
    y = top + (max_h - h) / 2
    slide.shapes.add_picture(str(path), PInches(x), PInches(y), width=PInches(w), height=PInches(h))
    return True


def _card(slide, left, top, width, height, fill, title, lines, title_color=WHITE, body_color=WHITE, title_size=15, body_size=13):
    sh = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, PInches(left), PInches(top), PInches(width), PInches(height)
    )
    _fill(sh, fill)
    tf = sh.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = PInches(0.14)
    tf.margin_right = PInches(0.12)
    tf.margin_top = PInches(0.08)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    _set_run(r, title_size, True, title_color)
    for line in lines:
        bp = tf.add_paragraph()
        bp.space_before = PPt(3)
        br = bp.add_run()
        br.text = line
        _set_run(br, body_size, False, body_color)
    return sh


def _chart_slide(prs, title, subtitle, image: Path, explain_title, explain_lines, verdict_title, verdict_lines, verdict_fill, notes):
    s = _blank(prs)
    _title_bar(s, title, subtitle)
    frame = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(0.22), PInches(1.18), PInches(8.55), PInches(6.05))
    _fill(frame, WHITE)
    _fit(s, image, 0.32, 1.28, 8.35, 5.85)
    _card(
        s, 8.95, 1.18, 4.1, 3.15, TEAL, explain_title, explain_lines,
        title_color=WHITE, body_color=WHITE, title_size=14, body_size=13,
    )
    _card(
        s, 8.95, 4.48, 4.1, 2.75, verdict_fill, verdict_title, verdict_lines,
        title_color=WHITE, body_color=WHITE, title_size=14, body_size=13,
    )
    _notes(s, notes)
    return s


def _section(prs, number, title, subtitle, color):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    _fill(bg, NAVY)
    stripe = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, PInches(5.2), prs.slide_width, PInches(0.14))
    _fill(stripe, color)
    tb = s.shapes.add_textbox(PInches(0.9), PInches(1.6), PInches(11.5), PInches(3.4))
    p = tb.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = number
    _set_run(r, 72, True, color)
    p2 = tb.text_frame.add_paragraph()
    r2 = p2.add_run()
    r2.text = title
    _set_run(r2, 40, True, WHITE)
    p3 = tb.text_frame.add_paragraph()
    r3 = p3.add_run()
    r3.text = subtitle
    _set_run(r3, 18, False, PptRGB(0xD6, 0xEE, 0xF0))
    return s


def _kpi_tile(slide, left, top, width, height, fill, value, label):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(left), PInches(top), PInches(width), PInches(height))
    _fill(sh, fill)
    tf = sh.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = value
    _set_run(r, 40, True, WHITE)
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = label
    _set_run(r2, 14, False, WHITE)
    return sh


def build_visual_pptx(charts: dict[str, Path]):
    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    parts = []

    def remember(title, notes):
        parts.append((title, notes))

    # ----- title -----
    s = _blank(prs)
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, PInches(0.28), prs.slide_height)
    _fill(band, CORAL)
    band2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, PInches(0.28), 0, PInches(0.12), prs.slide_height)
    _fill(band2, AMBER)
    tb = s.shapes.add_textbox(PInches(0.8), PInches(1.55), PInches(11.8), PInches(2.2))
    p = tb.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = "dxFeed demo services"
    _set_run(r, 42, True, NAVY)
    p2 = tb.text_frame.add_paragraph()
    r2 = p2.add_run()
    r2.text = "What was measured, what the charts show, and what is still open"
    _set_run(r2, 20, False, TEAL)
    chips = [
        (0.8, GREEN, "Done  ·  pass 1, load, SSE, Radar, Task A scrape"),
        (5.15, AMBER, "Hypothesis  ·  volume cause, FX ticks, retention why"),
        (9.35, CORAL, "Not done  ·  pass 2, Drive API, CME, OPRA 2026"),
    ]
    for x, color, label in chips:
        _card(s, x, 4.5, 3.7, 1.15, color, "", [label], body_color=WHITE, body_size=14)
    note = (
        "OPENING (about 45 seconds). This deck is the evidence from Friday 16 October 2026. "
        "Green means I measured it. Amber means I have a pattern and a hypothesis, not a root cause. "
        "Coral means the work was not done, and I will say why. "
        "Pass 2 is still waiting for Monday 19 October after 15:30 UTC."
    )
    _notes(s, note)
    remember("Title", note)

    # ----- at a glance -----
    s = _blank(prs)
    _title_bar(s, "At a glance", "Friday 16 October 2026 · one client, shared demo · every number reproducible offline")
    tiles = [
        (NAVY, "58,315", "candles validated"),
        (TEAL, "~900 s", "feed delay, every symbol"),
        (CORAL, "~8,000", "silent history cap per series"),
        (AMBER, "130 + 1", "AAPL hourly volume mismatches (ETH + RTH)"),
        (CORAL, "50", "EUR/USD candles outside session"),
        (AMBER, "~3 req/s", "saturation in market hours"),
        (GREEN, "0", "HTTP errors in 648 load requests"),
        (TEAL, "60", "holiday rows from the Task A scraper"),
    ]
    for i, (col, val, lab) in enumerate(tiles):
        x = 0.35 + (i % 4) * 3.2
        y = 1.35 + (i // 4) * 2.95
        _kpi_tile(s, x, y, 3.0, 2.7, col, val, lab)
    note = ("One slide of numbers before any detail. Read them left to right; each one has its own slide later. "
            "Latencies everywhere in this deck are seconds, not milliseconds.")
    _notes(s, note)
    remember("At a glance", note)

    # ----- done / not done -----
    s = _blank(prs)
    _title_bar(s, "Done, partial, and not done", "Status as of Sunday 2026-10-18 · nothing here is inferred from a later run")
    _card(
        s, 0.28, 1.25, 4.2, 5.9, GREEN, "Done — measured",
        [
            "Task A live scrape: NYSE 34, NASDAQ 12, OPRA 14",
            "NYSE = NASDAQ for 2026 (0 date differences)",
            "Task B plan, T+30 escalation, 3 preventions",
            "Pass 1 candles, validation, plots",
            "15-minute delay on REST, SSE, Radar",
            "Silent cap of about 8000 candles",
            "Load pre-market and market hours",
            "Load: throughput flat, ~1.6 / ~3.2 req/s",
            "Re-fetch of the 1h bars: stable",
        ],
        body_size=13,
    )
    _card(
        s, 4.58, 1.25, 4.2, 5.9, AMBER, "Partial — say it that way",
        [
            "Volume split is real; the cause is not proven",
            "AAPL 130 ETH + 1 RTH; TSLA 118 ETH + 2 RTH",
            "EUR/USD: 50 outside-session 1m candles; meaning open",
            "Weekend logger collected, then died",
            "Gap Friday 14:49Z → Saturday restart",
            "NASDAQ publishes the current year only",
            "OPRA PDF is 2025, plus 1 Jan 2026",
            "Crypto was requested; the demo has none",
            "Drive: CSVs uploaded by hand; API path untested",
        ],
        body_size=13,
    )
    _card(
        s, 8.88, 1.25, 4.15, 5.9, CORAL, "Not done — and why",
        [
            "Pass 2: Monday 19 Oct after 15:30Z",
            "Logger analysis of the freeze: same window",
            "Drive API upload: not run with real credentials",
            "CME rows: site terms forbid scraping",
            "OPRA 2026 PDF: not published (HTTP 403)",
            "nasdaq.com Playwright path: not needed",
            "TimeAndSale: TIMED_OUT on demo REST",
            "Second load client / burst / batching: not run",
            "SPY/MSFT RTH check and tho=true: not run",
            "Production capacity: not claimed",
        ],
        body_size=13,
    )
    note = (
        "Spend two minutes here. Interviewers will ask what you did not verify. "
        "Answer from the coral column before they ask. Do not upgrade amber items to conclusions."
    )
    _notes(s, note)
    remember("Done, partial, and not done", note)

    _section(prs, "01", "Task A — holiday calendar", "Scraper, validation and the files on Google Drive", AMBER)
    remember("Section: Task A", "Thirty seconds. The calendar is the input to the gap analysis in Task C.")

    # ----- task A chart -----
    _chart_slide(
        prs,
        "Task A — what the scraper actually returned",
        "Live run 2026-10-16 11:31Z · overall validation WARN, not FAIL",
        charts["holidays"],
        "How to read the bars",
        [
            "Teal = full-day close.",
            "Amber = early close at 13:00 local.",
            "NYSE covers 2026–2028.",
            "NASDAQ is 2026 only.",
            "OPRA is the 2025 PDF.",
            "CME is an empty bar on purpose.",
        ],
        "Not fetched",
        [
            "CME returns 403 and its terms forbid scripts.",
            "No CME CSV exists to upload.",
            "OPRA 2026 PDF was not on the CDN.",
            "CSVs on Drive were uploaded by hand.",
        ],
        CORAL,
        "Task A in one minute. 60 data rows. NYSE matched NASDAQ on every 2026 closed and early-close date. "
        "CME is WARN because the adapter refuses to scrape cmegroup.com. That is a compliance choice, not a parser bug.",
    )
    remember(
        "Task A chart",
        "Task A in one minute. 60 data rows. NYSE matched NASDAQ on every 2026 date. CME is empty because scraping is forbidden.",
    )

    _section(prs, "02", "Data consistency", "Delay, retention, cross-timeframe volume, prices and sessions", TEAL)
    remember("Section: data consistency", "Fifteen minutes for this section. Lead with what works, then the silent defects.")

    # ----- delay -----
    _chart_slide(
        prs,
        "The feed is 15 minutes delayed",
        "Blue = quote age · orange = last 1-minute candle age · dashed line = 15 min",
        PLOTS / "logger" / "data_age_timeline.png",
        "What the chart shows",
        [
            "Each panel is one symbol.",
            "Quote age sits on the dashed 15-minute line.",
            "Same floor on REST, SSE, and Radar.",
            "A freshness SLO has to be written as 900 seconds plus slack.",
            "“Fresh” on this demo means about 15 minutes old.",
        ],
        "Verified",
        [
            "Measured, not assumed.",
            "Clock skew does not fit: every symbol, both transports, same floor.",
            "The delay is upstream of the web tier. Load did not change it.",
        ],
        GREEN,
        "Start the data section here. Every later freshness number is relative to 900 seconds. "
        "Do not design a 5-second SLO against this endpoint.",
    )
    remember("15-minute delay", "Quote age sits on 900 seconds for every symbol. Fresh means fifteen minutes old.")

    # ----- per day -----
    _chart_slide(
        prs,
        "Price integrity: good, not perfect",
        "Candles per calendar day · holidays and weekends show up as gaps, not as bad timestamps",
        PLOTS / "pass1" / "per_day_1m_counts.png",
        "What was right",
        [
            "58,315 candles.",
            "21 boundary duplicates, 0 conflicts.",
            "0 misaligned timestamps.",
            "0 out-of-order rows.",
            "0 NaN OHLC.",
            "Holiday gaps match the Task A calendar.",
            "First hourly bar 00:00 ET; DST ok.",
            "Not perfect: OHLC differs on 6 hourly-from-5m candles.",
        ],
        "Read the gaps",
        [
            "Equity 1-minute series go to zero on the weekend.",
            "ES stops and restarts on its own session.",
            "EUR/USD has 50 out-of-session candles. Next chart.",
        ],
        TEAL,
        "Say what works before the anomalies. The price path is good but not perfect (6 OHLC differences, e.g. AAPL close 333.35 vs 333.3015). The defects are silent: retention and volume attribution.",
    )
    remember("Price integrity", "Lead with what works: 58,315 candles, 0 misaligned, holidays match. Then say OHLC is not 100% clean.")

    _chart_slide(
        prs,
        "Prices: almost, not perfectly, consistent",
        "Every price-field difference between served 1h candles and the 5-minute rebuild",
        RCH / "ohlc_mismatches.png",
        "What the bars show",
        [
            "6 hourly candles differ in a price field.",
            "3 are the forming 11:00Z bar (expected).",
            "3 are complete hours: AAPL 2 Oct, TSLA 8 Oct.",
            "Largest gap 0.023% of price.",
        ],
        "Corrected claim",
        [
            "An earlier draft said OHLC always agrees.",
            "It does not. Small, real differences.",
            "5m vs 1m differs only on incomplete buckets.",
        ],
        AMBER,
        "Say the correction out loud. It is small in size but it changes the sentence 'prices are identical'.",
    )
    remember("OHLC mismatches", "Six candles, three complete, all under 0.03 percent. Earlier claim of perfect agreement withdrawn.")

    # ----- volume summary + AAPL plot is next -----
    _chart_slide(
        prs,
        "Hourly volume differs from the 5-minute sum",
        "208 hourly candles each · green matches · coral is extended hours · amber is regular hours",
        charts["volume"],
        "What was counted",
        [
            "AAPL: 131 of 208 differ.",
            "130 of those are outside 09:30–16:00 ET.",
            "1 regular-hours hour differs, the other way (~+2%).",
            "TSLA: 120 differ = 118 ETH + 2 RTH.",
            "OHLC differs on a few candles (<=0.03%).",
            "Daily 2026-10-14: hourly sum closer than 1m sum.",
        ],
        "Not concluded",
        [
            "AAPL and TSLA RTH exceptions: same day and hour.",
            "Re-fetch 11.5 minutes later was stable.",
            "So this is not a candle still printing.",
            "TimeAndSale is TIMED_OUT on demo REST.",
            "Sale-condition cause stays a hypothesis.",
            "Which series is the reference: not decided.",
        ],
        AMBER,
        "Do not say zero regular-hours mismatches. Point at the one amber slice. "
        "The pattern is extended hours. The cause is not proven.",
    )
    remember("Volume split summary", "AAPL 130 ETH plus 1 RTH. TSLA 118 ETH plus 2 RTH. Cause not proven.")

    _chart_slide(
        prs,
        "Where the volume disagrees: hour by hour",
        "AAPL · % difference Σ5m vs served 1h · rows = days, columns = New York hour",
        RCH / "aapl_volume_heatmap.png",
        "How to read it",
        [
            "Red = the served hourly bar has more volume.",
            "The boxed regular-hours block is white.",
            "One blue cell: 8 Oct 11:00 ET, +2%.",
            "Worst cells: 17:00–18:00 ET and the 00:00 ET tail.",
        ],
        "Why it matters",
        [
            "Extended-hours volume depends on the timeframe.",
            "VWAP and relative volume will disagree.",
            "Regular hours are usually, not always, clean.",
        ],
        CORAL,
        "This is the clearest picture of the finding. Point at the white box, then at the red columns on either side.",
    )
    remember("AAPL heatmap", "Red outside regular hours, white inside, one blue exception.")

    _chart_slide(
        prs,
        "AAPL — the hourly volume chart",
        "Blue = volume percent difference · orange = close, which stays on zero",
        PLOTS / "pass1" / "agg_AAPL_1h_from_5m.png",
        "How to read it",
        [
            "Each blue dot is one hour.",
            "Zero means the 1-hour bar equals the sum of its 5-minute bars.",
            "Spikes near −100% are extended hours, worst −99.1% at 17:00 ET on 7 Oct (2 Oct 18:00 ET: −98.4%).",
            "Orange sits near zero: the close agrees except a few tiny gaps.",
            "Prices nearly consistent. Volume attribution is not.",
        ],
        "The exception",
        [
            "2026-10-08 11:00 ET is inside regular hours.",
            "Rebuilt volume is about 2% higher, opposite sign.",
            "OHLC matches. 1-minute equals 5-minute.",
            "Do not hide this row in the talk.",
        ],
        AMBER,
        "Live fallback: open agg_AAPL_1h_from_5m.csv, show the 18:00 ET row and the 11:00 ET exception. "
        "The PNG is the offline fallback.",
    )
    remember("AAPL volume chart", "Blue dots below zero are extended-hours volume gaps. One regular-hours hour goes the other way.")

    _chart_slide(
        prs,
        "TSLA shows the same shape",
        "Same rebuild · 120 of 208 hours differ · 2 of them are regular hours",
        PLOTS / "pass1" / "agg_TSLA_1h_from_5m.png",
        "Why this slide exists",
        [
            "The AAPL pattern is not one symbol.",
            "TSLA: 118 extended-hours mismatches.",
            "2 regular-hours mismatches.",
            "ES and EUR/USD do not show this equity pattern.",
            "So it is a US-stock session effect, not a generic bug in the aggregator.",
        ],
        "Still open",
        [
            "tho=true was never tested; not a workaround.",
            "SPY/MSFT same-hour check: not done.",
            "Trade and TimeAndSale history came back empty or TIMED_OUT.",
            "I will not name a sale condition I could not read.",
        ],
        CORAL,
        "Second symbol so nobody can say it is an AAPL quirk. Root cause tests that need TimeAndSale were blocked by the demo.",
    )
    remember("TSLA volume chart", "Same extended-hours pattern. Two regular-hours exceptions. TimeAndSale blocked.")

    _chart_slide(
        prs,
        "Which volume series is the reference?",
        "AAPL daily totals from 1-minute vs hourly candles · one daily candle to compare against",
        RCH / "volume_reconcile.png",
        "What the data says",
        [
            "Hourly totals are never below 1-minute totals.",
            "14 Oct daily: hourly −0.13%, 1-minute −0.15%.",
            "Hourly is closer — on one data point.",
        ],
        "So the advice is",
        [
            "Do not tell clients to rebuild from 1m.",
            "'We are confirming which series is the reference.'",
            "tho=true untested; SPY/MSFT not checked.",
        ],
        AMBER,
        "This changed the client advice. Earlier wording said build ETH analytics from 1m; the data does not support that.",
    )
    remember("Volume reconciliation", "Hourly is closer to daily on the one day we have. No workaround is offered.")

    _chart_slide(
        prs,
        "EUR/USD prints outside its FX session",
        "FX session is Sun 17:00 ET → Fri 17:00 ET · equities and ES do not do this",
        RCH / "fx_outside_session.png",
        "What was counted",
        [
            "50 of 8000 1m candles outside session (39 5m).",
            "7 after Friday close, 0 Saturday, 43 Sunday pre-open.",
            "Sparse from 14:00 ET Sunday, full after 17:00 ET.",
            "Old \"214 weekend\" counted the legit Sunday reopen.",
            "These are bid candles. Volume is tick count.",
            "ES: 0 outside session.",
        ],
        "Not concluded",
        [
            "Could be indicative quotes.",
            "Could be a session heartbeat.",
            "The logger bidTime test was proposed, not finished.",
            "Dangerous if a client treats last-candle age as “market open”.",
        ],
        AMBER,
        "Visible on a chart, dangerous in session logic. I am not calling these trades.",
    )
    remember("EURUSD weekend", "50 outside-session minutes (not 214). Not proven to be trades.")

    # ----- 8000 -----
    s = _blank(prs)
    _title_bar(s, "Silent ~8,000-candle retention", "A long history request returns status OK and then stops")
    _card(s, 0.35, 1.35, 4.0, 2.4, NAVY, "8,000", ["newest 1-minute candles", "status: OK", "no truncated flag"], title_size=40, body_size=16)
    _card(
        s, 4.55, 1.35, 4.15, 2.4, TEAL, "What that hides",
        ["About 8 trading days of 1-minute bars.", "About 7 weeks of 5-minute bars.", "Older windows: OK and zero candles.", "Looks exactly like a holiday."],
        body_size=14,
    )
    _card(
        s, 8.9, 1.35, 4.05, 2.4, CORAL, "Why it matters",
        ["A backtest drops a week.", "No HTTP error.", "No dxFeed error status.", "The client cannot alert on it."],
        body_size=14,
    )
    _card(
        s, 0.35, 3.95, 6.2, 3.15, GREEN, "Done",
        [
            "A 2-week 1-minute request returned about 8,000 candles (8000/8001).",
            "A window entirely before the edge returned OK and an empty body (15 bytes).",
            "That separates “retention” from “the response was too big to build”.",
            "Raw bodies and chunks.jsonl are in evidence/.",
        ],
        body_size=15,
    )
    _card(
        s, 6.75, 3.95, 6.2, 3.15, AMBER, "Not concluded",
        [
            "This may be an intentional demo quota.",
            "The defect is the silence, either way.",
            "A truncated flag or one sentence of docs fixes the client-visible failure.",
            "I did not test whether production has the same cap.",
        ],
        body_size=15,
    )
    note = (
        "Live demo: request 14 days of AAPL 1-minute candles, or open chunks.jsonl. "
        "Count 8000. Show the empty older window. Do not claim this is a production bug."
    )
    _notes(s, note)
    remember("Silent 8000", note)

    _chart_slide(
        prs,
        "Every 1-minute series stops at the same place",
        "Candles retrieved per instrument and timeframe in pass 1 (58,315 in total)",
        RCH / "candle_totals.png",
        "What the bars show",
        [
            "All four 1m series: 8,000 or 8,001.",
            "Different instruments, sessions, asset classes.",
            "Same ceiling, so it is a server limit.",
        ],
        "What it is not",
        [
            "Not a holiday or a market closure.",
            "Not an HTTP error: every response was OK.",
            "5m and 1h stay under the cap here.",
        ],
        NAVY,
        "Point at the dark blocks: identical height for equities, FX and futures. That is the retention edge, not the market.",
    )
    remember("Candle totals", "Identical 8,000 ceiling across four very different instruments: a server limit, silent.")

    _section(prs, "03", "Behaviour under load", "Throughput, latency by request type, and what failed first", CORAL)
    remember("Section: load", "Eight minutes. Every latency is seconds.")

    # ----- load -----
    _chart_slide(
        prs,
        "Load — latency in seconds, not milliseconds",
        "Y-axis is seconds. Dashed line is the politeness stop at p50 = 8 seconds",
        charts["load"],
        "What happened",
        [
            "0 HTTP errors. No 429. No Retry-After.",
            "Throughput through completion: pre-market ~1.6 req/s, market hours ~3.2 falling to 2.8 at c=50.",
            "Market hours ~2x pre-market. Shared-demo load varies.",
            "TIMED_OUT 3.3 s at c=1, ~29 s at c=50.",
            "p50 is in seconds: about 0.5 s at c=1, about 8 s at the stop.",
        ],
        "Little’s law",
        [
            "At concurrency 5 and 10, in-flight ≈ the setting.",
            "Pool limit 52 >= max c 50, so it could never bind.",
            "Per-IP throttle vs shared capacity: unresolved.",
            "p50 uses completed requests only (censored).",
            "One client. Not a production capacity number.",
        ],
        GREEN,
        "Walk the chart left to right. Pre-market stopped at concurrency 25. Market hours reached 50 with lower latency but flat throughput. Percentiles count completed requests only. "
        "Refuse any question that asks you to quote these RPS figures as production capacity.",
    )
    remember("Load p50 chart", "Throughput flat (~1.6 pre, ~3.2 market). Pool could not bind; second client not run. No 429.")

    _chart_slide(
        prs,
        "More workers did not buy more throughput",
        "Requests per second measured through request completion",
        RCH / "throughput_vs_concurrency.png",
        "What happened",
        [
            "Pre-market plateau ≈ 1.6 req/s.",
            "Market hours ≈ 3.2 req/s, falling to 2.8 at c=50.",
            "Extra parallelism only adds queueing.",
        ],
        "Corrected claim",
        [
            "Earlier: 'rising to 4.6 req/s'.",
            "That ignored requests still in flight.",
            "Through completion the curve is flat.",
        ],
        AMBER,
        "The single most important load chart. Throughput flat, latency rising: a saturated queue.",
    )
    remember("Throughput", "Flat at about 1.6 and 3 requests per second. The 4.6 figure was a measurement artefact.")

    _chart_slide(
        prs,
        "Queueing is not uniform",
        "p50 latency in seconds by request type, market hours",
        RCH / "latency_by_request_type.png",
        "What the bars show",
        [
            "c=25: quotes 2.6 s, candles 11–12 s.",
            "c=50: latest-candle p50 26 s.",
            "Fits per-request cost or separate queues.",
        ],
        "Plus",
        [
            "TIMED_OUT: 3.3 s alone → 29 s at c=50.",
            "Percentiles count completed requests only.",
            "So the tail is understated.",
        ],
        CORAL,
        "Candle requests suffer first. A dashboard mixing quotes and candles will look half-alive.",
    )
    remember("Latency by type", "Quotes stay fast, candles queue. TIMED_OUT stretches to 29 seconds.")

    s = _blank(prs)
    _title_bar(s, "The two latency plots, side by side", "Unit: seconds, not milliseconds · Left: pre-market, stopped at c=25 · Right: market hours, reached c=50")
    _fit(s, PLOTS / "load" / "premarket_fri_latency.png", 0.25, 1.2, 6.4, 4.7)
    _fit(s, PLOTS / "load" / "market_hours_fri_latency.png", 6.7, 1.2, 6.4, 4.7)
    cap = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(0.25), PInches(6.0), PInches(12.85), PInches(1.25))
    _fill(cap, NAVY)
    tf = cap.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = (
        "Unit: seconds, not milliseconds. A reading of 8 is 8 seconds, not 8 ms. "
        "p50/p95/p99 climb with concurrency and the error rate stays zero. "
        "The service queues. It does not tell the client to slow down."
    )
    _set_run(r, 15, False, WHITE)
    note = "Point at p95, not the error rate. The error rate stayed zero while the experience died."
    _notes(s, note)
    remember("Latency plots", note)

    # ----- radar -----
    _chart_slide(
        prs,
        "Radar matches the delayed REST bar",
        "Screenshot from the pre-market pass · the market-hours compare JSON says the same thing",
        RADAR / "radar_last_candle_1m_2026-10-16T120542Z.png",
        "What matched",
        [
            "Last 1-minute open, high, low agree with REST.",
            "Checked pre-market and again in regular hours.",
            "SSE lag median 0.72 s pre-market, 0.26 s in regular hours.",
            "Quote age still ~900 s on both paths.",
        ],
        "Client footgun",
        [
            "If fromTime sits inside the delay window, SSE emits NaN candles dated 2038-01-19.",
            "eventFlags 14 then 2. A client that ignores flags stores garbage.",
            "Radar lists NVDA. REST times NVDA out. Different symbol universes, not a price bug.",
        ],
        CORAL,
        "The 2038 timestamp is the 'would your parser survive this' moment. NVDA is a universe difference, not a data defect.",
    )
    remember("Radar", "OHL matches. 2038 NaN candles are a client footgun. NVDA is a different symbol list.")

    # ----- not done detail -----
    s = _blank(prs)
    _title_bar(s, "Open items — commands and owners", "I will not present these as results")
    rows = [
        (CORAL, "Pass 2", "Monday 19 Oct after 15:30Z", "fetch_candles.py --pass pass2, then validate_candles.py"),
        (CORAL, "Logger freeze", "Same Monday window", "analyze_logger.py — mention the Friday→Saturday gap"),
        (AMBER, "Volume cause", "Blocked on this demo", "TimeAndSale/Trade returned TIMED_OUT or empty"),
        (AMBER, "Google Drive", "Needs a service account", "Code is done. Last run wrote upload_manifest.json as DRY_RUN"),
        (AMBER, "CME calendar", "Manual download", "Put PDFs or the CSV template in taskA_holidays/input/cme/"),
        (AMBER, "OPRA 2026", "When OPRA publishes", "HEAD of the 2026 PDF returned 403 on 17 Oct"),
    ]
    y = 1.22
    for color, name, when, detail in rows:
        pill = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(0.3), PInches(y), PInches(2.3), PInches(0.9))
        _fill(pill, color)
        tf = pill.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = name
        _set_run(r, 16, True, WHITE)
        box = s.shapes.add_textbox(PInches(2.8), PInches(y), PInches(10.1), PInches(0.9))
        bp = box.text_frame.paragraphs[0]
        br = bp.add_run()
        br.text = when
        _set_run(br, 16, True, NAVY)
        bp2 = box.text_frame.add_paragraph()
        br2 = bp2.add_run()
        br2.text = detail
        _set_run(br2, 14, False, SLATE)
        y += 1.0
    note = (
        "If asked 'what did you not verify', read this slide. "
        "Pass 2 and the logger analysis are the only ones that are simply waiting on the clock."
    )
    _notes(s, note)
    remember("Open items", note)

    _section(prs, "04", "Risk, incident and improvements", "What I would escalate, a drill, and three proposals", GREEN)
    remember("Section: risk and incident", "Twelve minutes for risk, incident and improvements together.")

    # ----- risk + incident condensed -----
    s = _blank(prs)
    _title_bar(s, "What I would escalate", "Silent failures first — clients cannot alert on HTTP 200")
    _card(
        s, 0.28, 1.25, 6.3, 5.9, NAVY, "Ranked risks",
        [
            "1  Silent 8,000 cap / empty OK",
            "2  Cross-timeframe volume (mostly ETH, rare RTH)",
            "3  Saturation: queueing, no 429, no Retry-After",
            "4  Staleness that looks like a closed market",
            "5  FX bid-only candles and TIMED_OUT symbols",
            "6  Out-of-session FX prints used as a session signal",
            "7  Monitors that only watch HTTP errors",
        ],
        body_size=15,
    )
    _card(
        s, 6.75, 1.25, 6.25, 5.9, TEAL, "Incident drill INC-SIM-01",
        [
            "Client: AAPL 18:00 ET hourly volume is ~98% below the 1-minute roll-up (served 845k vs 14k).",
            "First 15 minutes: reproduce on the demo, count ETH vs RTH, check the daily total.",
            "Daily 2026-10-14: hourly sum closer than 1m sum.",
            "Escalate with the CSV; ask which series is the reference.",
            "Client note: facts, next-update time. No workaround claimed (tho=true untested).",
        ],
        body_size=15,
    )
    note = "Seven minutes for risk and the incident. The external email must not assert a root cause."
    _notes(s, note)
    remember("Risks and incident", note)

    # ----- improvements -----
    s = _blank(prs)
    _title_bar(s, "Three improvements", "Technical · monitoring · documentation")
    _card(
        s, 0.28, 1.3, 4.2, 5.7, TEAL, "Technical",
        [
            "Put truncated, serverTime, delaySeconds, and lastEventTime on the response.",
            "Flag the forming candle.",
            "Return UNKNOWN_SYMBOL immediately instead of a 3.3 s TIMED_OUT.",
            "Complexity: medium.",
            "Fewer false “no data” tickets.",
        ],
        body_size=15,
    )
    _card(
        s, 4.58, 1.3, 4.2, 5.7, AMBER, "Monitoring",
        [
            "One synthetic probe per asset class.",
            "Watch p95, freshness versus 900 s, and 1-hour versus 1-minute volume.",
            "Page when p95 > 5 s at low concurrency, or freshness > 1200 s.",
            "Complexity: small to medium.",
            "Probes spend real capacity on a service that queues. Budget them.",
        ],
        body_size=15,
    )
    _card(
        s, 8.88, 1.3, 4.15, 5.7, GREEN, "Documentation",
        [
            "One demo-facts page: delay, retention, symbol list, FX bid, Radar ≠ REST.",
            "Complexity: small.",
            "This report is the draft.",
            "It removes the three-experiment tax on every new integrator.",
        ],
        body_size=15,
    )
    note = "Five minutes. Lead with the response envelope because it fixes the silent cap."
    _notes(s, note)
    remember("Improvements", note)

    # ----- questions -----
    s = _blank(prs)
    _title_bar(s, "Questions", "Offline fallbacks are in evidence/ if the demo is slow")
    _card(
        s, 0.35, 1.3, 6.2, 5.7, NAVY, "I can open live",
        [
            "8,000 cap: a long fromTime, or chunks.jsonl.",
            "Volume: validate_candles.py --pass pass1, then the AAPL CSV.",
            "Show both the −99% extended-hours row and the +2% regular-hours row.",
            "Radar screenshots are already saved.",
        ],
        body_size=16,
    )
    _card(
        s, 6.75, 1.3, 6.2, 5.7, CORAL, "I will not claim",
        [
            "A root cause, or which volume series is the reference.",
            "That weekend EUR/USD prints are trades.",
            "Production capacity from this shared demo.",
            "Pass 2, a live Drive upload, or a CME calendar.",
            "That regular hours or OHLC were a perfect match.",
        ],
        body_size=16,
    )
    note = (
        "Q&A. If they ask whether the 8000 cap is just a quota: yes, possibly, and the defect is still the missing signal. "
        "If they ask about production RPS: the monitoring design transfers, the numbers do not."
    )
    _notes(s, note)
    remember("Questions", note)

    out = OUT / "TaskC_Live_Presentation.pptx"
    prs.save(out)
    return out, parts, len(prs.slides)


if __name__ == "__main__":
    charts = make_summary_charts()
    path, parts, n = build_visual_pptx(charts)
    print(path, "slides", n, "charts", list(charts))

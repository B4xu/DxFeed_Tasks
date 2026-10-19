"""Offline parser tests on saved raw snapshots (no network)."""
import datetime as dt
from pathlib import Path

import pytest

from conftest import FIXTURES
from scraper.adapters import CmeAdapter, NasdaqAdapter, NyseAdapter, OpraAdapter
from scraper.normalize import normalize
from scraper.validate import easter, good_friday, run_checks

TS = dt.datetime(2026, 10, 16, 11, 0, tzinfo=dt.timezone.utc)


def _adapter(cls, tmp_path, **kw):
    return cls(tmp_path / "raw", run_ts=TS, **kw)


def test_nasdaq_nasdaqtrader_snapshot(tmp_path):
    a = _adapter(NasdaqAdapter, tmp_path)
    rows = a.parse((FIXTURES / "nasdaqtrader_calendar_2026.html").read_bytes())
    closed = sorted(r.date for r in rows if r.status == "closed")
    early = {r.date: r for r in rows if r.status == "early_close"}
    assert len(closed) == 10
    assert closed[0] == dt.date(2026, 1, 1) and closed[-1] == dt.date(2026, 12, 25)
    assert set(early) == {dt.date(2026, 11, 27), dt.date(2026, 12, 24)}
    assert early[dt.date(2026, 11, 27)].close_time_local == dt.time(13, 0)
    assert early[dt.date(2026, 11, 27)].holiday_name == "Early close (day after Thanksgiving)"
    assert early[dt.date(2026, 12, 24)].holiday_name == "Early close (eve of Christmas Holiday)"
    assert all("*" not in r.holiday_name for r in rows)         # footnote markers stripped
    assert all(r.source_url.startswith("https://www.nasdaqtrader.com") for r in rows)


def test_nasdaq_nasdaqcom_snapshot_layout(tmp_path):
    """The fallback layout (Holiday | Date | Market Status) must parse to the same dates."""
    a = _adapter(NasdaqAdapter, tmp_path)
    rows = a.parse((FIXTURES / "nasdaq_com_holiday_schedule_2026.html").read_bytes(), url=a.source_url)
    assert len([r for r in rows if r.status == "closed"]) == 10
    assert len([r for r in rows if r.status == "early_close"]) == 2


def test_nasdaq_rejects_challenge_page(tmp_path):
    a = _adapter(NasdaqAdapter, tmp_path)
    with pytest.raises(ValueError):
        a.parse((FIXTURES / "nasdaqtrader_incapsula_stub.html").read_bytes())


def test_nyse_snapshot(tmp_path):
    a = _adapter(NyseAdapter, tmp_path)
    rows = a.parse((FIXTURES / "nyse_hours_calendars.html").read_bytes())
    years = {r.source_year for r in rows}
    assert years == {2026, 2027, 2028}
    closed_2026 = sorted(r.date for r in rows if r.status == "closed" and r.date.year == 2026)
    assert len(closed_2026) == 10
    early = sorted(r.date for r in rows if r.status == "early_close")
    assert early == [dt.date(2026, 11, 27), dt.date(2026, 12, 24), dt.date(2027, 11, 26),
                     dt.date(2028, 7, 3), dt.date(2028, 11, 24)]
    assert dt.date(2028, 1, 1) not in {r.date for r in rows}          # '—' not observed


def test_opra_pdf_snapshot(tmp_path):
    a = _adapter(OpraAdapter, tmp_path)
    rows = a.parse((FIXTURES / "opra_2025_holiday_schedule.pdf").read_bytes(), year=2025, url="x")
    closed = [r for r in rows if r.status == "closed"]
    early = {r.date: r for r in rows if r.status == "early_close"}
    assert len(closed) == 11                                           # 10 for 2025 + Jan 1 2026
    assert set(early) == {dt.date(2025, 7, 3), dt.date(2025, 11, 28), dt.date(2025, 12, 24)}
    assert all(r.close_time_local == dt.time(13, 0) for r in early.values())   # "3 hours early"


def test_cme_csv_manual_input(tmp_path):
    inp = tmp_path / "input" / "cme"; inp.mkdir(parents=True)
    (inp / "sample.csv").write_text(
        "date,holiday_name,status,close_time_local,product_scope,source_url\n"
        "2026-11-26,Thanksgiving (SYNTHETIC TEST ROW),early_close,12:00,Equity Index,https://example.test\n"
        "2026-12-25,Christmas (SYNTHETIC TEST ROW),closed,,Equity Index,https://example.test\n")
    a = CmeAdapter(tmp_path / "raw", run_ts=TS, input_dir=inp)
    rows = a.scrape()
    assert len(rows) == 2 and rows[0].timezone == "America/Chicago"
    df = normalize(rows)
    assert df.loc[df.status == "early_close", "close_time_utc"].iloc[0] == "2026-11-26T18:00:00Z"  # 12:00 CST


def test_cme_without_input_returns_zero_rows_with_note(tmp_path):
    a = CmeAdapter(tmp_path / "raw", run_ts=TS, input_dir=tmp_path / "nope")
    assert a.scrape() == []
    assert any("MANUAL_INPUT_REQUIRED" in n for n in a.notes)


def test_cme_xlsx_equities_trading_hours(tmp_path):
    """Operator-downloaded Trading Hours → Holidays xlsx: Equities row only."""
    inp = tmp_path / "input" / "cme"
    inp.mkdir(parents=True)
    src = FIXTURES / "cme_thanksgiving_2026.xlsx"
    (inp / src.name).write_bytes(src.read_bytes())
    a = CmeAdapter(tmp_path / "raw", run_ts=TS, input_dir=inp)
    rows = a.scrape()
    by_date = {r.date: r for r in rows}
    assert set(by_date) == {dt.date(2026, 11, 26), dt.date(2026, 11, 27)}
    assert by_date[dt.date(2026, 11, 26)].status == "closed"
    assert by_date[dt.date(2026, 11, 27)].status == "early_close"
    assert by_date[dt.date(2026, 11, 27)].close_time_local == dt.time(12, 15)
    assert "Thanksgiving" in by_date[dt.date(2026, 11, 26)].holiday_name


def test_utc_conversion_handles_dst():
    a = NyseAdapter(Path("/tmp/x"), run_ts=TS)
    summer = a.row(dt.date(2028, 7, 3), "x", "early_close", 2028, close_local=dt.time(13, 0))
    winter = a.row(dt.date(2026, 12, 24), "x", "early_close", 2026, close_local=dt.time(13, 0))
    df = normalize([summer, winter])
    assert df.loc[df.date == "2028-07-03", "close_time_utc"].iloc[0] == "2028-07-03T17:00:00Z"   # EDT
    assert df.loc[df.date == "2026-12-24", "close_time_utc"].iloc[0] == "2026-12-24T18:00:00Z"   # EST


def test_easter_and_good_friday():
    assert easter(2026) == dt.date(2026, 4, 5)
    assert good_friday(2026) == dt.date(2026, 4, 3)
    assert good_friday(2027) == dt.date(2027, 3, 26)
    assert good_friday(2028) == dt.date(2028, 4, 14)
    assert good_friday(2025) == dt.date(2025, 4, 18)


def test_validation_nasdaq_vs_nyse_and_missing_exchange(tmp_path):
    nyse = _adapter(NyseAdapter, tmp_path).parse((FIXTURES / "nyse_hours_calendars.html").read_bytes())
    nas = _adapter(NasdaqAdapter, tmp_path).parse((FIXTURES / "nasdaqtrader_calendar_2026.html").read_bytes())
    df = normalize(nyse + nas)
    checks = run_checks(df, {"NYSE": len(nyse), "NASDAQ": len(nas), "OPRA": 0},
                        {"OPRA": ["SOURCE_UNAVAILABLE: test"]}, None)
    by = {c.name: c for c in checks}
    assert by["weekday"].level == "PASS"
    assert by["duplicates"].level == "PASS"
    assert by["good_friday"].level == "PASS"
    assert by["NYSE_vs_NASDAQ.closed"].level == "PASS"
    assert by["NYSE_vs_NASDAQ.early_close"].level == "PASS"
    assert by["OPRA.rows"].level == "WARN" and "MISSING" in by["OPRA.rows"].detail
    assert by["NYSE.2026.closures"].level == "PASS"


def test_min_early_close_check_warns_on_zero():
    import datetime as dt
    import pandas as pd
    from scraper.validate import run_checks

    rows = []
    for i in range(9):
        d = dt.date(2026, 1, 1) + dt.timedelta(days=30 * i)
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        rows.append({"exchange": "NYSE", "date": d.isoformat(), "status": "closed", "close_time_local": "",
                     "source_year": 2026, "holiday_name": "x", "source": "t", "canonical_name": "x"})
    df = pd.DataFrame(rows)
    checks = run_checks(df, {"NYSE": len(df)}, {}, None)
    ec = [c for c in checks if c.name == "NYSE.2026.early_closes"]
    assert ec and ec[0].level == "WARN"

"""Orchestrator: scrape -> normalise -> validate -> write outputs -> (optionally) upload.

    python -m scraper.run [--exchanges NYSE,NASDAQ,OPRA,CME] [--upload] [--fail-on WARN|FAIL]

Exit codes: 0 ok, 1 validation FAIL, 2 adapter crash. Logs are JSON lines on stderr
(structured) so that CI can grep them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import traceback
from pathlib import Path

import pandas as pd

from .adapters import ADAPTERS
from .normalize import normalize
from .validate import checks_to_json, overall_level, render_report, run_checks

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "output"


class JsonFormatter(logging.Formatter):
    def format(self, record):  # noqa: D102
        return json.dumps({"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                           "level": record.levelname, "logger": record.name, "msg": record.getMessage()})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchanges", default=",".join(ADAPTERS))
    ap.add_argument("--upload", action="store_true", help="upload to Google Drive (needs env vars or DRY_RUN=1)")
    ap.add_argument("--fail-on", default="FAIL", choices=["WARN", "FAIL"])
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)

    h = logging.StreamHandler(sys.stderr); h.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[h])
    log = logging.getLogger("holidays")
    run_ts = dt.datetime.now(dt.timezone.utc)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    rows, counts, notes, crashed = [], {}, {}, []
    for ex in [e.strip().upper() for e in a.exchanges.split(",") if e.strip()]:
        adapter = ADAPTERS[ex](RAW, run_ts=run_ts)
        try:
            r = adapter.scrape()
            rows.extend(r); counts[ex] = len(r); notes[ex] = adapter.notes
            log.info("%s: %d rows", ex, len(r))
        except Exception as e:  # noqa: BLE001
            counts[ex] = 0; notes[ex] = adapter.notes + [f"CRASH: {e!r}"]; crashed.append(ex)
            log.error("%s adapter failed: %r\n%s", ex, e, traceback.format_exc())

    df = normalize(rows)
    prev = out / "trading_holidays_combined.csv"
    prev_copy = None
    if prev.exists():
        prev_copy = out / "_previous_combined.csv"; prev_copy.write_bytes(prev.read_bytes())
    checks = run_checks(df, counts, notes, prev_copy)
    report = render_report(checks, df, notes, run_ts)
    level = overall_level(checks)

    df.to_csv(prev, index=False)
    for ex, g in df.groupby("exchange"):
        g.to_csv(out / f"trading_holidays_{ex}.csv", index=False)
    (out / "validation_report.md").write_text(report)
    (out / "validation_checks.json").write_text(checks_to_json(checks))
    (out / "run_meta.json").write_text(json.dumps({"run_ts": run_ts.isoformat(), "rows": len(df), "counts": counts,
                                                   "level": level, "crashed": crashed}, indent=2))
    print(report)

    if a.upload:
        from .upload_drive import upload_from_env
        manifest = upload_from_env(df, report, out)
        log.info("upload manifest: %s", json.dumps(manifest))

    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    if crashed:
        return 2
    return 1 if order[level] >= order[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())

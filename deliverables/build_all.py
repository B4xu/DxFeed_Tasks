#!/usr/bin/env python3
"""Rebuild every chart, Word report and the Task C deck. Offline; no demo traffic."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

STEPS = [
    ("Task C report", HERE / "taskC_assessment" / "build_report.py"),
    ("Task B report", HERE / "taskB_incident" / "build_report.py"),
    ("Task A report", HERE / "taskA_holidays" / "build_report.py"),
    ("Task C deck", HERE / "taskC_presentation_pack" / "build_pack.py"),
    ("PDF export", HERE / "export_pdfs.py"),
]


def main() -> int:
    for label, script in STEPS:
        print(f"== {label}")
        rc = subprocess.call([sys.executable, script.name], cwd=script.parent)
        if rc:
            print(f"{label} failed (exit {rc})", file=sys.stderr)
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())

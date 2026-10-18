#!/usr/bin/env python3
"""Export the three Word reports and the Task C deck to PDF next to the originals.

Needs LibreOffice: either `soffice` on PATH or the Flatpak org.libreoffice.LibreOffice.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = [
    HERE / "taskC_assessment" / "TaskC_Assessment_Report.docx",
    HERE / "taskB_incident" / "TaskB_Incident_Report.docx",
    HERE / "taskA_holidays" / "TaskA_Holiday_Scraper_Report.docx",
    HERE / "taskC_presentation_pack" / "TaskC_Live_Presentation.pptx",
]


def soffice() -> list[str] | None:
    if shutil.which("soffice"):
        return ["soffice"]
    if shutil.which("flatpak"):
        ok = subprocess.run(["flatpak", "info", "org.libreoffice.LibreOffice"], capture_output=True).returncode == 0
        if ok:
            return ["flatpak", "run", f"--filesystem={HERE}", "org.libreoffice.LibreOffice"]
    return None


def main() -> int:
    cmd = soffice()
    if not cmd:
        print("LibreOffice not found; skipping PDF export", file=sys.stderr)
        return 0
    for f in FILES:
        subprocess.run(cmd + ["--headless", "--convert-to", "pdf", "--outdir", str(f.parent), str(f)],
                       check=True, capture_output=True)
        print("  ->", f.with_suffix(".pdf"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

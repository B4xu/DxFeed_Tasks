# dxFeed L2 Support Engineer — assessment package

The finished reports and the presentation are in [`submission/`](submission/), each as Word/PowerPoint and PDF:

| Task | Report / deck in `submission/` | Source, code and evidence |
|---|---|---|
| A — trading-holiday scraper | `TaskA_Holiday_Scraper_Report.docx` / `.pdf` | [`deliverables/taskA_holidays/`](deliverables/taskA_holidays/), CSVs in `output/` |
| B — on-call incident | `TaskB_Incident_Report.docx` / `.pdf` | [`deliverables/taskB_incident/`](deliverables/taskB_incident/), `answer.md` |
| C — demo feed assessment | `TaskC_Assessment_Report.docx` / `.pdf` | [`deliverables/taskC_assessment/`](deliverables/taskC_assessment/), `report.md`, `evidence/` |
| C — live presentation | `TaskC_Live_Presentation.pptx` / `.pdf` (27 slides) | [`deliverables/taskC_presentation_pack/`](deliverables/taskC_presentation_pack/), `SPEAKER_SCRIPT.md` |

The combined holiday CSV for Google Sheets is
[`deliverables/taskA_holidays/output/trading_holidays_combined.csv`](deliverables/taskA_holidays/output/trading_holidays_combined.csv).

Cross-task notes: `deliverables/executive_summary.md`, `deliverables/audit_status.md`,
`deliverables/worklog.md`.

## Environment

```bash
conda create -n dxfeed python=3.12 -y && conda activate dxfeed
pip install -r deliverables/taskA_holidays/requirements.txt
pip install pandas numpy matplotlib aiohttp requests python-docx python-pptx
```

## Rebuild every report and the deck (offline, no demo traffic)

```bash
python deliverables/build_all.py
```

The last step exports the reports and the deck to PDF with LibreOffice (`soffice` on PATH, or
`flatpak install --user flathub org.libreoffice.LibreOffice`). Without LibreOffice it is skipped.

## Automation

`.github/workflows/trading-holidays.yml` runs the Task A scraper weekly (Monday 06:17 UTC) and
on demand. It needs the repository secrets `GOOGLE_SERVICE_ACCOUNT_JSON` and `GDRIVE_FOLDER_ID`
for the Drive upload (without them it runs in `DRY_RUN`), and optionally `SLACK_WEBHOOK_URL`.

## Evidence storage

Raw dxFeed response bodies under `deliverables/taskC_assessment/evidence/candles/pass1/` and
`evidence/probe/raw/` are stored gzip-compressed (`*.json.gz`); the scripts read them
transparently. The parsed CSVs next to them are uncompressed.

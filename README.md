# dxFeed L2 Support Engineer — assessment package

| Task | Folder | Main deliverable |
|---|---|---|
| A — trading-holiday scraper | [`deliverables/taskA_holidays/`](deliverables/taskA_holidays/) | `TaskA_Holiday_Scraper_Report.docx` / `.pdf`, CSVs in `output/` |
| B — on-call incident | [`deliverables/taskB_incident/`](deliverables/taskB_incident/) | `TaskB_Incident_Report.docx` / `.pdf`, `answer.md` |
| C — demo feed assessment | [`deliverables/taskC_assessment/`](deliverables/taskC_assessment/) | `TaskC_Assessment_Report.docx` / `.pdf`, `report.md`, `evidence/` |
| C — live presentation | [`deliverables/taskC_presentation_pack/`](deliverables/taskC_presentation_pack/) | `TaskC_Live_Presentation.pptx` / `.pdf` (26 slides), `SPEAKER_SCRIPT.md` |

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

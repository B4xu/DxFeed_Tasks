"""Upload CSVs and a converted Google Sheet to Google Drive with a service account.

Credentials are NEVER read from the repo. Provide one of:
  GOOGLE_SERVICE_ACCOUNT_JSON   - the JSON key *content* (e.g. a GitHub Actions secret)
  GOOGLE_APPLICATION_CREDENTIALS - path to the JSON key file
and
  GDRIVE_FOLDER_ID              - target Drive folder ID (shared with the service account
                                  e-mail as Editor; on a Shared Drive the SA must be a member)
Optional:
  GDRIVE_SHARE_WITH             - comma-separated e-mails to share the folder with (reader)
  DRY_RUN=1                     - do everything except call the Drive API (used in tests/CI
                                  without secrets); writes an upload_manifest.json instead.

Re-runs overwrite: files are looked up by name inside the folder and updated by file ID,
so the Drive folder never accumulates duplicates. The Sheet is produced by uploading an
.xlsx (one tab per exchange + combined + validation) with the Google Sheets MIME type so
Drive converts it server-side.
"""
from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path

import pandas as pd

log = logging.getLogger("holidays.drive")
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME = "text/csv"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _credentials():
    from google.oauth2 import service_account  # imported lazily so DRY_RUN needs no google libs
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        return service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path and Path(path).exists():
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    raise RuntimeError("No Google credentials: set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS")


class DriveUploader:
    def __init__(self, folder_id: str, dry_run: bool = False, service=None):
        self.folder_id = folder_id
        self.dry_run = dry_run
        self.manifest: list[dict] = []
        if service is not None:
            self.svc = service
        elif dry_run:
            self.svc = None
        else:
            from googleapiclient.discovery import build
            self.svc = build("drive", "v3", credentials=_credentials(), cache_discovery=False)

    # -------------------------------------------------------------- helpers
    def _find(self, name: str) -> str | None:
        if self.svc is None:
            return None
        q = f"name = '{name}' and '{self.folder_id}' in parents and trashed = false"
        res = self.svc.files().list(q=q, fields="files(id,name)", supportsAllDrives=True,
                                    includeItemsFromAllDrives=True).execute()
        files = res.get("files", [])
        return files[0]["id"] if files else None

    def upload_bytes(self, name: str, data: bytes, mime: str, convert_to: str | None = None) -> dict:
        """Create or update (by ID) a file. convert_to=SHEET_MIME makes Drive convert the upload."""
        entry = {"name": name, "bytes": len(data), "mime": mime, "convert_to": convert_to}
        if self.svc is None:  # dry run
            entry.update(action="DRY_RUN", id=None)
            self.manifest.append(entry)
            log.info("DRY_RUN would upload %s (%d bytes, %s -> %s)", name, len(data), mime, convert_to or mime)
            return entry
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=False)
        existing = self._find(name)
        meta: dict = {"name": name}
        if convert_to:
            meta["mimeType"] = convert_to
        if existing:
            f = self.svc.files().update(fileId=existing, media_body=media, body={"mimeType": convert_to} if convert_to else None,
                                        fields="id,name,webViewLink", supportsAllDrives=True).execute()
            entry.update(action="updated", id=f["id"], link=f.get("webViewLink"))
        else:
            meta["parents"] = [self.folder_id]
            f = self.svc.files().create(body=meta, media_body=media, fields="id,name,webViewLink",
                                        supportsAllDrives=True).execute()
            entry.update(action="created", id=f["id"], link=f.get("webViewLink"))
        self.manifest.append(entry)
        log.info("%s %s -> %s", entry["action"], name, entry["id"])
        return entry

    def share_folder(self, emails: list[str], role: str = "reader") -> None:
        for e in [x.strip() for x in emails if x.strip()]:
            if self.svc is None:
                self.manifest.append({"name": "<folder>", "action": "DRY_RUN_share", "email": e, "role": role})
                continue
            self.svc.permissions().create(fileId=self.folder_id, body={"type": "user", "role": role, "emailAddress": e},
                                          sendNotificationEmail=False, supportsAllDrives=True).execute()
            self.manifest.append({"name": "<folder>", "action": "shared", "email": e, "role": role})

    # ------------------------------------------------------------- pipeline
    def upload_dataset(self, combined: pd.DataFrame, validation_md: str, out_dir: Path) -> list[dict]:
        combined_csv = combined.to_csv(index=False).encode()
        self.upload_bytes("trading_holidays_combined.csv", combined_csv, CSV_MIME)
        for ex, g in combined.groupby("exchange"):
            self.upload_bytes(f"trading_holidays_{ex}.csv", g.to_csv(index=False).encode(), CSV_MIME)
        # Google Sheet: build xlsx with tabs then upload with conversion
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            combined.to_excel(xw, sheet_name="combined", index=False)
            for ex, g in combined.groupby("exchange"):
                g.to_excel(xw, sheet_name=str(ex)[:31], index=False)
            val_rows = [l for l in validation_md.splitlines() if l.startswith("|") and not l.startswith("|---")]
            if val_rows:
                hdr = [c.strip() for c in val_rows[0].strip("|").split("|")]
                body = [[c.strip() for c in r.strip("|").split("|")] for r in val_rows[1:] if r.count("|") == val_rows[0].count("|")]
                pd.DataFrame(body, columns=hdr).to_excel(xw, sheet_name="validation", index=False)
            else:
                pd.DataFrame({"report": validation_md.splitlines()}).to_excel(xw, sheet_name="validation", index=False)
        self.upload_bytes("trading_holidays", buf.getvalue(), XLSX_MIME, convert_to=SHEET_MIME)
        share = os.environ.get("GDRIVE_SHARE_WITH", "")
        if share:
            self.share_folder(share.split(","))
        (out_dir / "upload_manifest.json").write_text(json.dumps(self.manifest, indent=2))
        return self.manifest


def upload_from_env(combined: pd.DataFrame, validation_md: str, out_dir: Path) -> list[dict]:
    dry = os.environ.get("DRY_RUN", "") not in ("", "0", "false")
    folder = os.environ.get("GDRIVE_FOLDER_ID", "")
    if not folder and not dry:
        raise RuntimeError("GDRIVE_FOLDER_ID is not set (or set DRY_RUN=1)")
    return DriveUploader(folder or "DRY_RUN_FOLDER", dry_run=dry).upload_dataset(combined, validation_md, out_dir)

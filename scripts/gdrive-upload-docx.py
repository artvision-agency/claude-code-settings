#!/usr/bin/env python3
"""
Загрузить .docx в Google Docs + установить sharing (anyone with link).
Использует OAuth с client_secret_v2.json (voice-87003).

Usage:
    python3 gdrive-upload-docx.py /path/to/file.docx [--role commenter|reader|writer]

При первом запуске откроется браузер для OAuth consent.
Токен сохраняется в ~/artvision-data/scripts/gdrive_token.json — последующие запуски тихие.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CLIENT_SECRET = "/Users/antonk/artvision-data/scripts/client_secret_v2.json"
TOKEN_PATH = "/Users/antonk/artvision-data/scripts/gdrive_token.json"


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[gdrive] refresh failed: {e}, doing fresh OAuth flow")
            creds = None

    if not creds or not creds.valid:
        print("[gdrive] OAuth flow — открываю браузер для consent...", file=sys.stderr)
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        os.chmod(TOKEN_PATH, 0o600)
        print(f"[gdrive] токен сохранён: {TOKEN_PATH}", file=sys.stderr)

    return creds


def upload_as_google_doc(file_path: str, creds, role: str = "commenter") -> dict:
    drive = build("drive", "v3", credentials=creds)

    fname = Path(file_path).name
    title = fname.replace(".docx", "")

    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
    }
    media = MediaFileUpload(
        file_path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        resumable=True,
    )

    print(f"[gdrive] uploading {fname} as Google Doc...", file=sys.stderr)
    file = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, mimeType, webViewLink",
    ).execute()

    file_id = file["id"]
    print(f"[gdrive] uploaded: {file_id}", file=sys.stderr)

    # Permissions: anyone with link
    permission = {
        "type": "anyone",
        "role": role,
        "allowFileDiscovery": False,
    }
    drive.permissions().create(
        fileId=file_id,
        body=permission,
        fields="id",
    ).execute()
    print(f"[gdrive] permission set: anyone with link → {role}", file=sys.stderr)

    return {
        "id": file_id,
        "name": file["name"],
        "webViewLink": file.get("webViewLink"),
        "role": role,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to .docx file")
    parser.add_argument("--role", default="commenter", choices=["reader", "commenter", "writer"])
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"FAIL: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    creds = get_credentials()
    result = upload_as_google_doc(args.file, creds, args.role)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

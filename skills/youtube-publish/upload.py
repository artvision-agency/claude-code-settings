#!/usr/bin/env python3
"""YouTube Data API v3 uploader (OAuth).

Usage:
    python3 upload.py --file VIDEO.mp4 --title "Title" [--description "..."]
                      [--tags "a,b,c"] [--privacy unlisted] [--category 23]

CRITICAL fixes from review:
  - C1: client_secret NO LONGER written into token file (was a leak)
  - WARN: relative path for SCRIPTS (env override)
  - WARN: chunksize=10MB instead of -1 (avoids loading whole file into memory)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# ─── Config constants ────────────────────────────────────────────────
YT_TITLE_MAX = 100
SHORTS_MAX_DURATION_SEC = 60
UPLOAD_CHUNK_BYTES = 10 * 1024 * 1024  # 10 MB — avoids whole-file in-memory load
YT_SHORTS_TAG = "#Shorts"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
DEFAULT_SCRIPTS_DIR = Path(
    os.environ.get(
        "YT_SCRIPTS_DIR",
        str(Path.home() / "artvision-data" / "scripts"),
    )
)
TOKEN_FILE = DEFAULT_SCRIPTS_DIR / "youtube_token.json"
CLIENT_SECRET = DEFAULT_SCRIPTS_DIR / "client_secret.json"
UPLOAD_LOG = Path.home() / ".claude" / "logs" / "youtube-uploads.jsonl"


# ─── OAuth ───────────────────────────────────────────────────────────

def _save_token(creds: Credentials) -> None:
    """Write token WITHOUT client_secret (that lives in client_secret.json only)."""
    TOKEN_FILE.write_text(json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }, indent=2))


def load_credentials() -> Credentials:
    """Load OAuth credentials. Refreshes if expired."""
    with open(TOKEN_FILE) as f:
        td = json.load(f)
    with open(CLIENT_SECRET) as f:
        cs = json.load(f)["installed"]
    creds = Credentials(
        token=td.get("token"),
        refresh_token=td.get("refresh_token"),
        token_uri=td.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=cs["client_id"],
        client_secret=cs["client_secret"],
        scopes=td.get("scopes", SCOPES),
    )
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)
    return creds


# ─── Video metadata ──────────────────────────────────────────────────

def is_short(path: str) -> bool:
    """Short = duration < 60s AND vertical (h > w)."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
            capture_output=True, text=True, timeout=30, check=True,
        )
        d = json.loads(r.stdout)
        for s in d.get("streams", []):
            if s.get("codec_type") == "video":
                w, h = int(s.get("width", 0)), int(s.get("height", 0))
                dur = float(s.get("duration", 0))
                return 0 < dur < SHORTS_MAX_DURATION_SEC and h > w
    except (subprocess.SubprocessError, KeyError, ValueError, json.JSONDecodeError):
        return False
    return False


def build_body(args: argparse.Namespace) -> dict[str, Any]:
    """Build YouTube API insert body from CLI args."""
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    description = args.description or ""
    if is_short(args.file) and YT_SHORTS_TAG.lower() not in description.lower():
        description = (description + f"\n\n{YT_SHORTS_TAG}").strip()
    return {
        "snippet": {
            "title": args.title[:YT_TITLE_MAX],
            "description": description,
            "tags": tags,
            "categoryId": args.category,
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }


# ─── Upload ──────────────────────────────────────────────────────────

def perform_upload(yt: Any, body: dict, file_path: str) -> str:
    """Execute resumable upload. Returns video ID."""
    media = MediaFileUpload(
        file_path, chunksize=UPLOAD_CHUNK_BYTES, resumable=True, mimetype="video/mp4",
    )
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    print(f"Uploading {file_path} → YouTube...", flush=True)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"  {int(status.progress()*100)}%", flush=True)
    return response["id"]


def log_upload(*, file_path: str, title: str, url: str, vid: str, privacy: str) -> None:
    """Append upload record to JSONL log."""
    UPLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(UPLOAD_LOG, "a") as f:
        f.write(json.dumps({
            "ts": datetime.datetime.now().isoformat(),
            "file": file_path,
            "title": title,
            "url": url,
            "privacy": privacy,
            "video_id": vid,
        }, ensure_ascii=False) + "\n")


# ─── Orchestrator ────────────────────────────────────────────────────

def upload(args: argparse.Namespace) -> int:
    try:
        creds = load_credentials()
    except FileNotFoundError as e:
        print(f"ERROR: missing OAuth file: {e}", file=sys.stderr)
        return 2
    yt = build("youtube", "v3", credentials=creds)
    body = build_body(args)
    try:
        vid = perform_upload(yt, body, args.file)
    except HttpError as e:
        print(f"HttpError: {e}", file=sys.stderr)
        return 1
    url = f"https://youtu.be/{vid}"
    print(f"✓ UPLOADED: {url}")
    print(f"  Title: {args.title}")
    print(f"  Privacy: {args.privacy}")
    log_upload(file_path=args.file, title=args.title, url=url, vid=vid, privacy=args.privacy)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--privacy", default="unlisted",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--category", default="23",
                    help="23=Comedy, 24=Entertainment, 22=People")
    return upload(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())

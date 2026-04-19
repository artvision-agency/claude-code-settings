#!/bin/bash
# Generic YouTube scheduled upload wrapper.
#
# Usage:
#   yt_upload_scheduled.sh <job.env>
#
# job.env format (sourced as bash):
#   FILE=/path/to/video.mp4
#   TITLE="Video title"
#   DESCRIPTION="Description text"
#   TAGS="tag1,tag2,tag3"
#   PRIVACY=unlisted                       # private|unlisted|public
#   CATEGORY=23                            # 23=Comedy, 24=Entertainment, 22=People
#   SELF_CLEANUP_PLIST=/path/to/plist      # optional, removed only on SUCCESS
#   HEALTHCHECK_URL=https://hc-ping.com/.. # optional, pings on success/fail
#   LOG_FILE=/path/to/log                  # optional, default ~/.claude/logs/yt-scheduled.log
#
# Called by: LaunchAgent plist (one-shot or recurring).
# Exit codes: 0 = success, 1 = upload failed, 2 = config error.

set -euo pipefail

JOB="${1:-}"
if [ -z "$JOB" ] || [ ! -f "$JOB" ]; then
    echo "ERROR: job file required as first arg: $0 <job.env>" >&2
    exit 2
fi

# shellcheck source=/dev/null
source "$JOB"

: "${FILE:?FILE not set in $JOB}"
: "${TITLE:?TITLE not set in $JOB}"
PRIVACY="${PRIVACY:-unlisted}"
CATEGORY="${CATEGORY:-23}"
DESCRIPTION="${DESCRIPTION:-}"
TAGS="${TAGS:-}"

if [ ! -f "$FILE" ]; then
    echo "ERROR: video file not found: $FILE" >&2
    exit 2
fi

LOG="${LOG_FILE:-$HOME/.claude/logs/yt-scheduled.log}"
mkdir -p "$(dirname "$LOG")"

{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── job: $(basename "$JOB") ──"
    echo "  file: $FILE"
    echo "  title: $TITLE"
    echo "  privacy: $PRIVACY"
} >> "$LOG"

EXIT_CODE=0
python3 "$HOME/.claude/skills/youtube-publish/upload.py" \
    --file "$FILE" \
    --title "$TITLE" \
    --description "$DESCRIPTION" \
    --tags "$TAGS" \
    --privacy "$PRIVACY" \
    --category "$CATEGORY" \
    >> "$LOG" 2>&1 || EXIT_CODE=$?

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Exit=$EXIT_CODE" >> "$LOG"

# Optional healthcheck ping
if [ -n "${HEALTHCHECK_URL:-}" ]; then
    if [ "$EXIT_CODE" -eq 0 ]; then
        curl -fsS -m 10 "$HEALTHCHECK_URL" >> "$LOG" 2>&1 || true
    else
        curl -fsS -m 10 "$HEALTHCHECK_URL/fail" >> "$LOG" 2>&1 || true
    fi
fi

# Self-cleanup ONLY on success (keeps retry possible on failure)
if [ "$EXIT_CODE" -eq 0 ] && [ -n "${SELF_CLEANUP_PLIST:-}" ] && [ -f "$SELF_CLEANUP_PLIST" ]; then
    launchctl unload "$SELF_CLEANUP_PLIST" 2>/dev/null || true
    rm -f "$SELF_CLEANUP_PLIST"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Self-cleanup: removed $SELF_CLEANUP_PLIST" >> "$LOG"
fi

exit "$EXIT_CODE"

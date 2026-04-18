#!/bin/bash
set -euo pipefail

# ================================================================
# deploy-with-check.sh — scp wrapper with factcheck
#
# Usage:
#   deploy-with-check.sh <local_file> <remote_path> [--force]
#   deploy-with-check.sh index.html root@80.90.181.152:/var/www/site/
#   deploy-with-check.sh kp.html root@80.90.181.152:/var/www/site/ --force
#
# Runs factcheck before scp for HTML files. Blocks if CRITICAL.
# Non-HTML files are deployed without factcheck.
#
# 0 tokens Claude — pure bash.
# ================================================================

VPS_IP="80.90.181.152"
FACTCHECK_HOOK="/Users/antonk/.claude/hooks/pre-deploy-factcheck.sh"
SMOKE_HOOK="/Users/antonk/.claude/hooks/post-deploy-smoke.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERR]${NC} $1"; }

usage() {
    echo "Usage: deploy-with-check.sh <local_file> <remote_path> [--force]"
    echo ""
    echo "Arguments:"
    echo "  local_file    Local file to deploy"
    echo "  remote_path   Remote destination (user@host:/path/)"
    echo "  --force       Skip factcheck and deploy anyway"
    echo ""
    echo "Examples:"
    echo "  deploy-with-check.sh clients/tvorim/kp/offer.html root@${VPS_IP}:/var/www/artvision/"
    echo "  deploy-with-check.sh page.html root@${VPS_IP}:/var/www/site/ --force"
    exit 1
}

# --- Parse arguments ---

LOCAL_FILE=""
REMOTE_PATH=""
FORCE=0

for arg in "$@"; do
    case "$arg" in
        --force)
            FORCE=1
            ;;
        --help|-h)
            usage
            ;;
        *)
            if [ -z "$LOCAL_FILE" ]; then
                LOCAL_FILE="$arg"
            elif [ -z "$REMOTE_PATH" ]; then
                REMOTE_PATH="$arg"
            else
                log_err "Too many arguments. See --help"
                exit 1
            fi
            ;;
    esac
done

if [ -z "$LOCAL_FILE" ] || [ -z "$REMOTE_PATH" ]; then
    usage
fi

if [ ! -f "$LOCAL_FILE" ]; then
    log_err "File not found: $LOCAL_FILE"
    exit 1
fi

# --- Step 1: Factcheck (HTML files only) ---

if [[ "$LOCAL_FILE" =~ \.html$ ]]; then
    log_info "Running factcheck on: $LOCAL_FILE"

    if [ -x "$FACTCHECK_HOOK" ]; then
        FACTCHECK_ARGS="$LOCAL_FILE"
        [ $FORCE -eq 1 ] && FACTCHECK_ARGS="$LOCAL_FILE --force"

        if ! "$FACTCHECK_HOOK" $FACTCHECK_ARGS; then
            if [ $FORCE -eq 0 ]; then
                log_err "Factcheck FAILED. Deployment blocked."
                log_info "Use --force to bypass factcheck."
                exit 1
            fi
        fi
    else
        log_warn "Factcheck hook not found or not executable: $FACTCHECK_HOOK"
        log_warn "Proceeding without factcheck."
    fi
else
    log_info "Non-HTML file — skipping factcheck."
fi

# --- Step 2: Deploy via scp ---

log_info "Deploying: $LOCAL_FILE -> $REMOTE_PATH"

if scp "$LOCAL_FILE" "$REMOTE_PATH"; then
    log_ok "Deployed successfully: $LOCAL_FILE"
else
    log_err "scp failed!"
    exit 1
fi

# --- Step 3: Post-deploy smoke test (if available) ---

if [ -x "$SMOKE_HOOK" ]; then
    # Extract hostname from remote path for smoke test
    REMOTE_HOST=$(echo "$REMOTE_PATH" | cut -d':' -f1 | cut -d'@' -f2)
    if [ "$REMOTE_HOST" = "$VPS_IP" ]; then
        log_info "Running post-deploy smoke test..."
        "$SMOKE_HOOK" "$LOCAL_FILE" "$REMOTE_PATH" 2>/dev/null || true
    fi
fi

log_ok "Deploy complete: $LOCAL_FILE"

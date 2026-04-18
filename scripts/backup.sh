#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# backup.sh — Бэкап репо + VPS данных
#
# Использование:
#   backup.sh local   — бэкап локальных репо (tar.gz)
#   backup.sh vps     — бэкап VPS (БД + сайты)
#   backup.sh all     — всё
#
# 0 токенов Claude.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

VPS="root@80.90.181.152"
BACKUP_DIR="$HOME/backups"
DATE=$(date +%Y-%m-%d_%H%M)

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}✅${NC} $1"; }
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }

mkdir -p "$BACKUP_DIR"

backup_local() {
    log_info "Бэкап локальных репо..."

    for repo in artvision-data artvision-tg-bot devops-agent; do
        local repo_path="$HOME/$repo"
        if [ -d "$repo_path" ]; then
            tar -czf "$BACKUP_DIR/${repo}_${DATE}.tar.gz" \
                --exclude='.git' \
                --exclude='node_modules' \
                --exclude='__pycache__' \
                -C "$HOME" "$repo"
            local size
            size=$(du -h "$BACKUP_DIR/${repo}_${DATE}.tar.gz" | cut -f1)
            log_ok "$repo → $size"
        fi
    done

    # Очистка старых бэкапов (>7 дней)
    find "$BACKUP_DIR" -name "*_*.tar.gz" -mtime +7 -delete 2>/dev/null
    log_info "Старые бэкапы (>7 дней) удалены"
}

backup_vps() {
    log_info "Бэкап VPS..."

    # MySQL dump
    ssh "$VPS" "mysqldump --all-databases --single-transaction | gzip" \
        > "$BACKUP_DIR/vps_mysql_${DATE}.sql.gz"
    local db_size
    db_size=$(du -h "$BACKUP_DIR/vps_mysql_${DATE}.sql.gz" | cut -f1)
    log_ok "MySQL dump → $db_size"

    # WP uploads (только новое)
    rsync -avz --ignore-existing \
        "$VPS:/var/www/tvorim/wp-content/uploads/" \
        "$BACKUP_DIR/tvorim-uploads/" 2>/dev/null
    log_ok "WP uploads синхронизированы"

    # nginx configs
    scp -q "$VPS:/etc/nginx/sites-enabled/*" "$BACKUP_DIR/nginx-configs/" 2>/dev/null || {
        mkdir -p "$BACKUP_DIR/nginx-configs"
        scp -q "$VPS:/etc/nginx/sites-enabled/*" "$BACKUP_DIR/nginx-configs/"
    }
    log_ok "Nginx конфиги скопированы"

    # Очистка старых дампов
    find "$BACKUP_DIR" -name "vps_mysql_*.sql.gz" -mtime +7 -delete 2>/dev/null
}

case "${1:-all}" in
    local)  backup_local ;;
    vps)    backup_vps ;;
    all)    backup_local; echo ""; backup_vps ;;
    *)
        echo "Использование: backup.sh [local|vps|all]"
        exit 1
        ;;
esac

echo ""
log_ok "Бэкап завершён → $BACKUP_DIR"
du -sh "$BACKUP_DIR"

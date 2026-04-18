#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# deploy.sh — Универсальный деплой на VPS
#
# Использование:
#   deploy.sh tvorim          — деплой темы Творим
#   deploy.sh tvorim page X   — деплой одной Tilda-страницы
#   deploy.sh bot             — деплой TG-бота
#   deploy.sh nginx           — перезагрузка nginx
#   deploy.sh status          — статус всех сервисов
#
# 0 токенов Claude — чистый bash.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

VPS="root@80.90.181.152"
VPS_TVORIM="/var/www/tvorim"
VPS_BOT="/opt/artvision-tg-bot"
LOCAL_BOT="$HOME/artvision-tg-bot"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}✅${NC} $1"; }
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
log_err()  { echo -e "${RED}❌${NC} $1"; }

deploy_tvorim() {
    log_info "Деплой темы Творим → $VPS:$VPS_TVORIM"

    # Перезагрузка PHP-FPM (очистка opcache)
    ssh "$VPS" "systemctl reload php8.3-fpm && echo 'PHP-FPM reloaded'"

    log_ok "Творим задеплоен"
}

deploy_tvorim_page() {
    local page="$1"
    local local_file="$2"
    local remote_dir="$VPS_TVORIM/wp-content/themes/tvorim-theme/tilda_pages"

    log_info "Деплой страницы: $page"
    scp "$local_file" "$VPS:$remote_dir/$page"
    ssh "$VPS" "sed -i 's|tvorimsovershenstvo\.ru|tvorim.artvision.pro|g' $remote_dir/$page"
    log_ok "Страница $page задеплоена"
}

deploy_bot() {
    log_info "Деплой TG-бота → $VPS:$VPS_BOT"

    cd "$LOCAL_BOT"
    rsync -avz --exclude='node_modules' --exclude='.env' --exclude='.git' \
        ./ "$VPS:$VPS_BOT/"

    ssh "$VPS" "cd $VPS_BOT && npm install --production && pm2 restart artvision-bot"
    log_ok "TG-бот задеплоен и перезапущен"
}

deploy_nginx() {
    log_info "Проверка + перезагрузка nginx"
    ssh "$VPS" "nginx -t && systemctl reload nginx"
    log_ok "nginx перезагружен"
}

deploy_status() {
    echo -e "\n${BLUE}━━━ VPS Status ━━━${NC}"
    ssh "$VPS" "
        echo '── Nginx:'
        systemctl is-active nginx
        echo '── PHP-FPM:'
        systemctl is-active php8.3-fpm
        echo '── PM2:'
        pm2 jlist 2>/dev/null | python3 -c \"import sys,json; procs=json.load(sys.stdin); [print(f'  {p[\\\"name\\\"]}: {p[\\\"pm2_env\\\"][\\\"status\\\"]}') for p in procs]\" 2>/dev/null || echo '  (pm2 не запущен)'
        echo '── Диск:'
        df -h / | tail -1 | awk '{print \"  \" \$3 \"/\" \$2 \" (\" \$5 \" used)\"}'
        echo '── RAM:'
        free -h | awk '/Mem/{print \"  \" \$3 \"/\" \$2 \" used\"}'
        echo '── Uptime:'
        uptime -p
    "
}

# ─── MAIN ───────────────────────────────────────────────────

case "${1:-status}" in
    tvorim)
        if [ "${2:-}" = "page" ] && [ -n "${3:-}" ]; then
            deploy_tvorim_page "$3" "${4:-$3}"
        else
            deploy_tvorim
        fi
        ;;
    bot)     deploy_bot ;;
    nginx)   deploy_nginx ;;
    status)  deploy_status ;;
    *)
        echo "Использование:"
        echo "  deploy.sh tvorim          — деплой темы Творим"
        echo "  deploy.sh tvorim page X   — деплой одной страницы"
        echo "  deploy.sh bot             — деплой TG-бота"
        echo "  deploy.sh nginx           — перезагрузка nginx"
        echo "  deploy.sh status          — статус VPS"
        exit 1
        ;;
esac

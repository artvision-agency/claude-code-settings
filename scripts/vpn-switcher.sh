#!/bin/bash
# VPN Auto-Switcher — переключает VPN при потере соединения
# Участники: Hiddify, v2RayTun, Hiddify 2 (VPN Plus), SSH-туннель через Timeweb
# Исключены: ЧебурНет

set -uo pipefail

# ─── Конфигурация ───────────────────────────────────────────
TIMEOUT=20          # секунд на проверку соединения
CHECK_INTERVAL=5    # секунд между проверками при работающем VPN
TEST_URLS=(
    "https://www.google.com"
    "https://api.ipify.org"
    "https://1.1.1.1"
)
SSH_HOST="vps"                    # SSH alias из ~/.ssh/config
SSH_SOCKS_PORT=1080
SSH_PID_FILE="/tmp/vpn-switcher-ssh.pid"
LOG_FILE="/tmp/vpn-switcher.log"

# ─── Цвета ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─── VPN провайдеры (порядок = приоритет) ───────────────────
# Формат: "тип|идентификатор|название"
VPNS=(
    "nc|Hiddify|Hiddify"
    "nc|v2RayTun|v2RayTun"
    "nc|Hiddify 2|Hiddify 2 (VPN Plus)"
    "ssh|vps|SSH Timeweb (80.90.181.152)"
)

# ─── Логирование ────────────────────────────────────────────
log() {
    local msg="[$(date '+%H:%M:%S')] $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

# ─── Проверка интернета ─────────────────────────────────────
check_internet() {
    local proxy_flag=""
    # Если активен SSH-туннель, проверяем через SOCKS
    if is_ssh_tunnel_active; then
        proxy_flag="--proxy socks5h://127.0.0.1:${SSH_SOCKS_PORT}"
    fi

    for url in "${TEST_URLS[@]}"; do
        if curl -s -o /dev/null -w "" --connect-timeout 5 --max-time 10 $proxy_flag "$url" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

# ─── Проверка без прокси (прямое соединение) ────────────────
check_internet_direct() {
    for url in "${TEST_URLS[@]}"; do
        if curl -s -o /dev/null -w "" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

# ─── Network Connection (scutil) VPN ────────────────────────
get_nc_status() {
    local name="$1"
    scutil --nc status "$name" 2>/dev/null | head -1 || true
}

connect_nc() {
    local name="$1"
    log "${BLUE}Подключаю ${name}...${NC}"
    scutil --nc start "$name" 2>/dev/null

    # Ждём подключения (макс 15 сек)
    local waited=0
    while [ $waited -lt 15 ]; do
        local status
        status=$(get_nc_status "$name")
        if [ "$status" = "Connected" ]; then
            log "${GREEN}${name} — Connected${NC}"
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    log "${RED}${name} — не подключился за 15 сек${NC}"
    return 1
}

disconnect_nc() {
    local name="$1"
    log "${YELLOW}Отключаю ${name}...${NC}"
    scutil --nc stop "$name" 2>/dev/null
    sleep 1
}

# ─── SSH SOCKS туннель ──────────────────────────────────────
is_ssh_tunnel_active() {
    if [ -f "$SSH_PID_FILE" ]; then
        local pid
        pid=$(cat "$SSH_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

connect_ssh() {
    log "${BLUE}Запускаю SSH SOCKS-прокси через Timeweb...${NC}"
    # Убиваем старый туннель если есть
    disconnect_ssh 2>/dev/null

    ssh -D "$SSH_SOCKS_PORT" -f -N -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "$SSH_HOST" 2>/dev/null
    local ssh_pid=$!

    # Находим PID форкнутого ssh
    sleep 1
    local pid
    pid=$(pgrep -f "ssh -D ${SSH_SOCKS_PORT}.*${SSH_HOST}" | head -1)
    if [ -n "$pid" ]; then
        echo "$pid" > "$SSH_PID_FILE"
        log "${GREEN}SSH туннель активен (PID: ${pid}, SOCKS: 127.0.0.1:${SSH_SOCKS_PORT})${NC}"

        # Устанавливаем системный SOCKS-прокси
        networksetup -setsocksfirewallproxy Wi-Fi 127.0.0.1 "$SSH_SOCKS_PORT" 2>/dev/null
        networksetup -setsocksfirewallproxystate Wi-Fi on 2>/dev/null
        return 0
    fi

    log "${RED}SSH туннель не запустился${NC}"
    return 1
}

disconnect_ssh() {
    if [ -f "$SSH_PID_FILE" ]; then
        local pid
        pid=$(cat "$SSH_PID_FILE")
        kill "$pid" 2>/dev/null
        rm -f "$SSH_PID_FILE"
    fi
    # Также убиваем по паттерну
    pkill -f "ssh -D ${SSH_SOCKS_PORT}" 2>/dev/null || true

    # Отключаем системный SOCKS
    networksetup -setsocksfirewallproxystate Wi-Fi off 2>/dev/null
    log "${YELLOW}SSH туннель остановлен${NC}"
}

# ─── Универсальные обёртки ──────────────────────────────────
connect_vpn() {
    local type="$1"
    local id="$2"

    case "$type" in
        nc)  connect_nc "$id" ;;
        ssh) connect_ssh ;;
    esac
}

disconnect_vpn() {
    local type="$1"
    local id="$2"

    case "$type" in
        nc)  disconnect_nc "$id" ;;
        ssh) disconnect_ssh ;;
    esac
}

disconnect_all() {
    for vpn in "${VPNS[@]}"; do
        IFS='|' read -r type id name <<< "$vpn"
        disconnect_vpn "$type" "$id" 2>/dev/null
    done
}

# ─── Показать текущий IP ────────────────────────────────────
show_ip() {
    local ip
    ip=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo "не определён")
    log "${CYAN}Текущий IP: ${ip}${NC}"
}

# ─── Найти рабочий VPN ─────────────────────────────────────
find_working_vpn() {
    local current_index=${1:--1}

    for i in "${!VPNS[@]}"; do
        # Пропускаем текущий (уже не работает)
        if [ "$i" -eq "$current_index" ] 2>/dev/null; then
            continue
        fi

        IFS='|' read -r type id name <<< "${VPNS[$i]}"
        log "\n${CYAN}━━━ Пробую: ${name} ━━━${NC}"

        # Отключаем всё перед подключением нового
        disconnect_all

        if connect_vpn "$type" "$id"; then
            # Ждём стабилизации
            sleep 2

            # Проверяем интернет
            log "Проверяю соединение (${TIMEOUT} сек таймаут)..."
            local start_time
            start_time=$(date +%s)
            local connected=false

            while true; do
                local elapsed=$(( $(date +%s) - start_time ))
                if [ "$elapsed" -ge "$TIMEOUT" ]; then
                    break
                fi

                if check_internet; then
                    connected=true
                    break
                fi
                sleep 2
            done

            if $connected; then
                log "${GREEN}✓ ${name} — РАБОТАЕТ!${NC}"
                show_ip
                echo "$i" > /tmp/vpn-switcher-current.idx
                return 0
            else
                log "${RED}✗ ${name} — нет интернета за ${TIMEOUT} сек${NC}"
                disconnect_vpn "$type" "$id"
            fi
        fi
    done

    log "${RED}⚠ Ни один VPN не работает!${NC}"
    return 1
}

# ─── Обработка Ctrl+C ──────────────────────────────────────
cleanup() {
    echo ""
    log "${YELLOW}Останавливаю VPN-switcher...${NC}"
    # НЕ отключаем текущий VPN — оставляем работающее соединение
    rm -f /tmp/vpn-switcher-current.idx
    exit 0
}
trap cleanup SIGINT SIGTERM

# ─── Главный цикл ──────────────────────────────────────────
main() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════╗"
    echo "║       VPN Auto-Switcher v1.0             ║"
    echo "║  Таймаут: ${TIMEOUT}с | Проверка: ${CHECK_INTERVAL}с         ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"

    log "Провайдеры (по приоритету):"
    for i in "${!VPNS[@]}"; do
        IFS='|' read -r type id name <<< "${VPNS[$i]}"
        log "  $((i+1)). ${name} [${type}]"
    done
    echo ""

    # Проверяем текущее соединение
    log "Проверяю текущее соединение..."
    if check_internet_direct; then
        log "${GREEN}Интернет уже работает!${NC}"
        show_ip

        # Определяем текущий VPN
        for i in "${!VPNS[@]}"; do
            IFS='|' read -r type id name <<< "${VPNS[$i]}"
            if [ "$type" = "nc" ]; then
                local status
                status=$(get_nc_status "$id")
                if [ "$status" = "Connected" ]; then
                    log "Активный VPN: ${name}"
                    echo "$i" > /tmp/vpn-switcher-current.idx
                    break
                fi
            fi
        done
    else
        log "${YELLOW}Интернет не работает — ищу рабочий VPN...${NC}"
        find_working_vpn
    fi

    # Мониторинг
    log "\n${CYAN}Мониторинг соединения (Ctrl+C для выхода)...${NC}"
    local fail_count=0

    while true; do
        sleep "$CHECK_INTERVAL"

        if check_internet; then
            if [ $fail_count -gt 0 ]; then
                log "${GREEN}Соединение восстановилось${NC}"
                fail_count=0
            fi
        else
            fail_count=$((fail_count + 1))
            local total_wait=$((fail_count * CHECK_INTERVAL))
            log "${YELLOW}Нет соединения (${total_wait}с)...${NC}"

            if [ "$total_wait" -ge "$TIMEOUT" ]; then
                log "${RED}Таймаут ${TIMEOUT}с — переключаю VPN!${NC}"
                local current_idx=-1
                [ -f /tmp/vpn-switcher-current.idx ] && current_idx=$(cat /tmp/vpn-switcher-current.idx)
                find_working_vpn "$current_idx"
                fail_count=0
            fi
        fi
    done
}

# ─── Режимы запуска ─────────────────────────────────────────
case "${1:-}" in
    --status)
        echo "VPN сервисы:"
        for vpn in "${VPNS[@]}"; do
            IFS='|' read -r type id name <<< "$vpn"
            if [ "$type" = "nc" ]; then
                status=$(get_nc_status "$id")
                echo "  $name: $status"
            elif [ "$type" = "ssh" ]; then
                if is_ssh_tunnel_active; then
                    echo "  $name: Active (PID: $(cat "$SSH_PID_FILE"))"
                else
                    echo "  $name: Inactive"
                fi
            fi
        done
        echo ""
        echo -n "Текущий IP: "
        curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo "не определён"
        echo ""
        ;;
    --stop)
        echo "Останавливаю все VPN..."
        disconnect_all
        echo "Готово"
        ;;
    --next)
        echo "Переключаю на следующий VPN..."
        current_idx=-1
        [ -f /tmp/vpn-switcher-current.idx ] && current_idx=$(cat /tmp/vpn-switcher-current.idx)
        find_working_vpn "$current_idx"
        ;;
    --help|-h)
        echo "VPN Auto-Switcher"
        echo ""
        echo "Использование:"
        echo "  vpn-switcher.sh          — запуск мониторинга (основной режим)"
        echo "  vpn-switcher.sh --status — показать статус VPN"
        echo "  vpn-switcher.sh --next   — переключить на следующий VPN"
        echo "  vpn-switcher.sh --stop   — отключить все VPN"
        echo ""
        echo "Переменные окружения:"
        echo "  VPN_TIMEOUT=30       — таймаут (сек, по умолчанию 20)"
        echo "  VPN_CHECK=10         — интервал проверки (сек, по умолчанию 5)"
        ;;
    *)
        # Поддержка env переменных для настройки
        [ -n "${VPN_TIMEOUT:-}" ] && TIMEOUT="$VPN_TIMEOUT"
        [ -n "${VPN_CHECK:-}" ] && CHECK_INTERVAL="$VPN_CHECK"
        main
        ;;
esac

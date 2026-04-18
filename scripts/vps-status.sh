#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# vps-status.sh — Быстрая проверка VPS
# 0 токенов Claude.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

VPS="root@80.90.181.152"

ssh "$VPS" "
echo '═══ VPS 80.90.181.152 (Timeweb) ═══'
echo ''
echo '── Сервисы:'
printf '  nginx:    %s\n' \$(systemctl is-active nginx)
printf '  php-fpm:  %s\n' \$(systemctl is-active php8.3-fpm)
printf '  mysql:    %s\n' \$(systemctl is-active mysql 2>/dev/null || echo 'n/a')

echo ''
echo '── PM2:'
pm2 jlist 2>/dev/null | python3 -c \"
import sys,json
try:
    procs=json.load(sys.stdin)
    for p in procs:
        print(f'  {p[\\\"name\\\"]}: {p[\\\"pm2_env\\\"][\\\"status\\\"]} (cpu: {p[\\\"monit\\\"][\\\"cpu\\\"]}%, mem: {p[\\\"monit\\\"][\\\"memory\\\"]//1024//1024}MB)')
except: print('  (нет процессов)')
\" 2>/dev/null

echo ''
echo '── Ресурсы:'
echo -n '  Диск: '; df -h / | tail -1 | awk '{print \$3 \"/\" \$2 \" (\" \$5 \")\"}'
echo -n '  RAM:  '; free -h | awk '/Mem/{print \$3 \"/\" \$2}'
echo -n '  Load: '; cat /proc/loadavg | awk '{print \$1, \$2, \$3}'
echo -n '  Up:   '; uptime -p

echo ''
echo '── SSL:'
for domain in tvorim.artvision.pro artvision.pro; do
    exp=\$(echo | openssl s_client -servername \$domain -connect \$domain:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ -n \"\$exp\" ]; then
        printf '  %s: %s\n' \$domain \"\$exp\"
    fi
done

echo ''
echo '── Сайты (HTTP status):'
for url in https://tvorim.artvision.pro/ https://artvision.pro/; do
    code=\$(curl -sL -o /dev/null -w '%{http_code}' \"\$url\" --max-time 5 2>/dev/null || echo 'timeout')
    printf '  %s → %s\n' \"\$url\" \"\$code\"
done
"

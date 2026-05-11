"""orm-pulse config — общие константы (ROOT, VPS, paths).

Вынесено из command-center.py при refactoring 2026-05-10 (security audit H2).
"""
from pathlib import Path

ROOT = Path("/Users/antonk/artvision-data")

# VPS deploy
VPS_USER = "root"
VPS_HOST = "80.90.181.152"
VPS_DIR = "/var/www/artvision/orm-command-center"
PUBLIC_BASE = "https://artvision.pro/orm-command-center"

# Tmp paths
TMP_ORM = Path("/tmp/orm-pulse")

# Sanity floors
MIN_ITEMS_STABLE = 500  # Q3+Q5 — sanity floor для live-reviews crawl
RECONCILIATION_WINDOW_DAYS = 7  # Q2 — окно для «removed»
PARTIAL_THRESHOLD = 3  # Q5 — N partials подряд → auto-stop
PACE_THRESHOLD_PER_DAY = 0.5  # Q10 — алёрт темпа
DASHBOARD_STALE_THRESHOLD_HOURS = 2  # Q11 — watchdog

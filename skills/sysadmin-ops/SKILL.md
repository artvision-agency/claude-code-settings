---
name: sysadmin-ops
description: "Infrastructure operations skill for monitoring servers, validating tokens, and managing backups. Triggers: /infra-status, /token-check, /backup-now"
disable-model-invocation: true
argument-hint: "[/infra-status | /token-check | /backup-now]"
---

# SysAdmin Operations Skill

Operations commands for Artvision infrastructure management.

## Commands

### /infra-status
Full infrastructure status report.

**Usage:** `/infra-status` or "статус инфраструктуры"

**Actions:**
1. Check VPS connectivity (ping + SSH)
2. Validate all API endpoints
3. Check token expiration status
4. Report last backup time
5. Output formatted status report

**Script:**
```bash
python3 /Users/antonk/devops-agent/monitors/health.py --report
```

---

### /token-check
Validate all tokens and check expiration.

**Usage:** `/token-check` or "проверь токены"

**Actions:**
1. Load tokens.json
2. Validate each token against its API
3. Check expiration dates
4. Alert if any token expires within 7 days
5. Output validation report

**Script:**
```bash
python3 /Users/antonk/devops-agent/monitors/token_monitor.py --validate
```

---

### /backup-now
Run immediate backup of all repositories.

**Usage:** `/backup-now` or "сделай бэкап"

**Actions:**
1. Backup Git repos to Google Drive
2. Create encrypted token backup
3. Dump Supabase database (if enabled)
4. Verify backup integrity
5. Report results

**Script:**
```bash
python3 /Users/antonk/devops-agent/backup/backup_controller.py --run
```

---

### /security-audit (TODO — скрипт не создан)

> **Статус:** Скрипт `security_audit.py` ещё не реализован.
> Когда будет готов: `devops-agent/secrets/security_audit.py`

**Планируемые действия:**
1. Check token permissions (overprivileged?)
2. Verify encrypted backups exist
3. Check SSH key security
4. Scan for exposed secrets in code

---

## Quick Reference

| Command | Описание | Статус |
|---------|----------|--------|
| `/infra-status` | Полный статус | ✅ Работает |
| `/token-check` | Проверка токенов | ✅ Работает |
| `/backup-now` | Ручной бэкап | ✅ Работает |
| `/security-audit` | Аудит безопасности | ⏳ TODO |

## Configuration

- **Config file:** `/Users/antonk/devops-agent/config/settings.yaml`
- **Tokens:** `/Users/antonk/artvision-data/tokens.json`
- **Logs:** `/Users/antonk/devops-agent/logs/`

## Alert Destinations

- **Telegram:** @avportal_bot → Admin 161261562
- **Log file:** `/Users/antonk/devops-agent/logs/sysadmin.log`

## Related

- Agent: `sysadmin-orchestrator`
- Project: `/Users/antonk/devops-agent/`

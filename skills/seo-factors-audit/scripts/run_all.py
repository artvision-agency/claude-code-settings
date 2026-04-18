#!/usr/bin/env python3
"""
SEO Factors Audit — Orchestrator

Запускает 4 модуля аудита (commercial / text / link / behavioral)
последовательно или параллельно и собирает итоговый dashboard.

CLI:
    python3 run_all.py --domain avto.world --client avtoworld
    python3 run_all.py --domain avto.world --client avtoworld --parallel
    python3 run_all.py --domain avto.world --client avtoworld \
        --competitors site2.ru,site3.ru --parallel \
        --weights comm=30,text=25,link=25,behav=20

Выход: reports/<client>/seo-audit-YYYY-MM-DD.html (+ 4 модульных отчёта).

Exit codes:
    0 — успех (хотя бы 1 модуль отработал)
    1 — все 4 модуля упали
    2 — ошибка аргументов
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Путь к tokens.json для автоопределения параметров модулей
TOKENS_PATH = Path.home() / "artvision-data" / "tokens.json"

# ============================================================
# Константы
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SKILLS_DIR = SKILL_ROOT.parent  # /Users/antonk/.claude/skills
REPORTS_DIR = SKILL_ROOT / "reports"
LOGS_DIR = SKILL_ROOT / "logs"

MODULES: dict[str, dict[str, Any]] = {
    "commercial": {
        "label": "Коммерческие факторы",
        "path": SKILLS_DIR / "commercial-factors-audit",
        "default_weight": 25,
    },
    "text": {
        "label": "Текстовые факторы",
        "path": SKILLS_DIR / "text-factors-audit",
        "default_weight": 25,
    },
    "link": {
        "label": "Ссылочные факторы",
        "path": SKILLS_DIR / "link-factors-audit",
        "default_weight": 25,
    },
    "behavioral": {
        "label": "Поведенческие факторы",
        "path": SKILLS_DIR / "behavioral-factors-audit",
        "default_weight": 25,
    },
}


# ============================================================
# Модели
# ============================================================
@dataclass
class ModuleResult:
    module: str
    label: str
    ok: bool
    json_path: Path | None = None
    html_path: Path | None = None
    score: float = 0.0
    error: str | None = None
    duration_s: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Автоопределение параметров модулей из tokens.json
# ============================================================
def load_tokens() -> dict[str, Any]:
    """Загружает tokens.json. Возвращает пустой dict при ошибке."""
    if not TOKENS_PATH.exists():
        return {}
    try:
        with open(TOKENS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def auto_detect_counter_id(tokens: dict[str, Any], domain: str) -> str | None:
    """Определяет counter_id Яндекс.Метрики по домену из tokens.json.

    Логика совпадает с behavioral-factors-audit/scripts/audit.py:
    сравнивает slug домена (без точек/дефисов) с ключами в yandex.metrika,
    пропуская служебные поля (token, client_id, client_secret, account).
    """
    metrika = tokens.get("yandex", {}).get("metrika", {})
    domain_clean = domain.replace("https://", "").replace("http://", "").rstrip("/").lower()
    slug = domain_clean.replace(".", "").replace("-", "")
    for key, val in metrika.items():
        if key.startswith("_") or key in ("token", "client_id", "client_secret", "account"):
            continue
        if not isinstance(val, (str, int)):
            continue
        key_clean = key.lower().replace("_counter", "").replace("_", "")
        if key_clean in slug or slug in key_clean:
            return str(val)
    return None


def build_module_extra_args(
    module_name: str,
    domain: str,
    tokens: dict[str, Any],
    counter_id: str | None = None,
    competitors: list[str] | None = None,
) -> list[str]:
    """Формирует дополнительные CLI-аргументы для конкретного модуля.

    Каждый модуль сам загружает токены, но оркестратор передаёт
    параметры, которые может автоопределить: counter-id, competitors.
    """
    extra: list[str] = []

    if module_name == "behavioral":
        cid = counter_id or auto_detect_counter_id(tokens, domain)
        if cid:
            extra.append(f"--counter-id={cid}")

    elif module_name == "link":
        if competitors:
            extra.append(f"--competitors={','.join(competitors)}")

    return extra


# ============================================================
# Логирование
# ============================================================
def setup_logger(log_file: Path) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("seo-factors-audit")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


# ============================================================
# Запуск модуля
# ============================================================
def run_module(
    module_name: str,
    module_cfg: dict[str, Any],
    domain: str,
    client: str,
    date_str: str,
    out_dir: Path,
    extra_args: list[str] | None = None,
) -> ModuleResult:
    """Запускает один модуль аудита. Graceful skip если модуль не установлен."""
    label = module_cfg["label"]
    module_path: Path = module_cfg["path"]
    start = time.time()

    audit_script = module_path / "scripts" / "audit.py"
    report_script = module_path / "scripts" / "report.py"

    if not audit_script.exists():
        return ModuleResult(
            module=module_name,
            label=label,
            ok=False,
            error=f"модуль не установлен: {audit_script} не найден",
            duration_s=time.time() - start,
        )

    json_path = out_dir / f"{module_name}-{date_str}.json"
    html_path = out_dir / f"{module_name}-{date_str}.html"

    # Выбор Python — предпочитаем venv скилла, иначе системный
    py_candidates = [
        module_path / "venv" / "bin" / "python",
        module_path / ".venv" / "bin" / "python",
        SKILL_ROOT / "venv" / "bin" / "python",
    ]
    python_bin = next((str(p) for p in py_candidates if p.exists()), sys.executable)

    try:
        # 1. audit
        cmd_audit = [
            python_bin,
            str(audit_script),
            f"https://{domain}",
            f"--output={json_path}",
            *(extra_args or []),
        ]
        r = subprocess.run(
            cmd_audit,
            capture_output=True,
            text=True,
            timeout=900,
            cwd=module_path,
        )
        if r.returncode != 0:
            return ModuleResult(
                module=module_name,
                label=label,
                ok=False,
                error=f"audit.py exit={r.returncode}: {r.stderr[:500]}",
                duration_s=time.time() - start,
            )

        # 2. report
        if report_script.exists():
            cmd_report = [
                python_bin,
                str(report_script),
                str(json_path),
                f"--output={html_path}",
                f"--client-name={client}",
            ]
            subprocess.run(
                cmd_report,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=module_path,
            )

        # 3. Читаем JSON для sweep-данных
        data: dict[str, Any] = {}
        score = 0.0
        if json_path.exists():
            try:
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                score = float(data.get("score", 0))
                # Fallback: если score не задан — считаем из factors
                if score == 0 and data.get("factors"):
                    score = compute_score(data["factors"])
            except (json.JSONDecodeError, ValueError) as e:
                return ModuleResult(
                    module=module_name,
                    label=label,
                    ok=False,
                    error=f"невалидный JSON: {e}",
                    duration_s=time.time() - start,
                )

        return ModuleResult(
            module=module_name,
            label=label,
            ok=True,
            json_path=json_path,
            html_path=html_path if html_path.exists() else None,
            score=score,
            data=data,
            duration_s=time.time() - start,
        )

    except subprocess.TimeoutExpired:
        return ModuleResult(
            module=module_name,
            label=label,
            ok=False,
            error="таймаут (>15 мин)",
            duration_s=time.time() - start,
        )
    except Exception as e:  # noqa: BLE001
        return ModuleResult(
            module=module_name,
            label=label,
            ok=False,
            error=f"{type(e).__name__}: {e}",
            duration_s=time.time() - start,
        )


def compute_score(factors: list[dict[str, Any]]) -> float:
    """score = sum(weight * passed) / sum(weight) * 100"""
    total_w = 0.0
    pass_w = 0.0
    for f in factors:
        w = float(f.get("weight", 1))
        total_w += w
        if f.get("passed") is True or f.get("status") == "pass":
            pass_w += w
    if total_w == 0:
        return 0.0
    return round(pass_w / total_w * 100, 1)


# ============================================================
# Парсинг весов
# ============================================================
def parse_weights(s: str | None) -> dict[str, float]:
    """comm=30,text=25,link=25,behav=20 → {'commercial': 30, ...}"""
    alias = {"comm": "commercial", "text": "text", "link": "link", "behav": "behavioral"}
    weights = {m: MODULES[m]["default_weight"] for m in MODULES}
    if not s:
        return weights
    for pair in s.split(","):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        key = alias.get(k.strip(), k.strip())
        if key in weights:
            try:
                weights[key] = float(v)
            except ValueError:
                pass
    return weights


# ============================================================
# Main
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="SEO Factors Audit — оркестратор")
    parser.add_argument("--domain", required=True, help="avto.world (без https://)")
    parser.add_argument("--client", required=True, help="slug клиента для папки отчётов")
    parser.add_argument("--competitors", default="", help="site2.ru,site3.ru")
    parser.add_argument("--parallel", action="store_true", help="Параллельный запуск модулей")
    parser.add_argument("--weights", default=None, help="comm=30,text=25,link=25,behav=20")
    parser.add_argument("--counter-id", default=None,
                        help="Яндекс.Метрика counter_id (авто из tokens.json если не указан)")
    parser.add_argument("--modules", default="commercial,text,link,behavioral",
                        help="Список модулей через запятую")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = REPORTS_DIR / args.client
    out_dir.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"seo-audit-{date_str}.log"
    log = setup_logger(log_file)
    log.info("=" * 60)
    log.info("SEO Factors Audit — старт")
    log.info("domain=%s client=%s parallel=%s", args.domain, args.client, args.parallel)

    selected = [m.strip() for m in args.modules.split(",") if m.strip() in MODULES]
    if not selected:
        log.error("нет валидных модулей в --modules")
        return 2

    weights = parse_weights(args.weights)
    log.info("weights: %s", weights)

    # Загрузка tokens.json для автоопределения параметров модулей
    tokens = load_tokens()
    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]
    counter_id: str | None = getattr(args, "counter_id", None)

    # Предварительный расчёт extra_args для каждого модуля
    module_extra: dict[str, list[str]] = {}
    for m in selected:
        extra = build_module_extra_args(
            module_name=m,
            domain=args.domain,
            tokens=tokens,
            counter_id=counter_id,
            competitors=competitors,
        )
        module_extra[m] = extra
        if extra:
            log.info("[%s] extra args: %s", m, extra)

    results: list[ModuleResult] = []

    if args.parallel:
        log.info("запуск %d модулей параллельно (ProcessPoolExecutor)", len(selected))
        with ProcessPoolExecutor(max_workers=min(4, len(selected))) as pool:
            futures = {
                pool.submit(
                    run_module, m, MODULES[m], args.domain, args.client,
                    date_str, out_dir, module_extra.get(m, []),
                ): m
                for m in selected
            }
            for fut in as_completed(futures):
                res = fut.result()
                results.append(res)
                log.info("[%s] ok=%s score=%s t=%.1fs err=%s",
                         res.module, res.ok, res.score, res.duration_s, res.error)
    else:
        log.info("последовательный запуск %d модулей", len(selected))
        for m in selected:
            res = run_module(
                m, MODULES[m], args.domain, args.client,
                date_str, out_dir, module_extra.get(m, []),
            )
            results.append(res)
            log.info("[%s] ok=%s score=%s t=%.1fs err=%s",
                     res.module, res.ok, res.score, res.duration_s, res.error)

    # Сводный dashboard
    dashboard_path = out_dir / f"seo-audit-{date_str}.html"
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from merge_report import build_dashboard  # type: ignore[import-not-found]  # noqa: E402

    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]

    build_dashboard(
        results=results,
        domain=args.domain,
        client=args.client,
        date_str=date_str,
        weights=weights,
        competitors=competitors,
        output_path=dashboard_path,
        log=log,
    )

    ok_count = sum(1 for r in results if r.ok)
    log.info("=" * 60)
    log.info("Готово. Успешно %d/%d модулей. Dashboard: %s",
             ok_count, len(results), dashboard_path)

    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    # Добавим scripts/ в path для относительного импорта merge_report
    sys.path.insert(0, str(SCRIPT_DIR))
    sys.exit(main())

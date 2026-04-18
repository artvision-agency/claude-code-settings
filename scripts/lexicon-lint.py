#!/usr/bin/env python3
"""Lexicon linter — проверяет текст против global + per-client правил.

Usage:
    lexicon-lint.py --content <file|-> --path <target_path> [--json]

Returns exit 0 always (warnings), exit 2 if critical (для блокировки хука).
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(json.dumps({"error": "pyyaml not installed"}))
    sys.exit(0)

GLOBAL_RULES = Path.home() / ".claude/rules/lexicon-global.yaml"
ARTVISION = Path.home() / "artvision-data"


def load_yaml(p: Path):
    if not p.exists():
        return {}
    try:
        return yaml.safe_load(p.read_text()) or {}
    except Exception:
        return {}


def detect_client(target_path: str) -> str | None:
    m = re.search(r"/clients/([^/]+)/", target_path)
    return m.group(1) if m else None


def detect_scope(target_path: str) -> set[str]:
    scopes = set()
    p = target_path.lower()
    if "/kp/" in p or "kp_" in p or "_kp." in p or p.endswith("-kp.html"):
        scopes.update({"kp", "public"})
    if "/presale/" in p:
        scopes.add("presale")
    if "/clients/" in p:
        scopes.add("client_page")
    if "baburov" in p:
        scopes.add("baburov")
    if "/content/" in p or "/blog/" in p:
        scopes.add("content")
    return scopes


def scope_matches(rule_scope, active_scopes) -> bool:
    if not rule_scope:
        return True  # правило без scope — везде
    return bool(set(rule_scope) & active_scopes)


def lint(content: str, target_path: str) -> list[dict]:
    rules = load_yaml(GLOBAL_RULES)
    client = detect_client(target_path)
    if client:
        client_rules = load_yaml(ARTVISION / f"clients/{client}/lexicon.yaml")
        for key in ("forbidden", "replace", "require"):
            rules[key] = (rules.get(key) or []) + (client_rules.get(key) or [])

    scopes = detect_scope(target_path)
    findings = []

    for rule in rules.get("forbidden", []) or []:
        if not scope_matches(rule.get("scope"), scopes):
            continue
        pat = rule.get("pattern")
        if not pat:
            continue
        for m in re.finditer(pat, content):
            findings.append({
                "type": "forbidden",
                "severity": rule.get("severity", "warning"),
                "match": m.group(0),
                "reason": rule.get("reason", ""),
            })

    for rule in rules.get("replace", []) or []:
        if not scope_matches(rule.get("scope"), scopes):
            continue
        pat = rule.get("from")
        if not pat:
            continue
        excl = rule.get("exclude_context") or []
        for m in re.finditer(pat, content):
            snippet_start = max(0, m.start() - 30)
            snippet_end = min(len(content), m.end() + 30)
            ctx = content[snippet_start:snippet_end]
            if any(e in ctx for e in excl):
                continue
            findings.append({
                "type": "replace",
                "severity": rule.get("severity", "warning"),
                "match": m.group(0),
                "suggest": rule.get("to", ""),
                "reason": rule.get("reason", ""),
            })

    for rule in rules.get("require", []) or []:
        if not scope_matches(rule.get("scope"), scopes):
            continue
        pat = rule.get("pattern")
        if not pat:
            continue
        found = len(re.findall(pat, content))
        if found < int(rule.get("min_count", 1)):
            findings.append({
                "type": "require_missing",
                "severity": rule.get("severity", "warning"),
                "found": found,
                "needed": rule.get("min_count", 1),
                "reason": rule.get("reason", ""),
            })

    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", required=True, help="файл или '-' для stdin")
    ap.add_argument("--path", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    content = sys.stdin.read() if args.content == "-" else Path(args.content).read_text()
    findings = lint(content, args.path)

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        if not findings:
            sys.exit(0)
        crit = [f for f in findings if f.get("severity") == "critical"]
        warn = [f for f in findings if f.get("severity") != "critical"]
        if crit:
            print(f"🚫 LEXICON CRITICAL ({len(crit)}):")
            for f in crit:
                print(f"  • [{f['type']}] {f.get('match','')} — {f['reason']}")
        if warn:
            print(f"⚠️  LEXICON WARN ({len(warn)}):")
            for f in warn[:10]:
                print(f"  • [{f['type']}] {f.get('match','')} — {f['reason']}")

    crit_count = sum(1 for f in findings if f.get("severity") == "critical")
    sys.exit(2 if crit_count else 0)


if __name__ == "__main__":
    main()

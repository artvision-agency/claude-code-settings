---
name: ext-seo-crawl4ai
description: External LLM-friendly web crawler (unclecode/crawl4ai, 66K⭐ Apache-2.0). Crawls site and outputs markdown ready for LLM ingestion. Supports JS-rendering, async, hooks. Use for GEO/AI-visibility audits (как ChatGPT/Perplexity видят сайт), SPA-scraping, конкурент-research, LLM-ingestion для /tfidf-clustering. Triggers — 'crawl4ai', 'llm crawler', 'llm friendly crawl', 'geo crawl', 'aivisibility crawl', 'ext-seo-crawl4ai'.
---

# ext-seo-crawl4ai — LLM-friendly web crawler

**Upstream:** github.com/artvision-agency/crawl4ai ← unclecode/crawl4ai (66K⭐, Apache-2.0)
**Category:** SEO / Crawl
**Use case:** crawl сайта → markdown output готовый под подачу в LLM. JS-rendering для SPA.

## Когда вызывать

- GEO-аудит клиента (как видит сайт ChatGPT, Perplexity, Claude)
- Парсинг конкурентов под `/cons` стратсессию
- Scraping для `/tfidf-clustering` (русскоязычные сайты с JS-render)
- Когда `hybrid-seo-audit.py` пропускает orphan-страницы

## Как пользоваться

```bash
gh repo clone artvision-agency/crawl4ai ~/forks/crawl4ai
cd ~/forks/crawl4ai && pip install -e .
# CLI:
crwl https://<client-site>/ --output markdown --depth 2 > /tmp/crawl-output.md
```

## A/B vs наши tools

- vs `hybrid-seo-audit.py` — coverage (orphan-страницы), token-efficient output
- Метрика: страниц найдено, время crawl, размер markdown под LLM
- Кейс: spb-kursy (где SF не нашёл /poleznyie-stati/ orphan секцию)

## Связанные

- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/01-seo-crawl.md`
- A/B benchmark output: `~/artvision-data/benchmarks/seo-crawl4ai-<date>-<client>.md`

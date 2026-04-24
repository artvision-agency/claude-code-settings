"""
LLM Consilium — MCP-сервер для подключения внешних LLM в Claude Code.

Возможности:
1. ask_model — спросить конкретную модель
2. ask_auto — авто-роутинг по типу задачи к лучшей модели
3. round_table — параллельный опрос нескольких моделей + синтез мастер-моделью
4. list_models / check_balance — служебные

Маршрутизация:
- Groq (FREE): llama-70b, qwen3-32b, kimi-k2, llama-scout, gpt-oss-groq
- OpenRouter (FREE): hermes-405b, qwen3-coder, qwen3-80b, nemotron-120b,
                      gpt-oss-120b, llama-70b-or, gemma4
- Google (GEO-BLOCKED): gemini-flash, gemini-pro

Обновлено: 2026-04-09
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from fastmcp import FastMCP

# --- Config ---

TOKENS_PATH = os.path.expanduser("~/artvision-data/tokens.json")

MASTER_MODEL = "gpt-oss-groq"  # 120B reasoning, FREE on Groq — stable default
MASTER_FALLBACK = "llama"       # 70B fast fallback (Groq FREE)
# Upgrade path: set MASTER_MODEL="kimi-k2-thinking" or "deepseek-r1" when OR credits available


def get_tokens() -> dict:
    with open(TOKENS_PATH) as f:
        return json.load(f)


# --- Model registry ---

MODELS = {
    # === Groq (FREE, fast, low latency) ===
    "llama": {
        "provider": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "cost": "FREE",
        "strengths": ["general", "summarization", "creative", "russian"],
    },
    # kimi-k2 snatched from Groq (2026-04). Now only via OpenRouter (paid).
    "kimi-k2": {
        "provider": "openrouter",
        "model_id": "moonshotai/kimi-k2-thinking",
        "cost": "PAID (OR credits)",
        "strengths": ["reasoning", "logic", "synthesis", "code", "math"],
    },
    "kimi-k2-latest": {
        "provider": "openrouter",
        "model_id": "moonshotai/kimi-k2.6",
        "cost": "PAID (OR credits)",
        "strengths": ["latest", "reasoning", "long_context"],
    },
    "deepseek-r1": {
        "provider": "openrouter",
        "model_id": "deepseek/deepseek-r1-0528",
        "cost": "PAID (OR credits)",
        "strengths": ["reasoning", "synthesis", "master_synthesizer"],
    },
    "deepseek-v4-pro": {
        "provider": "deepseek",
        "model_id": "deepseek-v4-pro",
        "cost": "PAID (DeepSeek credits)",
        "strengths": ["reasoning", "cheap_than_OR"],
    },
    "deepseek-v4-flash": {
        "provider": "deepseek",
        "model_id": "deepseek-v4-flash",
        "cost": "PAID (DeepSeek credits)",
        "strengths": ["fast", "cheap"],
    },
    "qwen3": {
        "provider": "groq",
        "model_id": "qwen/qwen3-32b",
        "cost": "FREE",
        "strengths": ["analysis", "data", "structured", "multilingual", "thinking"],
    },
    "llama-scout": {
        "provider": "groq",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "cost": "FREE",
        "strengths": ["fast", "lightweight", "multimodal"],
    },
    "gpt-oss-groq": {
        "provider": "groq",
        "model_id": "openai/gpt-oss-120b",
        "cost": "FREE",
        "strengths": ["general", "instruction_following"],
    },

    # === OpenRouter FREE (higher latency, bigger models) ===
    "hermes-405b": {
        "provider": "openrouter",
        "model_id": "nousresearch/hermes-3-llama-3.1-405b:free",
        "cost": "FREE",
        "strengths": ["largest_free", "general", "creative", "reasoning"],
    },
    "qwen3-coder": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-coder:free",
        "cost": "FREE",
        "strengths": ["code", "480B_MoE", "architecture", "debugging"],
    },
    "qwen3-80b": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-next-80b-a3b-instruct:free",
        "cost": "FREE",
        "strengths": ["analysis", "data", "structured", "multilingual"],
    },
    "nemotron-120b": {
        "provider": "openrouter",
        "model_id": "nvidia/nemotron-3-super-120b-a12b:free",
        "cost": "FREE",
        "strengths": ["reasoning", "instruction_following", "nvidia"],
    },
    "gpt-oss": {
        "provider": "openrouter",
        "model_id": "openai/gpt-oss-120b:free",
        "cost": "FREE",
        "strengths": ["general", "openai_architecture"],
    },
    "gemma4": {
        "provider": "openrouter",
        "model_id": "google/gemma-4-31b-it:free",
        "cost": "FREE",
        "strengths": ["google", "compact", "fast"],
    },
    "llama-or": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.3-70b-instruct:free",
        "cost": "FREE",
        "strengths": ["general", "creative", "russian"],
    },
    "minimax": {
        "provider": "openrouter",
        "model_id": "minimax/minimax-m2.5:free",
        "cost": "FREE",
        "strengths": ["creative", "multilingual"],
    },

    # === xAI Grok ($25 signup credits) ===
    "grok-3": {
        "provider": "xai",
        "model_id": "grok-3",
        "cost": "CREDITS ($25 signup)",
        "strengths": ["reasoning", "creative", "analysis", "code"],
    },
    "grok-3-mini": {
        "provider": "xai",
        "model_id": "grok-3-mini",
        "cost": "CREDITS ($25 signup)",
        "strengths": ["fast", "reasoning", "cheap"],
    },

    # === Google (geo-blocked for RU accounts) ===
    "gemini-flash": {
        "provider": "google",
        "model_id": "gemini-2.0-flash",
        "cost": "FREE (geo-blocked)",
        "strengths": ["fast", "google_ecosystem"],
    },
    "gemini-pro": {
        "provider": "google",
        "model_id": "gemini-2.5-pro-preview-05-06",
        "cost": "FREE (geo-blocked)",
        "strengths": ["reasoning", "long_context"],
    },
}

# --- Auto-routing rules ---

ROUTE_RULES = [
    # (pattern, model, reason)
    (r"(?i)(код|code|python|javascript|typescript|функци|class |def |import |bug|баг|ошибк|debug|fix|рефактор|refactor)",
     "qwen3-coder", "код и дебаг → Qwen3 Coder 480B"),

    (r"(?i)(math|матем|формул|вычисл|calculat|уравнен|integral|derivative|статистик|statistic)",
     "kimi-k2", "математика → Kimi K2"),

    (r"(?i)(логик|logic|reasoning|рассужд|почему|why|сравни|compare|взвес|pros.?cons|за и против|анализ альтернатив|трейд.?офф)",
     "kimi-k2", "логика и рассуждения → Kimi K2"),

    (r"(?i)(данн|data|csv|json|таблиц|table|парс|pars|sql|query|запрос|database|бд|аналит|analyz|отчёт|report|metric|метрик)",
     "qwen3", "данные и аналитика → Qwen3 32B"),

    (r"(?i)(стратег|strateg|бизнес|business|roi|revenue|доход|план|plan|маркетинг|market|kpi|конкурент|competitor|growth|рост)",
     "hermes-405b", "бизнес-стратегия → Hermes 405B"),

    (r"(?i)(напиши текст|копирайт|copywrite|слоган|headline|заголовок|креатив|creative|идея|idea|придумай|brainstorm|контент|content)",
     "llama", "креатив и контент → Llama 70B"),

    (r"(?i)(перевод|translat|english|англ|франц|french|немец|german|испан|spanish)",
     "llama", "перевод и языки → Llama 70B"),

    (r"(?i)(seo|ключев|keyword|title|meta|description|h1|snippet|serp|позици|position|трафик|traffic)",
     "qwen3", "SEO → Qwen3 32B"),

    (r"(?i)(архитектур|architect|design.?pattern|microservice|микросервис|system.?design|schema)",
     "qwen3-coder", "архитектура → Qwen3 Coder 480B"),
]

DEFAULT_ROUTE = ("llama", "общий вопрос → Llama 70B")


def auto_route(prompt: str) -> tuple[str, str]:
    """Pick the best model based on prompt content."""
    for pattern, model, reason in ROUTE_RULES:
        if re.search(pattern, prompt):
            # Check if model is available
            cfg = MODELS.get(model, {})
            if cfg.get("provider") == "google":
                # Google geo-blocked, fallback
                return "llama", f"{reason} (Google geo-blocked, fallback → Llama)"
            return model, reason
    return DEFAULT_ROUTE


# --- Provider callers ---

PROVIDER_URLS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "xai": "https://api.x.ai/v1/chat/completions",
}


def get_provider_key(provider: str) -> str:
    """Get API key for a provider from tokens.json."""
    tokens = get_tokens()

    if provider == "groq":
        k = tokens.get("groq", {})
        return k.get("api_key", k) if isinstance(k, dict) else k

    if provider == "deepseek":
        k = tokens.get("deepseek", {})
        return k.get("api_key", k) if isinstance(k, dict) else k

    if provider == "google":
        for key_name in ["google_ai", "google_gemini", "google_ai_studio"]:
            k = tokens.get(key_name, {})
            val = k.get("api_key", k) if isinstance(k, dict) else k
            if val and isinstance(val, str) and len(val) > 10:
                return val
        return ""

    if provider == "openrouter":
        return tokens.get("openrouter", {}).get("api_key", "")

    if provider == "xai":
        k = tokens.get("xai", {})
        return k.get("api_key", k) if isinstance(k, dict) else k

    return ""


def call_provider(provider: str, model_id: str, prompt: str,
                  system: str = "", max_tokens: int = 4096,
                  retries: int = 2) -> dict:
    """Call a model via its native provider API (OpenAI-compatible).
    Retries on 429 with exponential backoff."""
    import time as _time

    api_key = get_provider_key(provider)
    if not api_key:
        raise ValueError(f"Нет API ключа для {provider}. Добавь в tokens.json.")

    url = PROVIDER_URLS[provider]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://artvision.pro"
        headers["X-Title"] = "Artvision Consilium"

    data = None
    for attempt in range(retries + 1):
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                url,
                headers=headers,
                json={
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 429 and attempt < retries:
                wait = 2 ** attempt + 1  # 2s, 3s
                _time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break

    assert data is not None
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    model_used = data.get("model", model_id)

    return {
        "content": content,
        "model": model_used,
        "provider": provider,
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
    }


def _call_model_safe(model_name: str, prompt: str, system: str, max_tokens: int) -> dict:
    """Thread-safe wrapper for call_provider. Returns result or error dict."""
    cfg = MODELS[model_name]
    try:
        result = call_provider(cfg["provider"], cfg["model_id"], prompt, system, max_tokens)
        result["model_name"] = model_name
        result["cost"] = cfg["cost"]
        return result
    except Exception as e:
        return {"model_name": model_name, "error": str(e), "cost": cfg["cost"]}


# --- MCP Server ---

mcp = FastMCP(
    "llm-consilium",
    instructions=(
        "LLM Consilium — оркестратор внешних моделей. "
        "ask_auto — авто-роутинг к лучшей модели по типу задачи. "
        "round_table — параллельный опрос + синтез мастер-моделью (DeepSeek R1). "
        "ask_model — ручной выбор. Все бесплатные."
    ),
)


@mcp.tool()
def ask_model(
    prompt: str,
    model: str = "llama",
    system_prompt: str = "",
    max_tokens: int = 4096,
) -> str:
    """
    Спросить мнение конкретной модели.

    Args:
        prompt: Вопрос или задача для модели
        model: Короткое имя (llama, kimi-k2, qwen3, llama-scout, gpt-oss-groq,
               hermes-405b, qwen3-coder, qwen3-80b, nemotron-120b, gpt-oss,
               gemma4, llama-or, minimax)
        system_prompt: Системный промпт (роль, контекст)
        max_tokens: Максимум токенов ответа
    """
    if model not in MODELS:
        return f"Модель '{model}' не найдена. Используй list_models() для списка."

    cfg = MODELS[model]
    result = call_provider(cfg["provider"], cfg["model_id"], prompt, system_prompt, max_tokens)

    return (
        f"## Ответ: {result['model']}\n"
        f"**Провайдер:** {result['provider']} | **Стоимость:** {cfg['cost']}\n"
        f"**Токены:** {result['tokens_in']} in / {result['tokens_out']} out\n\n"
        f"{result['content']}"
    )


@mcp.tool()
def ask_auto(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4096,
) -> str:
    """
    Авто-роутинг — автоматически выбирает лучшую модель под задачу.

    Роутинг: код→DeepSeek, логика→DeepSeek-R1, данные/бизнес→Qwen,
    креатив→Llama, языки→Mistral.

    Args:
        prompt: Вопрос или задача
        system_prompt: Системный промпт
        max_tokens: Максимум токенов
    """
    model, reason = auto_route(prompt)
    cfg = MODELS[model]

    result = call_provider(cfg["provider"], cfg["model_id"], prompt, system_prompt, max_tokens)

    return (
        f"## Авто-роутинг: {model}\n"
        f"**Почему:** {reason}\n"
        f"**Провайдер:** {result['provider']} | **Стоимость:** {cfg['cost']}\n"
        f"**Токены:** {result['tokens_in']} in / {result['tokens_out']} out\n\n"
        f"{result['content']}"
    )


@mcp.tool()
def round_table(
    prompt: str,
    models: str = "llama,qwen3,gpt-oss-groq",
    system_prompt: str = "",
    synthesize: bool = True,
    master: str = "",
    max_tokens: int = 2048,
) -> str:
    """
    Круглый стол — параллельный опрос нескольких моделей + синтез мастер-моделью.

    1. Все модели получают один промпт ПАРАЛЛЕЛЬНО
    2. Мастер-модель (DeepSeek R1) анализирует все ответы и делает взвешенный синтез

    Args:
        prompt: Вопрос или задача
        models: Модели через запятую (e.g. "llama,deepseek,qwen")
        system_prompt: Общий системный промпт
        synthesize: Включить синтез мастер-моделью (default: True)
        master: Мастер-модель для синтеза (default: deepseek-r1, fallback: llama)
        max_tokens: Максимум токенов на каждый ответ
    """
    model_list = [m.strip() for m in models.split(",") if m.strip() in MODELS]
    if not model_list:
        return "Ни одна модель не найдена. Используй list_models()."

    # --- Phase 1: Parallel calls ---
    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=len(model_list)) as executor:
        futures = {
            executor.submit(_call_model_safe, m, prompt, system_prompt, max_tokens): m
            for m in model_list
        }
        for future in as_completed(futures):
            r = future.result()
            if "error" in r:
                errors.append(r)
            else:
                results.append(r)

    # Format individual responses
    response_parts = []
    for r in results:
        response_parts.append(
            f"### {r['model_name']} ({r['model']})\n"
            f"**Провайдер:** {r['provider']} | {r['cost']}\n"
            f"**Токены:** {r['tokens_in']} in / {r['tokens_out']} out\n\n"
            f"{r['content']}"
        )
    for e in errors:
        response_parts.append(f"### {e['model_name']}\n**ОШИБКА:** {e['error']}")

    individual = "\n\n---\n\n".join(response_parts)

    # --- Phase 2: Master synthesis ---
    synthesis_text = ""
    if synthesize and len(results) >= 2:
        master_model = master or MASTER_MODEL
        if master_model not in MODELS:
            master_model = MASTER_FALLBACK

        # Build synthesis prompt
        opinions = []
        for r in results:
            opinions.append(f"[{r['model_name']}]:\n{r['content']}")

        synthesis_prompt = (
            f"Ты — мастер-синтезатор консилиума моделей.\n\n"
            f"Исходный вопрос:\n{prompt}\n\n"
            f"Ответы {len(results)} моделей:\n\n"
            + "\n\n---\n\n".join(opinions) +
            f"\n\n"
            f"Твоя задача:\n"
            f"1. Выдели ОБЩЕЕ — в чём модели согласны\n"
            f"2. Выдели РАСХОЖДЕНИЯ — где мнения разошлись и кто убедительнее\n"
            f"3. Отметь УНИКАЛЬНЫЕ ИНСАЙТЫ — что заметила только одна модель\n"
            f"4. Дай ВЗВЕШЕННЫЙ ВЫВОД — синтез лучших идей из всех ответов\n"
            f"5. Оцени УВЕРЕННОСТЬ: HIGH/MEDIUM/LOW\n\n"
            f"Формат: структурированный ответ с заголовками. Кратко, по делу."
        )

        try:
            master_cfg = MODELS[master_model]
            master_result = call_provider(
                master_cfg["provider"], master_cfg["model_id"],
                synthesis_prompt, max_tokens=max_tokens
            )
            synthesis_text = (
                f"\n\n{'='*60}\n"
                f"## СИНТЕЗ (мастер: {master_model})\n"
                f"**Токены:** {master_result['tokens_in']} in / {master_result['tokens_out']} out\n\n"
                f"{master_result['content']}"
            )
        except Exception as e:
            # Fallback to MASTER_FALLBACK
            if master_model != MASTER_FALLBACK:
                try:
                    fb_cfg = MODELS[MASTER_FALLBACK]
                    fb_result = call_provider(
                        fb_cfg["provider"], fb_cfg["model_id"],
                        synthesis_prompt, max_tokens=max_tokens
                    )
                    synthesis_text = (
                        f"\n\n{'='*60}\n"
                        f"## СИНТЕЗ (fallback: {MASTER_FALLBACK}, {master_model} недоступен)\n"
                        f"**Токены:** {fb_result['tokens_in']} in / {fb_result['tokens_out']} out\n\n"
                        f"{fb_result['content']}"
                    )
                except Exception as e2:
                    synthesis_text = f"\n\n## СИНТЕЗ\n**ОШИБКА:** {master_model}: {e}, {MASTER_FALLBACK}: {e2}"
            else:
                synthesis_text = f"\n\n## СИНТЕЗ\n**ОШИБКА:** {e}"

    return (
        f"# Круглый стол — {len(results)} моделей"
        f"{f', {len(errors)} ошибок' if errors else ''}\n"
        f"**Промпт:** {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n\n"
        f"{individual}"
        f"{synthesis_text}"
    )


@mcp.tool()
def list_models() -> str:
    """Показать все доступные модели, провайдеров, стоимость и специализации."""
    lines = ["# Доступные модели\n"]

    by_provider: dict[str, list] = {}
    for short, cfg in MODELS.items():
        by_provider.setdefault(cfg["provider"], []).append((short, cfg))

    provider_names = {
        "groq": "Groq (FREE, быстрый)",
        "deepseek": "DeepSeek (прямой API)",
        "google": "Google AI Studio (geo-blocked RU)",
        "openrouter": "OpenRouter",
        "xai": "xAI Grok ($25 credits)",
    }

    for provider, models_list in by_provider.items():
        has_key = bool(get_provider_key(provider))
        status = "OK" if has_key else "НЕТ КЛЮЧА"
        lines.append(f"\n## {provider_names.get(provider, provider)} [{status}]")
        for short, cfg in models_list:
            strengths = ", ".join(cfg.get("strengths", []))
            lines.append(f"- **{short}** → `{cfg['model_id']}` — {cfg['cost']} [{strengths}]")

    lines.append(
        "\n## Авто-роутинг (ask_auto)\n"
        "| Тип задачи | Модель |\n|---|---|\n"
    )
    for _, _, reason in ROUTE_RULES:
        lines.append(f"| {reason} |")

    lines.append(f"\n**Мастер-синтезатор:** {MASTER_MODEL} (fallback: {MASTER_FALLBACK})")

    return "\n".join(lines)


@mcp.tool()
def check_balance() -> str:
    """Проверить статус провайдеров и баланс OpenRouter."""
    lines = ["# Статус провайдеров\n"]

    for provider in ["groq", "deepseek", "google", "openrouter"]:
        key = get_provider_key(provider)
        if key:
            lines.append(f"- **{provider}**: ключ есть ({key[:12]}...)")
        else:
            lines.append(f"- **{provider}**: НЕТ КЛЮЧА")

    try:
        or_key = get_provider_key("openrouter")
        if or_key:
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {or_key}"},
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
            lines.append(
                f"\n## OpenRouter баланс\n"
                f"- Использовано: ${data.get('usage', 0):.4f}\n"
                f"- За месяц: ${data.get('usage_monthly', 0):.4f}"
            )
    except Exception as e:
        lines.append(f"\n## OpenRouter баланс\n- Ошибка: {e}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

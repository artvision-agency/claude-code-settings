---
name: web-scraping-patterns
description: Web scraping best practices covering HTML parsing, Telegram scraping, rate limiting, deduplication, and LLM-powered extraction
---

# Web Scraping Patterns

## Overview

This skill covers practical patterns for building robust web scraping pipelines. It spans multiple tools (Cheerio, BeautifulSoup, Telethon, Jina Reader), languages (Node.js and Python), and includes strategies for rate limiting, deduplication, error handling, and LLM-powered extraction as a fallback.

## Cheerio (Node.js) HTML Parsing

Cheerio provides jQuery-like selectors for server-side HTML parsing. It does not execute JavaScript, making it fast and lightweight.

```typescript
// scraper/src/cheerio-parser.ts
import * as cheerio from "cheerio";

interface Article {
  title: string;
  url: string;
  author: string;
  date: string;
  summary: string;
}

export function parseArticleList(html: string, baseUrl: string): Article[] {
  const $ = cheerio.load(html);
  const articles: Article[] = [];

  $("article.post-card").each((_, el) => {
    const $el = $(el);
    const relativeUrl = $el.find("a.title-link").attr("href") || "";
    const fullUrl = new URL(relativeUrl, baseUrl).toString();

    articles.push({
      title: $el.find("h2.title").text().trim(),
      url: fullUrl,
      author: $el.find(".author-name").text().trim(),
      date: $el.find("time").attr("datetime") || "",
      summary: $el.find(".excerpt").text().trim(),
    });
  });

  return articles;
}

export function parseArticleBody(html: string): { content: string; tags: string[] } {
  const $ = cheerio.load(html);

  // Remove unwanted elements before extracting text
  $("script, style, nav, footer, .ad-banner, .sidebar").remove();

  const content = $("article .body, .post-content, main")
    .first()
    .text()
    .replace(/\s+/g, " ")
    .trim();

  const tags = $(".tag, .category")
    .map((_, el) => $(el).text().trim())
    .get();

  return { content, tags };
}
```

## BeautifulSoup4 (Python) Patterns

```python
# scraper/parsers/bs4_parser.py
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass
class Product:
    name: str
    price: float
    url: str
    image_url: str
    rating: float | None


def parse_product_listing(html: str, base_url: str) -> list[Product]:
    soup = BeautifulSoup(html, "lxml")
    products = []

    for card in soup.select("div.product-card"):
        name_el = card.select_one("h3.product-name")
        price_el = card.select_one("span.price")
        link_el = card.select_one("a.product-link")
        img_el = card.select_one("img.product-image")
        rating_el = card.select_one("span.rating")

        if not name_el or not price_el or not link_el:
            continue

        price_text = price_el.get_text(strip=True).replace("$", "").replace(",", "")

        products.append(Product(
            name=name_el.get_text(strip=True),
            price=float(price_text),
            url=urljoin(base_url, link_el.get("href", "")),
            image_url=urljoin(base_url, img_el.get("src", "")) if img_el else "",
            rating=float(rating_el.get_text(strip=True)) if rating_el else None,
        ))

    return products


def extract_table_data(html: str) -> list[dict[str, str]]:
    """Extract data from an HTML table into a list of dicts."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table")
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = []

    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))

    return rows
```

## Telethon for Telegram Channel Scraping

```python
# scraper/telegram_scraper.py
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from dataclasses import dataclass
from datetime import datetime
import asyncio


@dataclass
class TelegramPost:
    channel: str
    message_id: int
    date: datetime
    text: str
    has_media: bool
    views: int


class TelegramChannelScraper:
    def __init__(self, api_id: int, api_hash: str, session_name: str = "scraper"):
        self.client = TelegramClient(session_name, api_id, api_hash)

    async def connect(self) -> None:
        await self.client.start()

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def scrape_channel(
        self,
        channel_username: str,
        limit: int = 100,
        min_date: datetime | None = None,
    ) -> list[TelegramPost]:
        posts = []
        entity = await self.client.get_entity(channel_username)

        async for message in self.client.iter_messages(
            entity, limit=limit, offset_date=min_date, reverse=True
        ):
            if message.text is None and message.media is None:
                continue

            posts.append(TelegramPost(
                channel=channel_username,
                message_id=message.id,
                date=message.date,
                text=message.text or "",
                has_media=message.media is not None,
                views=message.views or 0,
            ))

        return posts

    async def scrape_multiple_channels(
        self,
        channels: list[str],
        limit_per_channel: int = 50,
    ) -> dict[str, list[TelegramPost]]:
        results = {}
        for channel in channels:
            try:
                posts = await self.scrape_channel(channel, limit=limit_per_channel)
                results[channel] = posts
            except Exception as e:
                print(f"Error scraping {channel}: {e}")
                results[channel] = []
            await asyncio.sleep(2)  # Rate limit between channels

        return results
```

## Jina Reader API for LLM-Ready Content

Jina Reader converts any URL into clean markdown, perfect for feeding into LLMs:

```typescript
// scraper/src/jina-reader.ts
interface JinaResult {
  title: string;
  content: string;
  url: string;
}

export async function fetchWithJina(url: string): Promise<JinaResult> {
  const response = await fetch(`https://r.jina.ai/${url}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${process.env.JINA_API_KEY}`,
      "X-Return-Format": "markdown",
    },
  });

  if (!response.ok) {
    throw new Error(`Jina Reader failed: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();

  return {
    title: data.data?.title || "",
    content: data.data?.content || "",
    url: data.data?.url || url,
  };
}

export async function fetchMultipleWithJina(
  urls: string[],
  concurrency: number = 3,
  delayMs: number = 1000,
): Promise<JinaResult[]> {
  const results: JinaResult[] = [];

  for (let i = 0; i < urls.length; i += concurrency) {
    const batch = urls.slice(i, i + concurrency);
    const batchResults = await Promise.allSettled(
      batch.map((url) => fetchWithJina(url))
    );

    for (const result of batchResults) {
      if (result.status === "fulfilled") {
        results.push(result.value);
      }
    }

    if (i + concurrency < urls.length) {
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }

  return results;
}
```

## Rate Limiting and Backoff Strategies

### Token Bucket Rate Limiter

```python
# scraper/rate_limiter.py
import asyncio
import time
from dataclasses import dataclass


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""
    max_tokens: float
    refill_rate: float  # tokens per second
    _tokens: float = 0.0
    _last_refill: float = 0.0

    def __post_init__(self):
        self._tokens = self.max_tokens
        self._last_refill = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self.max_tokens,
                self._tokens + elapsed * self.refill_rate,
            )
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            wait_time = (1.0 - self._tokens) / self.refill_rate
            await asyncio.sleep(wait_time)
```

### Exponential Backoff with Jitter

```python
# scraper/backoff.py
import asyncio
import random
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")


async def with_backoff(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (Exception,),
) -> T:
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except retryable_exceptions as e:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.5)
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay + jitter:.1f}s")
            await asyncio.sleep(delay + jitter)

    raise RuntimeError("Unreachable")
```

## Deduplication

### Text Hash Deduplication

```python
# scraper/dedup.py
import hashlib
import re
from typing import Set


class TextDeduplicator:
    """Deduplicates content based on normalized text hashes."""

    def __init__(self):
        self._seen_hashes: Set[str] = set()

    def normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", "", text)
        return text

    def compute_hash(self, text: str) -> str:
        normalized = self.normalize(text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def is_duplicate(self, text: str) -> bool:
        h = self.compute_hash(text)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False
```

### URL Normalization

```python
# scraper/url_normalize.py
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication purposes."""
    parsed = urlparse(url.strip())

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().rstrip(".")

    # Remove default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Remove trailing slash from path
    path = parsed.path.rstrip("/") or "/"

    # Sort and filter query params (remove tracking params)
    tracking_params = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "fbclid", "ref"}
    query_params = parse_qs(parsed.query)
    filtered = {k: v for k, v in query_params.items() if k not in tracking_params}
    sorted_query = urlencode(filtered, doseq=True)

    # Remove fragment
    return urlunparse((scheme, netloc, path, "", sorted_query, ""))
```

## Data Extraction Pipeline

Build a pipeline that fetches, parses, deduplicates, and stores:

```python
# scraper/pipeline.py
import asyncio
import httpx
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

from scraper.rate_limiter import RateLimiter
from scraper.backoff import with_backoff
from scraper.dedup import TextDeduplicator
from scraper.url_normalize import normalize_url


@dataclass
class ScrapedItem:
    url: str
    title: str
    content: str
    scraped_at: datetime


class ScrapingPipeline:
    def __init__(
        self,
        rate_limiter: RateLimiter,
        deduplicator: TextDeduplicator,
        max_concurrent: int = 5,
    ):
        self.rate_limiter = rate_limiter
        self.dedup = deduplicator
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CustomBot/1.0)"},
        )

    async def fetch_url(self, url: str) -> str:
        await self.rate_limiter.acquire()
        async with self.semaphore:
            response = await with_backoff(
                lambda: self.client.get(url),
                max_retries=3,
                retryable_exceptions=(httpx.HTTPStatusError, httpx.ConnectTimeout),
            )
            response.raise_for_status()
            return response.text

    async def process_urls(self, urls: list[str]) -> AsyncIterator[ScrapedItem]:
        seen_urls = set()

        for url in urls:
            normalized = normalize_url(url)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)

            try:
                html = await self.fetch_url(url)
                # Parse with your chosen parser here
                item = self._parse(url, html)

                if item and not self.dedup.is_duplicate(item.content):
                    yield item
            except Exception as e:
                print(f"Failed to process {url}: {e}")

    def _parse(self, url: str, html: str) -> ScrapedItem | None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        title_el = soup.select_one("title")
        body_el = soup.select_one("article, main, .content")

        if not body_el:
            return None

        return ScrapedItem(
            url=url,
            title=title_el.get_text(strip=True) if title_el else "",
            content=body_el.get_text(separator="\n", strip=True),
            scraped_at=datetime.utcnow(),
        )

    async def close(self):
        await self.client.aclose()
```

## Proxy Rotation

```python
# scraper/proxy_pool.py
import itertools
import httpx
from dataclasses import dataclass


@dataclass
class Proxy:
    url: str
    protocol: str = "http"
    failed_count: int = 0


class ProxyPool:
    def __init__(self, proxies: list[str]):
        self._proxies = [Proxy(url=p) for p in proxies]
        self._cycle = itertools.cycle(self._proxies)
        self._max_failures = 3

    def get_next(self) -> Proxy | None:
        """Get the next healthy proxy via round-robin."""
        tried = 0
        while tried < len(self._proxies):
            proxy = next(self._cycle)
            if proxy.failed_count < self._max_failures:
                return proxy
            tried += 1
        return None  # All proxies exhausted

    def report_failure(self, proxy: Proxy) -> None:
        proxy.failed_count += 1

    def report_success(self, proxy: Proxy) -> None:
        proxy.failed_count = max(0, proxy.failed_count - 1)

    def get_httpx_client(self) -> httpx.AsyncClient:
        proxy = self.get_next()
        if proxy is None:
            return httpx.AsyncClient(timeout=30.0)
        return httpx.AsyncClient(
            timeout=30.0,
            proxy=proxy.url,
        )
```

## Cron / APScheduler for Scheduled Scraping

```python
# scraper/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import asyncio


scheduler = AsyncIOScheduler()


async def scrape_news_sites():
    """Runs every 30 minutes to scrape news sites."""
    from scraper.pipeline import ScrapingPipeline
    from scraper.rate_limiter import RateLimiter
    from scraper.dedup import TextDeduplicator

    pipeline = ScrapingPipeline(
        rate_limiter=RateLimiter(max_tokens=5, refill_rate=1.0),
        deduplicator=TextDeduplicator(),
    )

    urls = [
        "https://example.com/news",
        "https://example.com/blog",
    ]

    async for item in pipeline.process_urls(urls):
        print(f"Scraped: {item.title}")
        # Save to database here

    await pipeline.close()


async def scrape_telegram_channels():
    """Runs every hour to scrape Telegram channels."""
    from scraper.telegram_scraper import TelegramChannelScraper
    import os

    scraper = TelegramChannelScraper(
        api_id=int(os.environ["TELEGRAM_API_ID"]),
        api_hash=os.environ["TELEGRAM_API_HASH"],
    )
    await scraper.connect()

    results = await scraper.scrape_multiple_channels(
        channels=["@example_channel", "@news_channel"],
        limit_per_channel=20,
    )

    for channel, posts in results.items():
        print(f"{channel}: {len(posts)} new posts")
        # Save to database here

    await scraper.disconnect()


def setup_scheduler():
    scheduler.add_job(
        scrape_news_sites,
        trigger=IntervalTrigger(minutes=30),
        id="news_scraper",
        replace_existing=True,
    )

    scheduler.add_job(
        scrape_telegram_channels,
        trigger=CronTrigger(minute=0),  # Every hour on the hour
        id="telegram_scraper",
        replace_existing=True,
    )

    scheduler.start()


# In main.py:
# setup_scheduler()
# asyncio.get_event_loop().run_forever()
```

## LLM-Powered Extraction as Fallback

When structured selectors fail, use an LLM to extract data:

```python
# scraper/llm_extractor.py
import json
import httpx
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    data: dict
    model: str
    tokens_used: int


async def extract_with_llm(
    text: str,
    schema_description: str,
    model: str = "llama-3.1-70b-versatile",
    provider: str = "groq",
) -> ExtractionResult:
    """
    Use an LLM to extract structured data from text.
    Falls back from Groq to OpenAI if Groq fails.
    """
    system_prompt = f"""Extract the following information from the provided text.
Return ONLY valid JSON matching this schema:
{schema_description}

If a field cannot be determined, use null."""

    providers = {
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key_env": "GROQ_API_KEY",
            "model": model,
        },
        "openai": {
            "url": "https://api.openai.com/v1/chat/completions",
            "key_env": "OPENAI_API_KEY",
            "model": "gpt-4o-mini",
        },
    }

    errors = []

    for provider_name in [provider, "openai"] if provider != "openai" else ["openai"]:
        config = providers[provider_name]
        import os
        api_key = os.environ.get(config["key_env"])
        if not api_key:
            continue

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config["url"],
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config["model"],
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text[:8000]},
                        ],
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                tokens = data.get("usage", {}).get("total_tokens", 0)

                return ExtractionResult(
                    data=parsed,
                    model=config["model"],
                    tokens_used=tokens,
                )
        except Exception as e:
            errors.append(f"{provider_name}: {e}")

    raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")


# Usage example:
# result = await extract_with_llm(
#     text=raw_html_text,
#     schema_description='{"title": "string", "author": "string", "date": "ISO date", "topics": ["string"]}',
# )
```

## Error Handling and Retry Logic

Wrap the entire scraping flow with structured error handling:

```python
# scraper/error_handling.py
import logging
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    TRANSIENT = "transient"     # Retry
    PERMANENT = "permanent"     # Skip
    CRITICAL = "critical"       # Stop the pipeline


@dataclass
class ScrapeError:
    url: str
    error: Exception
    severity: ErrorSeverity


def classify_error(error: Exception) -> ErrorSeverity:
    """Classify an error to determine retry behavior."""
    import httpx

    if isinstance(error, httpx.ConnectTimeout):
        return ErrorSeverity.TRANSIENT
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status == 429:  # Too Many Requests
            return ErrorSeverity.TRANSIENT
        if status in (403, 404, 410):
            return ErrorSeverity.PERMANENT
        if status >= 500:
            return ErrorSeverity.TRANSIENT
    if isinstance(error, (ConnectionError, TimeoutError)):
        return ErrorSeverity.TRANSIENT

    return ErrorSeverity.PERMANENT


async def resilient_scrape(url: str, pipeline) -> ScrapedItem | None:
    """Scrape a URL with error classification and structured logging."""
    try:
        html = await pipeline.fetch_url(url)
        return pipeline._parse(url, html)
    except Exception as e:
        severity = classify_error(e)
        logger.warning(f"[{severity.value}] Failed to scrape {url}: {e}")

        if severity == ErrorSeverity.CRITICAL:
            raise
        return None
```

## Key Principles

1. **Respect robots.txt** -- Always check robots.txt before scraping. Use the `robotparser` module from Python's standard library.
2. **Set reasonable rate limits** -- 1-2 requests per second is a good default. Increase only if the site explicitly allows it.
3. **Use proper User-Agent strings** -- Identify your bot. Do not impersonate browsers unless scraping requires JavaScript rendering.
4. **Handle encoding correctly** -- Use `response.encoding` detection or `chardet` for pages with non-UTF-8 encoding.
5. **Store raw HTML alongside extracted data** -- This lets you re-parse later if your extraction logic changes.
6. **Monitor for site structure changes** -- Selectors break when sites redesign. Use alerts when extraction yields empty results.
7. **Prefer APIs when available** -- Many sites offer APIs that are faster, more reliable, and within terms of service.

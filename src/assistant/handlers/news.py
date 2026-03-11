"""
News command handler.

Handles commands like:
  - "tell me the news"
  - "what's happening today?"
  - "latest headlines"
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import httpx

from assistant.config.settings import AppSettings
from assistant.handlers.base import BaseHandler, HandlerResponse
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


class NewsHandler(BaseHandler):
    """Fetches and reads the top news headlines."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings.news
        self._client = httpx.AsyncClient(timeout=10.0)
        self._cache: Optional[Tuple[float, List[dict]]] = None

    @property
    def patterns(self) -> List[str]:
        return [
            r"\b(news|headlines|happening|stories)\b",
            r"\bwhat.*(today|going on)\b",
            r"\btell me.*(news|headlines)\b",
            r"\blatest\b",
        ]

    async def handle(self, command: str) -> HandlerResponse:
        articles = await self._get_articles()
        if not articles:
            return HandlerResponse.error(
                "I couldn't fetch any news headlines right now. "
                "Please check your internet connection."
            )

        count = min(len(articles), self._settings.page_size)
        lines = [f"Here are the top {count} headlines:"]
        for i, article in enumerate(articles[:count], start=1):
            title = article.get("title", "").split(" - ")[0].strip()
            if title:
                lines.append(f"{i}. {title}.")

        return HandlerResponse(
            text=" ".join(lines),
            data={"articles": articles[:count]},
        )

    async def _get_articles(self) -> List[dict]:
        now = time.monotonic()
        if self._cache and (now - self._cache[0]) < self._settings.cache_ttl_seconds:
            logger.debug("News cache hit")
            return self._cache[1]

        try:
            response = await self._client.get(
                f"{self._settings.base_url}/top-headlines",
                params={
                    "country": self._settings.country,
                    "pageSize": self._settings.page_size,
                    "apiKey": self._settings.api_key,
                },
            )
            response.raise_for_status()
            articles = response.json().get("articles", [])
            self._cache = (now, articles)
            return articles
        except httpx.TimeoutException:
            logger.warning("News API request timed out")
            return []
        except Exception:
            logger.exception("Failed to fetch news articles")
            return []

    async def close(self) -> None:
        await self._client.aclose()

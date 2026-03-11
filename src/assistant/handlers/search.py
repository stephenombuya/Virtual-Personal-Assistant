"""
Web search handler.

Handles commands like:
  - "search for Python tutorials"
  - "Google how to make pasta"
  - "look up machine learning"
"""

from __future__ import annotations

import re
import urllib.parse
import webbrowser
from typing import List

from assistant.handlers.base import BaseHandler, HandlerResponse
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


class SearchHandler(BaseHandler):
    """Opens a Google search in the default browser."""

    _SEARCH_URL = "https://www.google.com/search?q={query}"

    @property
    def patterns(self) -> List[str]:
        return [
            r"\b(search|google|look up|look for|find)\b.+",
            r"\bsearch (for|about|how)\b",
        ]

    async def handle(self, command: str) -> HandlerResponse:
        query = self._extract_query(command)
        if not query:
            return HandlerResponse.error(
                "What would you like me to search for? "
                "Try saying 'search for Python tutorials'."
            )

        url = self._SEARCH_URL.format(query=urllib.parse.quote_plus(query))
        try:
            opened = webbrowser.open(url)
            if not opened:
                raise RuntimeError("webbrowser.open returned False")
        except Exception as exc:
            logger.exception("Failed to open browser for search: %s", exc)
            return HandlerResponse.error(
                "I couldn't open your browser. Please check your browser settings."
            )

        return HandlerResponse(
            text=f"Searching Google for '{query}'.",
            data={"query": query, "url": url},
        )

    def _extract_query(self, command: str) -> str:
        """Strip the action verb and return the raw search query."""
        cleaned = re.sub(
            r"^(?:please\s+)?(?:search(?:\s+for|\s+about|\s+how)?|google|look\s+up|look\s+for|find)\s+",
            "",
            command,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned

"""
Date and time command handler.

Handles commands like:
  - "what time is it?"
  - "what's the date?"
  - "what day is it today?"
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from assistant.handlers.base import BaseHandler, HandlerResponse


class DateTimeHandler(BaseHandler):
    """Returns the current date and/or time."""

    @property
    def patterns(self) -> List[str]:
        return [
            r"\bwhat.*(time|clock)\b",
            r"\bcurrent time\b",
            r"\bwhat.*(date|day|today)\b",
            r"\bwhat day\b",
            r"\btell me the (time|date)\b",
        ]

    async def handle(self, command: str) -> HandlerResponse:
        now = datetime.now()
        cmd = command.lower()

        if any(kw in cmd for kw in ("date", "day", "today")):
            text = f"Today is {now.strftime('%A, %B %d, %Y')}."
        elif any(kw in cmd for kw in ("time", "clock")):
            text = f"The current time is {now.strftime('%I:%M %p')}."
        else:
            text = (
                f"It is {now.strftime('%I:%M %p')} "
                f"on {now.strftime('%A, %B %d, %Y')}."
            )

        return HandlerResponse(
            text=text,
            data={"datetime": now.isoformat()},
        )

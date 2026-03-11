"""
Reminder command handler.

Handles commands like:
  - "remind me at 3 pm to call mom"
  - "set a reminder for 14:30 to take medicine"
  - "list my reminders"
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

from assistant.database.repository import ReminderRepository
from assistant.handlers.base import BaseHandler, HandlerResponse
from assistant.utils.logger import get_logger

logger = get_logger(__name__)

# Regex patterns for time extraction
_TIME_12H = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
    re.IGNORECASE,
)
_TIME_24H = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_IN_DELTA = re.compile(
    r"\bin\s+(\d+)\s+(minute|minutes|min|hour|hours|hr|second|seconds|sec)\b",
    re.IGNORECASE,
)

# Phrases that mark the reminder message
_MESSAGE_MARKERS = re.compile(
    r"\bto\b|\bto\s+(?:call|take|send|check|do|go|buy|meet|pick)",
    re.IGNORECASE,
)


def _parse_time(command: str) -> Optional[datetime]:
    """Attempt to parse a time expression from the command."""
    now = datetime.now()

    # "in X minutes/hours"
    match = _IN_DELTA.search(command)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("sec"):
            return now + timedelta(seconds=amount)
        elif unit.startswith("min"):
            return now + timedelta(minutes=amount)
        else:
            return now + timedelta(hours=amount)

    # 12-hour format: "3 pm", "3:30 pm"
    match = _TIME_12H.search(command)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3).lower()
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # 24-hour format: "14:30"
    match = _TIME_24H.search(command)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target

    return None


def _extract_message(command: str) -> Optional[str]:
    """Extract the reminder message from the command string."""
    # Try to find text after "to" keyword
    match = re.search(r"\bto\s+(.+?)(?:\s+at\s+|$)", command, re.IGNORECASE)
    if match:
        msg = match.group(1).strip()
        if msg:
            return msg

    # Fallback: strip time-related tokens
    cleaned = re.sub(
        r"\b(remind(?:er)?|set|a|me|at|for|in|the|please)\b|"
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm|o.?clock)?\b",
        "",
        command,
        flags=re.IGNORECASE,
    )
    cleaned = " ".join(cleaned.split())
    return cleaned if len(cleaned) > 2 else None


class ReminderHandler(BaseHandler):
    """Creates and lists voice-activated reminders."""

    def __init__(self, repo: ReminderRepository) -> None:
        self._repo = repo

    @property
    def patterns(self) -> List[str]:
        return [
            r"\b(remind|reminder|set.+reminder|remember)\b",
            r"\blist.+reminder\b",
            r"\bmy.+reminder\b",
        ]

    async def handle(self, command: str) -> HandlerResponse:
        cmd = command.lower()

        # List reminders
        if re.search(r"\b(list|show|what)\b.*\breminder\b", cmd, re.IGNORECASE):
            return await self._list_reminders()

        return await self._create_reminder(command)

    async def _create_reminder(self, command: str) -> HandlerResponse:
        remind_at = _parse_time(command)
        if not remind_at:
            return HandlerResponse.error(
                "I couldn't understand the time for your reminder. "
                "Try saying 'remind me at 3 pm to call mom' or "
                "'remind me in 30 minutes to take medicine'."
            )

        message = _extract_message(command) or "reminder"

        try:
            reminder = self._repo.create(message=message, remind_at=remind_at)
        except Exception:
            logger.exception("Failed to save reminder")
            return HandlerResponse.error("I had trouble saving that reminder.")

        friendly_time = remind_at.strftime("%I:%M %p")
        text = f"Got it. I'll remind you to {message} at {friendly_time}."
        return HandlerResponse(
            text=text,
            data={"reminder_id": reminder.id, "remind_at": remind_at.isoformat()},
        )

    async def _list_reminders(self) -> HandlerResponse:
        try:
            reminders = self._repo.list_upcoming(limit=5)
        except Exception:
            logger.exception("Failed to list reminders")
            return HandlerResponse.error("I couldn't retrieve your reminders right now.")

        if not reminders:
            return HandlerResponse(text="You have no upcoming reminders.")

        lines = [f"You have {len(reminders)} upcoming reminder(s):"]
        for r in reminders:
            t = r.remind_at.strftime("%I:%M %p on %A")
            lines.append(f"{r.message} at {t}.")

        return HandlerResponse(text=" ".join(lines), data={"count": len(reminders)})

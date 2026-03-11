"""
Background scheduler — polls the database for due reminders and
fires them through the speech engine.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from assistant.database.repository import ReminderRepository
from assistant.core.speech import SpeechEngine
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


class ReminderScheduler:
    """
    Polls for pending reminders on a fixed interval and notifies the user.
    Runs as a background asyncio task.
    """

    def __init__(
        self,
        repo: ReminderRepository,
        speech: SpeechEngine,
        poll_interval: int = 30,
    ) -> None:
        self._repo = repo
        self._speech = speech
        self._poll_interval = poll_interval
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the scheduler as a background coroutine."""
        self._task = asyncio.create_task(self._run(), name="reminder-scheduler")
        logger.info("Reminder scheduler started (interval=%ds)", self._poll_interval)

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            logger.info("Reminder scheduler stopped")

    async def _run(self) -> None:
        try:
            while True:
                await self._check_reminders()
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass

    async def _check_reminders(self) -> None:
        try:
            pending = self._repo.get_pending(as_of=datetime.now())
        except Exception:
            logger.exception("Error polling for reminders")
            return

        for reminder in pending:
            logger.info("Firing reminder id=%s: %s", reminder.id, reminder.message)
            self._speech.speak(f"Reminder: {reminder.message}")
            try:
                self._repo.mark_completed(reminder.id)
            except Exception:
                logger.exception("Failed to mark reminder %s completed", reminder.id)

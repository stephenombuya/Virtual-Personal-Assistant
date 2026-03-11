"""
VoiceAssistant — top-level orchestrator.

Wires all sub-systems together and runs the main listen → route → speak loop.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Optional

from assistant.config.settings import AppSettings
from assistant.core.command_router import CommandRouter
from assistant.core.scheduler import ReminderScheduler
from assistant.core.speech import MicrophoneNotFoundError, SpeechEngine, SpeechRecognitionError
from assistant.database.repository import CommandLogRepository, DatabaseManager, ReminderRepository
from assistant.handlers.datetime_handler import DateTimeHandler
from assistant.handlers.news import NewsHandler
from assistant.handlers.reminder import ReminderHandler
from assistant.handlers.search import SearchHandler
from assistant.handlers.system import SystemHandler
from assistant.handlers.weather import WeatherHandler
from assistant.utils.logger import get_logger

logger = get_logger(__name__)

_EXIT_PHRASES = frozenset(
    {"goodbye", "bye", "exit", "quit", "stop", "shut down", "see you"}
)


class VoiceAssistant:
    """
    Lifecycle controller for the voice assistant.

    Usage:
        async with VoiceAssistant(settings) as assistant:
            await assistant.run()
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._running = False

        # Infrastructure
        self._db = DatabaseManager(settings)
        self._speech = SpeechEngine(settings)

        # Repositories
        reminder_repo = ReminderRepository(self._db)
        log_repo = CommandLogRepository(self._db)

        # Handlers (order matters — more specific patterns first)
        weather_handler = WeatherHandler(settings)
        news_handler = NewsHandler(settings)

        self._closeable_handlers = [weather_handler, news_handler]

        handlers = [
            DateTimeHandler(),
            weather_handler,
            news_handler,
            ReminderHandler(reminder_repo),
            SystemHandler(),
            SearchHandler(),
        ]

        # Router and scheduler
        self._router = CommandRouter(handlers, log_repo=log_repo)
        self._scheduler = ReminderScheduler(reminder_repo, self._speech)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "VoiceAssistant":
        return self

    async def __aexit__(self, *_) -> None:
        await self.shutdown()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the main voice interaction loop."""
        self._running = True
        self._scheduler.start()
        self._install_signal_handlers()

        self._greet()

        consecutive_errors = 0
        max_consecutive_errors = 5

        while self._running:
            try:
                command = await self._speech.listen()
            except SpeechRecognitionError as exc:
                logger.debug("Recognition error: %s", exc)
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    self._speech.speak(
                        "I'm having trouble hearing you. "
                        "Please check your microphone and try again."
                    )
                    consecutive_errors = 0
                continue
            except MicrophoneNotFoundError:
                logger.critical("No microphone detected — exiting.")
                self._speech.speak(
                    "No microphone detected. "
                    "Please connect a microphone and restart."
                )
                break
            except Exception:
                logger.exception("Unexpected error during listen()")
                consecutive_errors += 1
                continue

            consecutive_errors = 0

            if self._is_exit_command(command):
                self._speech.speak(
                    f"Goodbye! Have a great day."
                )
                break

            response = await self._router.route(command)
            if response.speak:
                self._speech.speak(response.text)

        await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully tear down all sub-systems."""
        if not self._running:
            return
        self._running = False
        logger.info("Shutting down %s…", self._settings.app_name)
        self._scheduler.stop()
        for handler in self._closeable_handlers:
            if hasattr(handler, "close"):
                await handler.close()
        self._speech.shutdown()
        self._db.dispose()
        logger.info("Shutdown complete.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _greet(self) -> None:
        name = self._settings.assistant_name
        self._speech.speak(
            f"Hello! I'm {name}, your voice assistant. "
            "I can help you with weather, news, reminders, opening apps, "
            "and web searches. How can I help you today?"
        )

    @staticmethod
    def _is_exit_command(command: str) -> bool:
        return any(phrase in command for phrase in _EXIT_PHRASES)

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self.shutdown()),
                )
            except NotImplementedError:
                # Windows does not support loop.add_signal_handler
                pass

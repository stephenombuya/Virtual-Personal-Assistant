"""
Command router — maps a normalised text command to the correct handler
and records the result in the audit log.
"""

from __future__ import annotations

import time
from typing import List, Optional

from assistant.database.repository import CommandLogRepository
from assistant.handlers.base import BaseHandler, HandlerResponse
from assistant.utils.logger import get_logger

logger = get_logger(__name__)

_FALLBACK_RESPONSE = HandlerResponse(
    text=(
        "I'm sorry, I didn't understand that. "
        "You can ask me about the weather, news, time, "
        "set reminders, open apps, or search the web."
    ),
    success=False,
)


class CommandRouter:
    """
    Iterates over registered handlers in priority order and delegates
    the command to the first handler that claims it.
    """

    def __init__(
        self,
        handlers: List[BaseHandler],
        log_repo: Optional[CommandLogRepository] = None,
    ) -> None:
        self._handlers = handlers
        self._log_repo = log_repo

    def register(self, handler: BaseHandler) -> None:
        self._handlers.append(handler)

    async def route(self, command: str) -> HandlerResponse:
        """
        Find the appropriate handler and execute it.

        Args:
            command: Normalised (lowercased, stripped) voice command.

        Returns:
            A HandlerResponse (never raises).
        """
        start = time.perf_counter()
        matched_handler: Optional[str] = None
        response = _FALLBACK_RESPONSE

        for handler in self._handlers:
            if handler.can_handle(command):
                matched_handler = type(handler).__name__
                logger.info("Routing '%s' → %s", command, matched_handler)
                try:
                    response = await handler.handle(command)
                except Exception:
                    logger.exception(
                        "Unhandled exception in %s", matched_handler
                    )
                    response = HandlerResponse.error(
                        "Something went wrong processing your request. Please try again."
                    )
                break

        duration_ms = int((time.perf_counter() - start) * 1000)

        if self._log_repo and matched_handler:
            try:
                self._log_repo.record(
                    raw_input=command,
                    handler=matched_handler,
                    success=response.success,
                    error_message=None if response.success else response.text,
                    duration_ms=duration_ms,
                )
            except Exception:
                logger.warning("Failed to write command log", exc_info=True)

        logger.debug(
            "Command processed in %dms — success=%s", duration_ms, response.success
        )
        return response

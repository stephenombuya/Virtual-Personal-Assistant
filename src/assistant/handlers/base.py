"""
Base handler contract that all command handlers must implement.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HandlerResponse:
    """Structured response returned by every handler."""

    text: str
    success: bool = True
    speak: bool = True
    data: Optional[dict] = field(default=None)

    @classmethod
    def error(cls, message: str) -> "HandlerResponse":
        return cls(text=message, success=False)


class BaseHandler(ABC):
    """
    Abstract base class for all command handlers.

    Subclasses must implement:
        - ``patterns`` – list of regex strings that trigger this handler.
        - ``handle`` – process the matched command and return a HandlerResponse.
    """

    @property
    @abstractmethod
    def patterns(self) -> List[str]:
        """Return a list of regex patterns (case-insensitive) this handler matches."""

    def can_handle(self, command: str) -> bool:
        """Return True if any pattern matches the given command string."""
        return any(
            re.search(pattern, command, re.IGNORECASE) for pattern in self.patterns
        )

    @abstractmethod
    async def handle(self, command: str) -> HandlerResponse:
        """
        Process the command and return a structured response.

        Args:
            command: The normalised text command from the user.

        Returns:
            HandlerResponse with text to speak and optional metadata.
        """

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__}>"

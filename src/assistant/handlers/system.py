"""
System application launcher handler.

Handles commands like:
  - "open Chrome"
  - "open Notepad"
  - "launch calculator"
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from typing import Dict, List, Optional

from assistant.handlers.base import BaseHandler, HandlerResponse
from assistant.utils.logger import get_logger

logger = get_logger(__name__)

OS = platform.system().lower()  # "linux", "darwin", "windows"

# Normalised app name → per-OS launch command
_APP_MAP: Dict[str, Dict[str, List[str]]] = {
    "chrome": {
        "linux": ["google-chrome", "--new-window"],
        "darwin": ["open", "-a", "Google Chrome"],
        "windows": ["start", "chrome"],
    },
    "firefox": {
        "linux": ["firefox"],
        "darwin": ["open", "-a", "Firefox"],
        "windows": ["start", "firefox"],
    },
    "calculator": {
        "linux": ["gnome-calculator"],
        "darwin": ["open", "-a", "Calculator"],
        "windows": ["calc"],
    },
    "notepad": {
        "linux": ["gedit"],
        "darwin": ["open", "-a", "TextEdit"],
        "windows": ["notepad"],
    },
    "terminal": {
        "linux": ["x-terminal-emulator"],
        "darwin": ["open", "-a", "Terminal"],
        "windows": ["cmd"],
    },
    "files": {
        "linux": ["nautilus"],
        "darwin": ["open", "."],
        "windows": ["explorer"],
    },
    "spotify": {
        "linux": ["spotify"],
        "darwin": ["open", "-a", "Spotify"],
        "windows": ["start", "spotify"],
    },
    "vscode": {
        "linux": ["code"],
        "darwin": ["code"],
        "windows": ["code"],
    },
    "word": {
        "darwin": ["open", "-a", "Microsoft Word"],
        "windows": ["start", "winword"],
    },
    "excel": {
        "darwin": ["open", "-a", "Microsoft Excel"],
        "windows": ["start", "excel"],
    },
}

# Aliases that map common spoken names to canonical keys
_ALIASES: Dict[str, str] = {
    "google chrome": "chrome",
    "web browser": "chrome",
    "browser": "chrome",
    "text editor": "notepad",
    "text edit": "notepad",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "file manager": "files",
    "file explorer": "files",
    "calc": "calculator",
    "cmd": "terminal",
    "command prompt": "terminal",
    "bash": "terminal",
}


def _resolve_app(spoken: str) -> Optional[str]:
    """Resolve spoken app name to a canonical key."""
    spoken = spoken.lower().strip()
    if spoken in _ALIASES:
        return _ALIASES[spoken]
    if spoken in _APP_MAP:
        return spoken
    # Partial match
    for key in _APP_MAP:
        if key in spoken or spoken in key:
            return key
    return None


class SystemHandler(BaseHandler):
    """Launches system applications via voice command."""

    @property
    def patterns(self) -> List[str]:
        return [
            r"\b(open|launch|start|run)\b.+",
        ]

    async def handle(self, command: str) -> HandlerResponse:
        match = re.search(
            r"\b(?:open|launch|start|run)\s+(.+?)(?:\s+please)?$",
            command,
            re.IGNORECASE,
        )
        if not match:
            return HandlerResponse.error(
                "I didn't catch which application to open. "
                "Try saying 'open Chrome' or 'launch Calculator'."
            )

        app_spoken = match.group(1).strip()
        app_key = _resolve_app(app_spoken)

        if not app_key:
            return HandlerResponse.error(
                f"I don't know how to open '{app_spoken}'. "
                f"Supported apps include: {', '.join(sorted(_APP_MAP))}."
            )

        os_commands = _APP_MAP.get(app_key, {})
        command_args = os_commands.get(OS)

        if not command_args:
            return HandlerResponse.error(
                f"Opening {app_key} isn't supported on your operating system."
            )

        # Verify the binary exists (skip for shell built-ins like "start")
        binary = command_args[0]
        if binary not in ("start", "open") and not shutil.which(binary):
            return HandlerResponse.error(
                f"I couldn't find {app_key} installed on your system."
            )

        try:
            subprocess.Popen(
                command_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=(OS == "windows"),
            )
            return HandlerResponse(
                text=f"Opening {app_key.title()} for you.",
                data={"app": app_key, "command": command_args},
            )
        except Exception as exc:
            logger.exception("Failed to launch %s: %s", app_key, exc)
            return HandlerResponse.error(f"I had trouble launching {app_key}.")

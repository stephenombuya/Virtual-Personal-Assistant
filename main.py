#!/usr/bin/env python3
"""
Virtual Personal Assistant — entry point.

Run with:
    python main.py
"""

from __future__ import annotations

import asyncio
import sys

from assistant.config.settings import get_settings
from assistant.core.assistant import VoiceAssistant
from assistant.utils.logger import configure_logging, get_logger


def main() -> None:
    settings = get_settings()

    configure_logging(
        level=settings.log_level.value,
        log_file=settings.log_file,
    )

    logger = get_logger(__name__)
    logger.info(
        "Starting %s v%s (debug=%s)",
        settings.app_name,
        settings.app_version,
        settings.debug,
    )

    try:
        asyncio.run(_run(settings))
    except KeyboardInterrupt:
        logger.info("Interrupted by user — exiting.")
        sys.exit(0)
    except Exception:
        logger.critical("Fatal error — assistant terminated.", exc_info=True)
        sys.exit(1)


async def _run(settings) -> None:
    async with VoiceAssistant(settings) as assistant:
        await assistant.run()


if __name__ == "__main__":
    main()

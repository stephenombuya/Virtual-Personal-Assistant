"""
Tests for the CommandRouter.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from assistant.core.command_router import CommandRouter
from assistant.handlers.base import BaseHandler, HandlerResponse


class AlwaysHandler(BaseHandler):
    """Handler that always claims the command."""

    @property
    def patterns(self):
        return [r".*"]

    async def handle(self, command: str) -> HandlerResponse:
        return HandlerResponse(text="Always handled", data={"input": command})


class NeverHandler(BaseHandler):
    """Handler that never claims the command."""

    @property
    def patterns(self):
        return [r"^NEVER_MATCH_THIS_STRING$"]

    async def handle(self, command: str) -> HandlerResponse:  # pragma: no cover
        return HandlerResponse(text="Should never run")


class ErrorHandler(BaseHandler):
    """Handler that raises inside handle()."""

    @property
    def patterns(self):
        return [r".*"]

    async def handle(self, command: str) -> HandlerResponse:
        raise ValueError("Simulated handler crash")


class TestCommandRouter:
    @pytest.mark.asyncio
    async def test_routes_to_matching_handler(self):
        router = CommandRouter([AlwaysHandler()])
        response = await router.route("anything")
        assert response.success
        assert response.text == "Always handled"

    @pytest.mark.asyncio
    async def test_returns_fallback_when_no_handler_matches(self):
        router = CommandRouter([NeverHandler()])
        response = await router.route("something unrecognised")
        assert not response.success
        assert "didn't understand" in response.text.lower()

    @pytest.mark.asyncio
    async def test_first_matching_handler_wins(self):
        first = AlwaysHandler()
        second = AlwaysHandler()

        called = []

        async def track_first(cmd):
            called.append("first")
            return HandlerResponse(text="first")

        async def track_second(cmd):  # pragma: no cover
            called.append("second")
            return HandlerResponse(text="second")

        first.handle = track_first  # type: ignore
        second.handle = track_second  # type: ignore

        router = CommandRouter([first, second])
        response = await router.route("test")
        assert called == ["first"]

    @pytest.mark.asyncio
    async def test_handler_exception_returns_error_response(self):
        router = CommandRouter([ErrorHandler()])
        response = await router.route("trigger crash")
        assert not response.success
        assert "went wrong" in response.text.lower()

    @pytest.mark.asyncio
    async def test_logs_command_when_repo_provided(self):
        log_repo = MagicMock()
        router = CommandRouter([AlwaysHandler()], log_repo=log_repo)
        await router.route("test command")
        log_repo.record.assert_called_once()
        call_kwargs = log_repo.record.call_args[1]
        assert call_kwargs["success"] is True
        assert call_kwargs["handler"] == "AlwaysHandler"

    @pytest.mark.asyncio
    async def test_register_adds_handler(self):
        router = CommandRouter([NeverHandler()])
        router.register(AlwaysHandler())
        response = await router.route("anything")
        assert response.success

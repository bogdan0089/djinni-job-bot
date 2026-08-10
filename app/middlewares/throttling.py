import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User


class ThrottlingMiddleware(BaseMiddleware):
    """Drops updates that arrive faster than `rate` seconds apart per user.

    Prevents a user from spamming `/jobs` and turning the bot into a
    request amplifier against Djinni.
    """

    MAX_TRACKED_USERS = 10_000

    def __init__(self, rate: float = 0.7) -> None:
        self.rate = rate
        self._last_seen: dict[int, float] = {}

    def _prune(self, now: float) -> None:
        """Keep the tracking dict from growing without bound."""
        if len(self._last_seen) <= self.MAX_TRACKED_USERS:
            return
        cutoff = now - self.rate
        self._last_seen = {k: v for k, v in self._last_seen.items() if v > cutoff}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or self.rate <= 0:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last_seen.get(user.id)
        if last is not None and now - last < self.rate:
            return None  # silently ignore — answering would double the flood
        self._last_seen[user.id] = now
        self._prune(now)
        return await handler(event, data)

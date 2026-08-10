from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.repository import UserRepository
from app.services.job_service import JobService
from app.services.parser_service import ParserService
from app.services.user_service import UserService


class DbSessionMiddleware(BaseMiddleware):
    """Opens one session per update and injects ready-to-use services.

    Handlers receive `user_service` / `job_service` instead of rebuilding the
    session → repository → service chain themselves. The transaction is
    committed once, after the handler returns without raising.
    """

    def __init__(self, session_factory: async_sessionmaker, parser: ParserService) -> None:
        self.session_factory = session_factory
        self.parser = parser

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            data["session"] = session
            data["user_service"] = UserService(repo)
            data["job_service"] = JobService(repo, self.parser)
            result = await handler(event, data)
            await session.commit()
            return result

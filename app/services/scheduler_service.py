import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import ParserError
from app.db.models import User
from app.db.repository import UserRepository
from app.services.job_service import JobService
from app.services.parser_service import ParserService
from app.services.user_service import UserService
from app.utils.text import build_vacancy_messages

logger = logging.getLogger(__name__)

# Telegram allows ~30 messages/second to different chats
SEND_DELAY_SECONDS = 0.05


class SchedulerService:
    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker,
        parser: ParserService,
    ) -> None:
        self.bot = bot
        self.session_factory = session_factory
        self.parser = parser

    async def send_daily_digest(self) -> None:
        """Send fresh vacancies to every subscriber.

        Each user is processed in its own transaction: a blocked bot, a
        Djinni outage or a malformed filter affects that user only and never
        aborts the run for everyone else.
        """
        async with self.session_factory() as session:
            users = await UserService(UserRepository(session)).get_subscribers()

        logger.info("Daily digest started for %d subscriber(s)", len(users))
        delivered = 0
        for user in users:
            try:
                if await self._process_user(user):
                    delivered += 1
            except Exception:
                # Deliberately broad: one user must never abort the whole run
                logger.exception("Daily digest failed for user %s", user.telegram_id)
            await asyncio.sleep(SEND_DELAY_SECONDS)
        logger.info("Daily digest finished, %d/%d users notified", delivered, len(users))

    async def _process_user(self, user: User) -> bool:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            job_service = JobService(repo, self.parser)
            # Re-attach to this session; the user may have unsubscribed since the scan
            fresh_user = await repo.get_by_telegram_id(user.telegram_id)
            if fresh_user is None or not fresh_user.is_active:
                return False

            try:
                vacancies = await job_service.fetch_new_for(fresh_user)
            except ParserError as exc:
                logger.warning("Skipping user %s: %s", user.telegram_id, exc)
                return False

            if not vacancies:
                await session.commit()
                return False

            messages = build_vacancy_messages(
                vacancies, header=f"<b>{len(vacancies)} new vacancies for you</b>"
            )
            try:
                for text in messages:
                    await self._send(fresh_user.telegram_id, text)
            except TelegramForbiddenError:
                # User blocked the bot — stop wasting requests on them
                logger.info("User %s blocked the bot, deactivating", user.telegram_id)
                fresh_user.is_active = False
                await session.commit()
                return False

            # Committed only after a successful delivery: if sending raises,
            # the rollback un-marks the vacancies and they are retried tomorrow.
            await session.commit()
            return True

    async def _send(self, chat_id: int, text: str) -> None:
        try:
            await self.bot.send_message(chat_id, text, disable_web_page_preview=True)
        except TelegramRetryAfter as exc:
            logger.warning("Flood limit hit, sleeping %ss", exc.retry_after)
            await asyncio.sleep(exc.retry_after)
            await self.bot.send_message(chat_id, text, disable_web_page_preview=True)

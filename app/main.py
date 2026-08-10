import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.session import dispose_db, init_db, session_factory
from app.handlers import build_router
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.services.parser_service import ParserService
from app.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="jobs", description="Fresh vacancies right now"),
    BotCommand(command="filters", description="Set stack, salary, experience"),
    BotCommand(command="me", description="Show my filters"),
    BotCommand(command="reset", description="Clear my filters"),
    BotCommand(command="stop", description="Pause the daily digest"),
    BotCommand(command="help", description="How this bot works"),
]


def create_dispatcher(parser: ParserService) -> Dispatcher:
    dispatcher = Dispatcher()
    router = build_router()

    for observer in (router.message, router.callback_query):
        observer.middleware(ThrottlingMiddleware(settings.THROTTLE_RATE))
        observer.middleware(DbSessionMiddleware(session_factory, parser))

    dispatcher.include_router(router)
    return dispatcher


def create_scheduler(scheduler_service: SchedulerService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.tzinfo)
    scheduler.add_job(
        scheduler_service.send_daily_digest,
        trigger="cron",
        hour=settings.DIGEST_HOUR,
        minute=settings.DIGEST_MINUTE,
        id="daily_digest",
        # A restart must not fire yesterday's missed run, and two overlapping
        # digests would double-send.
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )
    return scheduler


async def main() -> None:
    setup_logging(settings.LOG_LEVEL)
    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    parser = ParserService()
    scheduler = create_scheduler(SchedulerService(bot, session_factory, parser))
    dispatcher = create_dispatcher(parser)

    try:
        try:
            await bot.set_my_commands(COMMANDS)
        except TelegramUnauthorizedError:
            # A wrong token is the most common deploy mistake; a traceback here
            # buries the one line that actually matters.
            logger.error("BOT_TOKEN is rejected by Telegram. Check it with @BotFather.")
            return
        scheduler.start()
        logger.info(
            "Bot started. Daily digest at %02d:%02d %s",
            settings.DIGEST_HOUR,
            settings.DIGEST_MINUTE,
            settings.TIMEZONE,
        )
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        logger.info("Shutting down…")
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await parser.close()
        await bot.session.close()
        await dispose_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopped by user")

from aiogram import Bot, Dispatcher
import asyncio
from handlers.handlers_start import router_start
from handlers.handlers_filters import router_filters
from handlers.handlers_jobs import router_jobs
from core.config import settings
from database.models import init_db
from services.scheduler_service import SchedulerService
from apscheduler.schedulers.asyncio import AsyncIOScheduler


async def main():
    await init_db()
    bot = Bot(token=settings.BOT_TOKEN)
    scheduler = AsyncIOScheduler()
    scheduler_service = SchedulerService(bot)
    scheduler.add_job(scheduler_service.send_daily_jobs, "cron", hour=9, minute=0)
    scheduler.start()
    dispatcher = Dispatcher()
    dispatcher.include_router(router_start)
    dispatcher.include_router(router_filters)
    dispatcher.include_router(router_jobs)
    await dispatcher.start_polling(bot)


asyncio.run(main())

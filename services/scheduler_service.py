from aiogram import Bot
from database.models import AsyncSessionLocal
from database.queries import RepositoryBot
from services.parser_service import ParserService
from services.user_service import UserService


class SchedulerService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_daily_jobs(self):
        async with AsyncSessionLocal() as session:
            repo = RepositoryBot(session)
            service_parser = ParserService()
            service_user = UserService(repo)
            users = await service_user.get_all_is_active()
            for user in users:
                jobs = await service_parser.get_djinni_jobs(stack=user.stack, experience=user.experience)
                for job in jobs:
                    if await repo.is_job_sent(user.id, job['url']):
                        continue
                    text = f"{job['title']}\n{job['url']}"
                    await self.bot.send_message(user.telegram_id, text)
                    await repo.save_sent_job(user.id, job['url'])

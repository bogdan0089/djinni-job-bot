from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.models import AsyncSessionLocal
from database.queries import RepositoryBot
from services.user_service import UserService
from services.parser_service import ParserService

router_jobs = Router()


@router_jobs.message(Command("jobs"))
async def get_jobs(message: Message):
    async with AsyncSessionLocal() as session:
        repo = RepositoryBot(session)
        service = UserService(repo)
        user = await service.get_user(message.from_user.id)

    parser = ParserService()
    jobs = await parser.get_djinni_jobs(stack=user.stack, experience=user.experience)

    if not jobs:
        await message.answer("No vacancies found. Try changing your filters with /filters")
        return

    for job in jobs:
        text = (
            f"{job['title']}\n"
            f"{job['url']}"
        )
        await message.answer(text)

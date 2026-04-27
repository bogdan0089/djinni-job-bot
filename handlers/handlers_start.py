from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from database.models import AsyncSessionLocal
from database.queries import RepositoryBot
from services.user_service import UserService
from schemas.user_schema import RegisterUser


router_start = Router()
        
@router_start.message(CommandStart())
async def start(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username

    data = RegisterUser(
        telegram_id=telegram_id,
        username=username
    )

    async with AsyncSessionLocal() as session:
        repo = RepositoryBot(session)
        service = UserService(repo)
        await service.register_user(data)

    await message.answer(
        "Welcome to Job Search Bot!\n\n"
        "I will send you new vacancies from Djinni every day.\n\n"
        "/filters — set up your stack, salary, experience\n"
        "/jobs — get vacancies right now"
    )


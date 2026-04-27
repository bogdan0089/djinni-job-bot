from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import AsyncSessionLocal
from database.queries import RepositoryBot
from services.user_service import UserService
from schemas.user_schema import UpdateFilters

router_filters = Router()


class FilterStates(StatesGroup):
    waiting_stack = State()
    waiting_salary = State()
    waiting_experience = State()


@router_filters.message(Command("filters"))
async def start_filters(message: Message, state: FSMContext):
    await state.set_state(FilterStates.waiting_stack)
    await message.answer("What is your tech stack? (e.g. Python, FastAPI, PostgreSQL)\nOr send /skip to skip.")


@router_filters.message(FilterStates.waiting_stack)
async def set_stack(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(stack=message.text)
    await state.set_state(FilterStates.waiting_salary)
    await message.answer("Minimum salary in USD? (e.g. 1500)\nOr send /skip to skip.")


@router_filters.message(FilterStates.waiting_salary)
async def set_salary(message: Message, state: FSMContext):
    if message.text != "/skip":
        if not message.text.isdigit():
            await message.answer("Please enter a number. Try again.")
            return
        await state.update_data(min_salary=int(message.text))
    await state.set_state(FilterStates.waiting_experience)
    await message.answer("Experience level?\nSend: junior / middle / senior\nOr /skip.")


@router_filters.message(FilterStates.waiting_experience)
async def set_experience(message: Message, state: FSMContext):
    if message.text != "/skip":
        if message.text.lower() not in ["junior", "middle", "senior"]:
            await message.answer("Please send: junior, middle or senior.")
            return
        await state.update_data(experience=message.text.lower())

    data = await state.get_data()
    await state.clear()

    filters = UpdateFilters(**data)

    async with AsyncSessionLocal() as session:
        repo = RepositoryBot(session)
        service = UserService(repo)
        await service.update_filters(message.from_user.id, filters)

    await message.answer("Filters saved! Use /jobs to get vacancies.")

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.models import User
from app.keyboards.common import BTN_ME, BTN_PAUSE, BTN_RESUME, main_menu
from app.schemas.user import RegisterUser
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="start")

HELP_TEXT = (
    "<b>Djinni Job Bot</b>\n\n"
    "/jobs — fresh vacancies right now\n"
    "/filters — set stack, salary and experience\n"
    "/me — show your current filters\n"
    "/reset — clear all filters\n"
    "/stop — pause the daily digest\n"
    "/help — this message"
)


def _describe(user: User) -> str:
    return (
        f"Stack: {user.stack or 'any'}\n"
        f"Experience: {user.experience or 'any'}\n"
        f"Min salary: {f'${user.min_salary}' if user.min_salary else 'any'}"
    )


@router.message(or_f(CommandStart(), F.text == BTN_RESUME))
async def cmd_start(message: Message, state: FSMContext, user_service: UserService) -> None:
    await state.clear()
    await user_service.register(
        RegisterUser(telegram_id=message.from_user.id, username=message.from_user.username)
    )
    logger.info("User %s registered", message.from_user.id)
    await message.answer(
        "Welcome! I send you new Djinni vacancies every morning.\n\n"
        "Start with /filters to tell me what you are looking for.\n\n" + HELP_TEXT,
        reply_markup=main_menu(is_active=True),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, user_service: UserService) -> None:
    await message.answer(
        HELP_TEXT,
        reply_markup=main_menu(await user_service.is_subscribed(message.from_user.id)),
    )


@router.message(or_f(Command("me"), F.text == BTN_ME))
async def cmd_me(message: Message, user_service: UserService) -> None:
    user = await user_service.get(message.from_user.id)
    await message.answer(
        f"<b>Your filters</b>\n{_describe(user)}\n"
        f"Daily digest: {'on' if user.is_active else 'off'}",
        reply_markup=main_menu(user.is_active),
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, user_service: UserService) -> None:
    user = await user_service.reset_filters(message.from_user.id)
    await message.answer(
        "Filters cleared. Use /filters to set them again.",
        reply_markup=main_menu(user.is_active),
    )


@router.message(or_f(Command("stop"), F.text == BTN_PAUSE))
async def cmd_stop(message: Message, user_service: UserService) -> None:
    await user_service.set_active(message.from_user.id, active=False)
    await message.answer(
        "Daily digest paused. You can still use /jobs any time.",
        reply_markup=main_menu(is_active=False),
    )

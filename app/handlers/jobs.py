import logging

from aiogram import F, Router
from aiogram.filters import Command, or_f
from aiogram.types import Message

from app.core.exceptions import ParserError
from app.keyboards.common import BTN_JOBS, main_menu
from app.services.job_service import JobService
from app.services.user_service import UserService
from app.utils.text import build_vacancy_messages

logger = logging.getLogger(__name__)
router = Router(name="jobs")


@router.message(or_f(Command("jobs"), F.text == BTN_JOBS))
async def cmd_jobs(
    message: Message, user_service: UserService, job_service: JobService
) -> None:
    user = await user_service.get(message.from_user.id)

    status = await message.answer("Searching Djinni…")
    try:
        vacancies = await job_service.fetch_new_for(user)
    except ParserError as exc:
        logger.warning("Parser failed for user %s: %s", user.telegram_id, exc)
        await status.edit_text("Djinni is not responding right now. Try again in a minute.")
        return

    if not vacancies:
        await status.edit_text(
            "No new vacancies. You have already seen everything that matches "
            "your filters — try widening them with /filters."
        )
        return

    messages = build_vacancy_messages(
        vacancies, header=f"<b>{len(vacancies)} vacancies for you</b>"
    )
    await status.edit_text(messages[0], disable_web_page_preview=True)
    for text in messages[1:]:
        await message.answer(text, disable_web_page_preview=True)

    await message.answer(
        "Want more? Adjust /filters.",
        reply_markup=main_menu(user.is_active),
    )

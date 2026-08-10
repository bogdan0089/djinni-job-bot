from aiogram import F, Router
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.keyboards.common import (
    BTN_FILTERS,
    CANCEL,
    MENU_BUTTONS,
    SKIP,
    experience_levels,
    main_menu,
    skip_or_cancel,
)
from app.schemas.job import Experience
from app.schemas.user import UpdateFilters
from app.services.user_service import UserService
from app.utils.validators import split_keywords

router = Router(name="filters")

MAX_STACK_LENGTH = 255
MAX_SALARY = 1_000_000


class FilterStates(StatesGroup):
    stack = State()
    salary = State()
    experience = State()


def _is_skip(text: str) -> bool:
    return text.lower() in {"/skip", SKIP.lower()}


@router.message(or_f(Command("filters"), F.text == BTN_FILTERS))
async def start_filters(message: Message, state: FSMContext) -> None:
    await state.set_state(FilterStates.stack)
    await message.answer(
        "What is your tech stack? (e.g. <code>Python, FastAPI</code>)\n"
        "Up to 3 keywords are used for the search.",
        reply_markup=skip_or_cancel(),
    )


@router.message(StateFilter(FilterStates), Command("cancel"))
@router.message(StateFilter(FilterStates), F.text.casefold() == CANCEL.casefold())
async def cancel_filters(
    message: Message, state: FSMContext, user_service: UserService
) -> None:
    await state.clear()
    await message.answer(
        "Cancelled. Nothing was changed.",
        reply_markup=main_menu(await user_service.is_subscribed(message.from_user.id)),
    )


@router.message(StateFilter(FilterStates), ~F.text)
async def reject_non_text(message: Message) -> None:
    """Guards every step against stickers, photos and other non-text updates."""
    await message.answer("Please send text, or press Cancel.")


@router.message(FilterStates.stack)
async def set_stack(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not _is_skip(text):
        # A command or a menu button pressed mid-flow is navigation, not a stack
        if text.startswith("/") or text in MENU_BUTTONS:
            await message.answer("Finish the setup or press Cancel.")
            return
        if len(text) > MAX_STACK_LENGTH:
            await message.answer(f"Too long, keep it under {MAX_STACK_LENGTH} characters.")
            return
        if not split_keywords(text, 1):
            # Djinni answers an unknown keyword with the full unfiltered feed,
            # so junk must be rejected here rather than silently searched for.
            await message.answer(
                "That does not look like a tech keyword. "
                "Send it in latin letters, e.g. <code>Python</code> or <code>React</code>."
            )
            return
        await state.update_data(stack=text)

    await state.set_state(FilterStates.salary)
    await message.answer(
        "Minimum salary in USD? (e.g. <code>1500</code>)", reply_markup=skip_or_cancel()
    )


@router.message(FilterStates.salary)
async def set_salary(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not _is_skip(text):
        digits = text.lstrip("$").replace(" ", "")
        if not digits.isdigit() or not 0 < int(digits) <= MAX_SALARY:
            await message.answer("Please send a number between 1 and 1000000.")
            return
        await state.update_data(min_salary=int(digits))

    await state.set_state(FilterStates.experience)
    await message.answer("Your experience level?", reply_markup=experience_levels())


@router.message(FilterStates.experience)
async def set_experience(
    message: Message, state: FSMContext, user_service: UserService
) -> None:
    text = message.text.strip()
    if not _is_skip(text):
        try:
            level = Experience(text.lower())
        except ValueError:
            options = " / ".join(e.value for e in Experience)
            await message.answer(f"Please choose one of: {options}.")
            return
        await state.update_data(experience=level)

    data = await state.get_data()
    await state.clear()

    if not data:
        await message.answer(
            "Nothing to save — all steps were skipped.",
            reply_markup=main_menu(await user_service.is_subscribed(message.from_user.id)),
        )
        return

    user = await user_service.update_filters(message.from_user.id, UpdateFilters(**data))
    await message.answer(
        "Filters saved:\n"
        f"Stack: {user.stack or 'any'}\n"
        f"Experience: {user.experience or 'any'}\n"
        f"Min salary: {f'${user.min_salary}' if user.min_salary else 'any'}\n\n"
        "Use /jobs to get vacancies now.",
        reply_markup=main_menu(user.is_active),
    )

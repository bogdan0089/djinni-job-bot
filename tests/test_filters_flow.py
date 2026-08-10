import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.db.models import User
from app.db.repository import UserRepository
from app.handlers.filters import (
    FilterStates,
    cancel_filters,
    set_experience,
    set_salary,
    set_stack,
    start_filters,
)
from app.keyboards.common import MENU_BUTTONS
from app.services.user_service import UserService


class FakeMessage:
    """Minimal stand-in for aiogram's Message — records what the bot replied."""

    def __init__(self, text: str | None, user_id: int) -> None:
        self.text = text
        self.from_user = type("U", (), {"id": user_id, "username": None})()
        self.replies: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.replies.append(text)


@pytest.fixture
def state() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=1, user_id=1001)
    )


@pytest.fixture
def service(repo: UserRepository) -> UserService:
    return UserService(repo)


async def run_step(handler, text, state, user_id=1001, **kwargs) -> FakeMessage:
    message = FakeMessage(text, user_id)
    await handler(message, state, **kwargs)
    return message


class TestHappyPath:
    async def test_full_flow_saves_every_filter(
        self, state: FSMContext, service: UserService, user: User
    ) -> None:
        await run_step(start_filters, "/filters", state)
        assert await state.get_state() == FilterStates.stack.state

        await run_step(set_stack, "Python, FastAPI", state)
        assert await state.get_state() == FilterStates.salary.state

        await run_step(set_salary, "2000", state)
        assert await state.get_state() == FilterStates.experience.state

        await run_step(set_experience, "middle", state, user_service=service)
        assert await state.get_state() is None

        assert (user.stack, user.min_salary, user.experience) == (
            "Python, FastAPI",
            2000,
            "middle",
        )

    async def test_salary_accepts_a_dollar_sign_and_spaces(
        self, state: FSMContext, service: UserService, user: User
    ) -> None:
        await state.set_state(FilterStates.salary)
        await run_step(set_salary, "$2 500", state)
        await run_step(set_experience, "/skip", state, user_service=service)
        assert user.min_salary == 2500


class TestSkipping:
    async def test_skipped_steps_leave_previous_values_untouched(
        self, state: FSMContext, service: UserService, user: User
    ) -> None:
        user.stack = "Go"
        await state.set_state(FilterStates.stack)
        await run_step(set_stack, "/skip", state)
        await run_step(set_salary, "3000", state)
        await run_step(set_experience, "Skip", state, user_service=service)

        assert user.stack == "Go"  # not overwritten
        assert user.min_salary == 3000
        assert user.experience is None

    async def test_skipping_everything_saves_nothing(
        self, state: FSMContext, service: UserService, user: User
    ) -> None:
        await state.set_state(FilterStates.stack)
        await run_step(set_stack, "/skip", state)
        await run_step(set_salary, "/skip", state)
        message = await run_step(set_experience, "/skip", state, user_service=service)

        assert "Nothing to save" in message.replies[-1]
        assert (user.stack, user.min_salary, user.experience) == (None, None, None)


class TestValidation:
    async def test_non_numeric_salary_keeps_the_user_on_the_same_step(
        self, state: FSMContext
    ) -> None:
        await state.set_state(FilterStates.salary)
        message = await run_step(set_salary, "a lot", state)
        assert await state.get_state() == FilterStates.salary.state
        assert "number" in message.replies[0]

    @pytest.mark.parametrize("value", ["0", "-100", "99999999"])
    async def test_out_of_range_salary_is_rejected(
        self, state: FSMContext, value: str
    ) -> None:
        await state.set_state(FilterStates.salary)
        await run_step(set_salary, value, state)
        assert await state.get_state() == FilterStates.salary.state

    async def test_unknown_experience_keeps_the_user_on_the_same_step(
        self, state: FSMContext, service: UserService
    ) -> None:
        await state.set_state(FilterStates.experience)
        message = await run_step(set_experience, "architect", state, user_service=service)
        assert await state.get_state() == FilterStates.experience.state
        assert "junior" in message.replies[0]

    async def test_a_command_is_not_swallowed_as_a_stack(self, state: FSMContext) -> None:
        await state.set_state(FilterStates.stack)
        message = await run_step(set_stack, "/jobs", state)
        assert await state.get_state() == FilterStates.stack.state
        assert (await state.get_data()) == {}
        assert "Cancel" in message.replies[0]

    async def test_an_over_long_stack_is_rejected(self, state: FSMContext) -> None:
        await state.set_state(FilterStates.stack)
        await run_step(set_stack, "P" * 300, state)
        assert await state.get_state() == FilterStates.stack.state

    @pytest.mark.parametrize("junk", ["✅", "🧐", "1300", "!!!"])
    async def test_a_stack_without_a_searchable_keyword_is_rejected(
        self, state: FSMContext, junk: str
    ) -> None:
        """Djinni returns the full unfiltered feed for an unknown keyword, so
        junk must never be saved as a stack."""
        await state.set_state(FilterStates.stack)
        message = await run_step(set_stack, junk, state)

        assert await state.get_state() == FilterStates.stack.state
        assert await state.get_data() == {}
        assert "latin letters" in message.replies[0]

    @pytest.mark.parametrize("button", sorted(MENU_BUTTONS))
    async def test_a_menu_button_is_not_saved_as_a_stack(
        self, state: FSMContext, button: str
    ) -> None:
        """Pressing a menu button mid-flow is navigation, not an answer."""
        await state.set_state(FilterStates.stack)
        message = await run_step(set_stack, button, state)

        assert await state.get_state() == FilterStates.stack.state
        assert await state.get_data() == {}
        assert "Cancel" in message.replies[0]

    async def test_a_mixed_stack_is_accepted(self, state: FSMContext) -> None:
        await state.set_state(FilterStates.stack)
        await run_step(set_stack, "✅ Python", state)
        assert await state.get_state() == FilterStates.salary.state
        assert (await state.get_data())["stack"] == "✅ Python"


class TestCancel:
    async def test_cancel_clears_the_state_and_saves_nothing(
        self, state: FSMContext, service: UserService, user: User
    ) -> None:
        await state.set_state(FilterStates.salary)
        await state.update_data(stack="Rust")
        message = await run_step(cancel_filters, "Cancel", state, user_service=service)

        assert await state.get_state() is None
        assert await state.get_data() == {}
        assert user.stack is None
        assert "Cancelled" in message.replies[0]

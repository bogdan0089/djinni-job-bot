import pytest

from app.db.repository import UserRepository
from app.keyboards.common import (
    BTN_JOBS,
    BTN_PAUSE,
    BTN_RESUME,
    MENU_BUTTONS,
    experience_levels,
    main_menu,
    skip_or_cancel,
)
from app.schemas.job import Experience
from app.services.user_service import UserService


def labels(markup) -> list[str]:
    return [button.text for row in markup.keyboard for button in row]


class TestMainMenu:
    def test_shows_pause_while_the_digest_is_on(self) -> None:
        assert BTN_PAUSE in labels(main_menu(is_active=True))
        assert BTN_RESUME not in labels(main_menu(is_active=True))

    def test_shows_resume_while_the_digest_is_paused(self) -> None:
        assert BTN_RESUME in labels(main_menu(is_active=False))
        assert BTN_PAUSE not in labels(main_menu(is_active=False))

    def test_every_label_is_a_known_menu_button(self) -> None:
        for state in (True, False):
            assert set(labels(main_menu(state))) <= MENU_BUTTONS

    def test_jobs_button_is_always_present(self) -> None:
        assert BTN_JOBS in labels(main_menu(True))
        assert BTN_JOBS in labels(main_menu(False))


class TestFlowKeyboards:
    def test_skip_or_cancel_offers_both(self) -> None:
        assert labels(skip_or_cancel()) == ["Skip", "Cancel"]

    def test_experience_keyboard_lists_every_level(self) -> None:
        shown = labels(experience_levels())
        assert all(level.value in shown for level in Experience)


class TestSubscriptionState:
    @pytest.fixture
    def service(self, repo: UserRepository) -> UserService:
        return UserService(repo)

    async def test_unknown_user_defaults_to_subscribed(self, service: UserService) -> None:
        assert await service.is_subscribed(999) is True

    async def test_reflects_a_paused_user(self, service: UserService, user) -> None:
        await service.set_active(user.telegram_id, active=False)
        assert await service.is_subscribed(user.telegram_id) is False

    async def test_reflects_an_active_user(self, service: UserService, user) -> None:
        assert await service.is_subscribed(user.telegram_id) is True

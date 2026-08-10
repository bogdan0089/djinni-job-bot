import pytest

from app.core.exceptions import UserNotFoundError
from app.db.models import User
from app.db.repository import UserRepository
from app.schemas.job import Experience
from app.schemas.user import RegisterUser, UpdateFilters
from app.services.user_service import UserService


@pytest.fixture
def service(repo: UserRepository) -> UserService:
    return UserService(repo)


class TestRegister:
    async def test_creates_new_user(self, service: UserService) -> None:
        user = await service.register(RegisterUser(telegram_id=7, username="a"))
        assert user.id is not None

    async def test_is_idempotent(self, service: UserService) -> None:
        first = await service.register(RegisterUser(telegram_id=7, username="a"))
        second = await service.register(RegisterUser(telegram_id=7, username="renamed"))
        assert first.id == second.id
        assert second.username == "renamed"

    async def test_resubscribes_a_stopped_user(self, service: UserService) -> None:
        user = await service.register(RegisterUser(telegram_id=7))
        user.is_active = False
        again = await service.register(RegisterUser(telegram_id=7))
        assert again.is_active is True


class TestGet:
    async def test_raises_for_unknown_user(self, service: UserService) -> None:
        with pytest.raises(UserNotFoundError):
            await service.get(12345)


class TestFilters:
    async def test_partial_update_keeps_other_fields(
        self, service: UserService, user: User
    ) -> None:
        await service.update_filters(
            user.telegram_id,
            UpdateFilters(stack="Python", min_salary=2000, experience=Experience.MIDDLE),
        )
        updated = await service.update_filters(
            user.telegram_id, UpdateFilters(min_salary=3000)
        )
        assert updated.stack == "Python"
        assert updated.experience == "middle"
        assert updated.min_salary == 3000

    async def test_experience_is_stored_as_plain_string(
        self, service: UserService, user: User
    ) -> None:
        updated = await service.update_filters(
            user.telegram_id, UpdateFilters(experience=Experience.SENIOR)
        )
        assert updated.experience == "senior"
        assert type(updated.experience) is str

    async def test_reset_clears_everything(self, service: UserService, user: User) -> None:
        await service.update_filters(user.telegram_id, UpdateFilters(stack="Go"))
        reset = await service.reset_filters(user.telegram_id)
        assert (reset.stack, reset.min_salary, reset.experience) == (None, None, None)

    async def test_invalid_experience_is_rejected_by_the_schema(self) -> None:
        with pytest.raises(ValueError):
            UpdateFilters(experience="architect")

    async def test_negative_salary_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            UpdateFilters(min_salary=-1)

    async def test_a_stack_without_a_latin_keyword_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            UpdateFilters(stack="✅")

    async def test_a_stack_with_a_latin_keyword_is_accepted(self) -> None:
        assert UpdateFilters(stack="C++").stack == "C++"


class TestSubscribers:
    async def test_empty_list_is_not_an_error(self, service: UserService) -> None:
        assert await service.get_subscribers() == []

    async def test_stopped_users_are_excluded(self, service: UserService, user: User) -> None:
        await service.set_active(user.telegram_id, active=False)
        await service.repo.session.flush()
        assert await service.get_subscribers() == []

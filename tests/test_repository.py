from app.db.models import User
from app.db.repository import UserRepository
from app.schemas.user import RegisterUser


class TestUsers:
    async def test_create_and_get(self, repo: UserRepository) -> None:
        created = await repo.create(RegisterUser(telegram_id=42, username="bob"))
        assert created.id is not None

        found = await repo.get_by_telegram_id(42)
        assert found is not None
        assert found.username == "bob"
        assert found.is_active is True

    async def test_get_unknown_returns_none(self, repo: UserRepository) -> None:
        assert await repo.get_by_telegram_id(999) is None

    async def test_get_active_skips_deactivated(self, repo: UserRepository) -> None:
        active = await repo.create(RegisterUser(telegram_id=1))
        await repo.create(RegisterUser(telegram_id=2))
        await repo.deactivate((await repo.get_by_telegram_id(2)).id)
        await repo.session.flush()

        assert [u.id for u in await repo.get_active()] == [active.id]


class TestSentJobs:
    async def test_all_urls_are_new_for_a_fresh_user(
        self, repo: UserRepository, user: User
    ) -> None:
        urls = ["https://a", "https://b"]
        assert await repo.filter_unsent_urls(user.id, urls) == urls

    async def test_marked_urls_are_filtered_out(
        self, repo: UserRepository, user: User
    ) -> None:
        await repo.mark_sent(user.id, ["https://a"])
        assert await repo.filter_unsent_urls(user.id, ["https://a", "https://b"]) == [
            "https://b"
        ]

    async def test_mark_sent_is_idempotent(self, repo: UserRepository, user: User) -> None:
        await repo.mark_sent(user.id, ["https://a"])
        await repo.mark_sent(user.id, ["https://a", "https://a"])
        await repo.session.commit()
        assert await repo.filter_unsent_urls(user.id, ["https://a"]) == []

    async def test_history_is_per_user(self, repo: UserRepository, user: User) -> None:
        other = await repo.create(RegisterUser(telegram_id=2002))
        await repo.mark_sent(user.id, ["https://a"])
        assert await repo.filter_unsent_urls(other.id, ["https://a"]) == ["https://a"]

    async def test_empty_input_is_a_no_op(self, repo: UserRepository, user: User) -> None:
        assert await repo.filter_unsent_urls(user.id, []) == []
        await repo.mark_sent(user.id, [])

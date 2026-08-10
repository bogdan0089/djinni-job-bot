import pytest
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ParserError
from app.db.models import Base
from app.db.repository import UserRepository
from app.schemas.job import Vacancy
from app.schemas.user import RegisterUser
from app.services.scheduler_service import SchedulerService

VACANCIES = [Vacancy(title="Python Dev", url="https://djinni.co/jobs/1")]


class FakeBot:
    def __init__(self, blocked: set[int] | None = None) -> None:
        self.blocked = blocked or set()
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        if chat_id in self.blocked:
            raise TelegramForbiddenError(method=None, message="bot was blocked by the user")
        self.sent.append((chat_id, text))


class FakeParser:
    def __init__(self, failing_stacks: set[str] | None = None) -> None:
        self.failing_stacks = failing_stacks or set()

    async def get_jobs(self, stack=None, experience=None, min_salary=None):
        if stack in self.failing_stacks:
            raise ParserError("Djinni is unreachable")
        return VACANCIES


class ExplodingParser:
    async def get_jobs(self, **kwargs):
        raise RuntimeError("unexpected crash")


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def seed(factory, users: list[tuple[int, str | None]]) -> None:
    async with factory() as session:
        repo = UserRepository(session)
        for telegram_id, stack in users:
            user = await repo.create(RegisterUser(telegram_id=telegram_id))
            user.stack = stack
        await session.commit()


class TestDailyDigest:
    async def test_sends_to_every_subscriber(self, factory) -> None:
        await seed(factory, [(1, "Python"), (2, "Go")])
        bot = FakeBot()
        await SchedulerService(bot, factory, FakeParser()).send_daily_digest()
        assert sorted(chat for chat, _ in bot.sent) == [1, 2]

    async def test_a_blocked_user_does_not_stop_the_run(self, factory) -> None:
        await seed(factory, [(1, "Python"), (2, "Python"), (3, "Python")])
        bot = FakeBot(blocked={2})
        await SchedulerService(bot, factory, FakeParser()).send_daily_digest()
        assert sorted(chat for chat, _ in bot.sent) == [1, 3]

    async def test_a_blocked_user_is_deactivated(self, factory) -> None:
        await seed(factory, [(1, "Python")])
        await SchedulerService(FakeBot(blocked={1}), factory, FakeParser()).send_daily_digest()
        async with factory() as session:
            user = await UserRepository(session).get_by_telegram_id(1)
            assert user.is_active is False

    async def test_a_parser_outage_for_one_user_does_not_stop_the_run(
        self, factory
    ) -> None:
        await seed(factory, [(1, "Broken"), (2, "Python")])
        bot = FakeBot()
        parser = FakeParser(failing_stacks={"Broken"})
        await SchedulerService(bot, factory, parser).send_daily_digest()
        assert [chat for chat, _ in bot.sent] == [2]

    async def test_an_unexpected_crash_for_one_user_does_not_stop_the_run(
        self, factory
    ) -> None:
        await seed(factory, [(1, "Python")])
        bot = FakeBot()
        # Must not raise — the scheduler swallows and logs per-user failures
        await SchedulerService(bot, factory, ExplodingParser()).send_daily_digest()
        assert bot.sent == []

    async def test_vacancies_are_not_repeated_the_next_day(self, factory) -> None:
        await seed(factory, [(1, "Python")])
        bot = FakeBot()
        service = SchedulerService(bot, factory, FakeParser())
        await service.send_daily_digest()
        await service.send_daily_digest()
        assert len(bot.sent) == 1

    async def test_a_failed_send_leaves_vacancies_unmarked_for_a_retry(
        self, factory
    ) -> None:
        await seed(factory, [(1, "Python")])

        class FlakyBot(FakeBot):
            def __init__(self) -> None:
                super().__init__()
                self.attempts = 0

            async def send_message(self, chat_id, text, **kwargs):
                self.attempts += 1
                if self.attempts == 1:
                    raise RuntimeError("network blip")
                await super().send_message(chat_id, text, **kwargs)

        bot = FlakyBot()
        service = SchedulerService(bot, factory, FakeParser())
        await service.send_daily_digest()
        assert bot.sent == []
        await service.send_daily_digest()
        assert len(bot.sent) == 1

    async def test_no_subscribers_is_not_an_error(self, factory) -> None:
        bot = FakeBot()
        await SchedulerService(bot, factory, FakeParser()).send_daily_digest()
        assert bot.sent == []

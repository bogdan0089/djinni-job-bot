import pytest

from app.db.models import User
from app.db.repository import UserRepository
from app.schemas.job import Vacancy
from app.services.job_service import JobService


class FakeParser:
    """Stands in for ParserService — no network, records the filters it received."""

    def __init__(self, vacancies: list[Vacancy]) -> None:
        self.vacancies = vacancies
        self.calls: list[dict] = []

    async def get_jobs(self, stack=None, experience=None, min_salary=None):
        self.calls.append(
            {"stack": stack, "experience": experience, "min_salary": min_salary}
        )
        return self.vacancies


@pytest.fixture
def vacancies() -> list[Vacancy]:
    return [
        Vacancy(title="Python Dev", url="https://djinni.co/jobs/1"),
        Vacancy(title="Django Dev", url="https://djinni.co/jobs/2"),
    ]


class TestFetchNewFor:
    async def test_returns_everything_on_the_first_call(
        self, repo: UserRepository, user: User, vacancies: list[Vacancy]
    ) -> None:
        service = JobService(repo, FakeParser(vacancies))
        assert len(await service.fetch_new_for(user)) == 2

    async def test_never_returns_the_same_vacancy_twice(
        self, repo: UserRepository, user: User, vacancies: list[Vacancy]
    ) -> None:
        service = JobService(repo, FakeParser(vacancies))
        await service.fetch_new_for(user)
        assert await service.fetch_new_for(user) == []

    async def test_only_the_new_vacancy_is_returned(
        self, repo: UserRepository, user: User, vacancies: list[Vacancy]
    ) -> None:
        parser = FakeParser(vacancies)
        service = JobService(repo, parser)
        await service.fetch_new_for(user)

        extra = Vacancy(title="Go Dev", url="https://djinni.co/jobs/3")
        parser.vacancies = [*vacancies, extra]
        assert await service.fetch_new_for(user) == [extra]

    async def test_preview_mode_does_not_consume_vacancies(
        self, repo: UserRepository, user: User, vacancies: list[Vacancy]
    ) -> None:
        service = JobService(repo, FakeParser(vacancies))
        await service.fetch_new_for(user, mark_as_sent=False)
        assert len(await service.fetch_new_for(user)) == 2

    async def test_user_filters_are_forwarded_to_the_parser(
        self, repo: UserRepository, user: User, vacancies: list[Vacancy]
    ) -> None:
        user.stack = "Python"
        user.experience = "middle"
        user.min_salary = 2500
        parser = FakeParser(vacancies)
        await JobService(repo, parser).fetch_new_for(user)
        assert parser.calls == [
            {"stack": "Python", "experience": "middle", "min_salary": 2500}
        ]

    async def test_empty_feed(self, repo: UserRepository, user: User) -> None:
        assert await JobService(repo, FakeParser([])).fetch_new_for(user) == []

    async def test_duplicate_urls_in_one_feed_are_collapsed(
        self, repo: UserRepository, user: User
    ) -> None:
        duplicated = [
            Vacancy(title="A", url="https://djinni.co/jobs/1"),
            Vacancy(title="A again", url="https://djinni.co/jobs/1"),
        ]
        result = await JobService(repo, FakeParser(duplicated)).fetch_new_for(user)
        assert len(result) == 1

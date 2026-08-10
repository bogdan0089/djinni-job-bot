from urllib.parse import parse_qs, urlparse

import pytest

from app.core.exceptions import ParserError
from app.schemas.job import Experience, Vacancy
from app.services.parser_service import ParserService, _split_stack

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>Senior Python Developer</title><link>https://djinni.co/jobs/1</link></item>
  <item><title>Middle Python Developer</title><link>https://djinni.co/jobs/2</link></item>
  <item><title>Tech Lead Python</title><link>https://djinni.co/jobs/3</link></item>
  <item><title>Broken item without a link</title></item>
</channel></rss>
"""


class TestStackSplitting:
    @pytest.mark.parametrize(
        ("stack", "expected"),
        [
            ("Python, FastAPI, PostgreSQL", ["Python", "FastAPI", "PostgreSQL"]),
            ("Python/Django", ["Python", "Django"]),
            ("Python Python", ["Python"]),  # duplicates collapse
            ("a, b, c, d, e", ["a", "b", "c"]),  # capped at 3 keywords
            ("C++, C#, .NET, Node.js", ["C++", "C#", ".NET"]),  # punctuation survives
            (None, ["Python"]),
            ("   ", ["Python"]),
        ],
    )
    def test_split(self, stack: str | None, expected: list[str]) -> None:
        assert _split_stack(stack) == expected

    @pytest.mark.parametrize("junk", ["✅", "🧐 🤝", "1300", "!!!", "。。。"])
    def test_junk_never_reaches_djinni(self, junk: str) -> None:
        """Djinni answers an unknown keyword with the full unfiltered feed,
        so a junk stack must fall back to the default instead of being searched."""
        assert _split_stack(junk) == ["Python"]

    def test_junk_is_dropped_but_real_keywords_are_kept(self) -> None:
        assert _split_stack("✅ Python 🧐 Django") == ["Python", "Django"]


class TestFeedParsing:
    def test_skips_items_without_link(self) -> None:
        vacancies = ParserService._parse_feed(RSS)
        assert [v.url for v in vacancies] == [
            "https://djinni.co/jobs/1",
            "https://djinni.co/jobs/2",
            "https://djinni.co/jobs/3",
        ]
    def test_empty_feed(self) -> None:
        assert ParserService._parse_feed("<rss><channel></channel></rss>") == []


class TestFilters:
    @pytest.fixture
    def vacancies(self) -> list[Vacancy]:
        return ParserService._parse_feed(RSS)

    def test_junior_excludes_senior_and_lead(self, vacancies: list[Vacancy]) -> None:
        result = ParserService._apply_filters(vacancies, Experience.JUNIOR)
        assert [v.url for v in result] == ["https://djinni.co/jobs/2"]

    def test_middle_keeps_senior_but_drops_lead(self, vacancies: list[Vacancy]) -> None:
        result = ParserService._apply_filters(vacancies, Experience.MIDDLE)
        assert [v.url for v in result] == [
            "https://djinni.co/jobs/1",
            "https://djinni.co/jobs/2",
        ]

    def test_senior_keeps_everything(self, vacancies: list[Vacancy]) -> None:
        assert ParserService._apply_filters(vacancies, Experience.SENIOR) == vacancies

    def test_no_level_keeps_everything(self, vacancies: list[Vacancy]) -> None:
        assert ParserService._apply_filters(vacancies, None) == vacancies


class TestExperienceCoercion:
    def test_unknown_level_is_ignored(self) -> None:
        assert ParserService._coerce_experience("architect") is None

    def test_case_insensitive(self) -> None:
        assert ParserService._coerce_experience("SENIOR") is Experience.SENIOR

    def test_none(self) -> None:
        assert ParserService._coerce_experience(None) is None


@pytest.fixture
def record_requests(monkeypatch):
    """Replace the HTTP call with a recorder; returns the list of call args."""
    calls: list[tuple] = []

    async def fake_request(self, keyword, level, min_salary=None):
        calls.append((keyword, level, min_salary))
        return RSS

    monkeypatch.setattr(ParserService, "_request", fake_request)
    return calls


class TestCaching:
    async def test_second_call_is_served_from_cache(self, record_requests) -> None:
        parser = ParserService()
        await parser.get_jobs(stack="Python")
        await parser.get_jobs(stack="Python")
        assert len(record_requests) == 1

    async def test_a_different_salary_is_a_different_cache_entry(
        self, record_requests
    ) -> None:
        parser = ParserService()
        await parser.get_jobs(stack="Python", min_salary=2000)
        await parser.get_jobs(stack="Python", min_salary=5000)
        assert [c[2] for c in record_requests] == [2000, 5000]

    async def test_a_different_level_is_a_different_cache_entry(
        self, record_requests
    ) -> None:
        parser = ParserService()
        await parser.get_jobs(stack="Python", experience="junior")
        await parser.get_jobs(stack="Python", experience="senior")
        assert [c[1] for c in record_requests] == [Experience.JUNIOR, Experience.SENIOR]


class TestFilterForwarding:
    async def test_salary_reaches_djinni_instead_of_being_filtered_locally(
        self, record_requests
    ) -> None:
        await ParserService().get_jobs(stack="Python", min_salary=3000)
        assert record_requests == [("Python", None, 3000)]

    async def test_every_keyword_is_requested(self, record_requests) -> None:
        await ParserService().get_jobs(stack="Python, Django")
        assert [c[0] for c in record_requests] == ["Python", "Django"]


class TestRequestUrl:
    """Checks the real URL built by `_request`, with only the socket faked out."""

    @staticmethod
    async def captured_query(**kwargs) -> dict[str, list[str]]:
        seen: list[str] = []

        class FakeResponse:
            status = 200

            async def text(self) -> str:
                return RSS

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc) -> None:
                return None

        class FakeSession:
            closed = False

            def get(self, url: str):
                seen.append(url)
                return FakeResponse()

        parser = ParserService(session=FakeSession())
        await parser.get_jobs(**kwargs)
        return parse_qs(urlparse(seen[0]).query)

    async def test_salary_is_sent_to_djinni(self) -> None:
        query = await self.captured_query(stack="Python", min_salary=4000)
        assert query["salary"] == ["4000"]

    async def test_experience_is_mapped_to_exp_level(self) -> None:
        query = await self.captured_query(stack="Python", experience="senior")
        assert query["exp_level"] == ["5y"]

    async def test_keyword_is_sent_as_primary_keyword(self) -> None:
        query = await self.captured_query(stack="Django")
        assert query["primary_keyword"] == ["Django"]

    async def test_optional_params_are_omitted_when_unset(self) -> None:
        query = await self.captured_query(stack="Python")
        assert "salary" not in query
        assert "exp_level" not in query


class TestErrors:
    async def test_raises_when_every_keyword_fails(self, monkeypatch) -> None:
        async def failing(self, keyword, level, min_salary=None):
            raise ParserError("boom")

        monkeypatch.setattr(ParserService, "_request", failing)

        with pytest.raises(ParserError):
            await ParserService().get_jobs(stack="Python, Django")

    async def test_partial_failure_still_returns_results(self, monkeypatch) -> None:
        async def flaky(self, keyword, level, min_salary=None):
            if keyword == "Django":
                raise ParserError("boom")
            return RSS

        monkeypatch.setattr(ParserService, "_request", flaky)

        jobs = await ParserService().get_jobs(stack="Python, Django")
        assert len(jobs) == 3

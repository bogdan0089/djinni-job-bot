import asyncio
import logging
import time
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.exceptions import ParserError
from app.schemas.job import Experience, Vacancy
from app.utils.validators import split_keywords

logger = logging.getLogger(__name__)

_DEFAULT_KEYWORD = "Python"
_MAX_KEYWORDS = 3


def _split_stack(stack: str | None) -> list[str]:
    """Keywords to query Djinni with, falling back to a sane default.

    Rows written before stack validation existed may hold junk, so this is the
    last line of defence: junk would otherwise reach Djinni, which answers an
    unknown keyword with the full unfiltered feed instead of an error.
    """
    return split_keywords(stack, _MAX_KEYWORDS) or [_DEFAULT_KEYWORD]


class ParserService:
    """Fetches vacancies from the Djinni RSS feed.

    Owns a single aiohttp session (reused across requests) and an in-memory
    TTL cache, so a daily digest for N users with the same stack costs one
    HTTP request rather than N.
    """

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None
        self._cache: dict[tuple[str, str | None], tuple[float, list[Vacancy]]] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.HTTP_TIMEOUT),
                headers={"User-Agent": "djinni-job-bot/1.0 (+https://github.com/bogdan0089)"},
            )
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def get_jobs(
        self,
        stack: str | None = None,
        experience: Experience | str | None = None,
        min_salary: int | None = None,
    ) -> list[Vacancy]:
        """Return vacancies matching the user's filters, newest first.

        Stack, experience and salary are all applied by Djinni itself, so the
        feed comes back already filtered instead of being trimmed locally.
        """
        level = self._coerce_experience(experience)
        keywords = _split_stack(stack)

        results = await asyncio.gather(
            *(self._fetch_keyword(kw, level, min_salary) for kw in keywords),
            return_exceptions=True,
        )

        vacancies: list[Vacancy] = []
        seen: set[str] = set()
        failures = 0
        for keyword, result in zip(keywords, results, strict=True):
            if isinstance(result, BaseException):
                failures += 1
                logger.warning("Djinni fetch failed for %r: %s", keyword, result)
                continue
            for vacancy in result:
                if vacancy.url not in seen:
                    seen.add(vacancy.url)
                    vacancies.append(vacancy)

        if failures == len(keywords):
            raise ParserError("Djinni is unreachable")

        return self._apply_filters(vacancies, level)

    @staticmethod
    def _coerce_experience(value: Experience | str | None) -> Experience | None:
        if value is None:
            return None
        try:
            return Experience(str(value).lower())
        except ValueError:
            logger.warning("Unknown experience level %r, ignoring", value)
            return None

    @staticmethod
    def _apply_filters(vacancies: list[Vacancy], level: Experience | None) -> list[Vacancy]:
        """Drop titles whose seniority contradicts the requested level.

        Djinni's `exp_level` matches years of experience, not job titles, so a
        junior query still returns the occasional "Senior"/"Lead" posting.
        """
        if level is None or not level.excluded_title_words:
            return vacancies
        excluded = level.excluded_title_words
        return [v for v in vacancies if not any(w in v.title.lower() for w in excluded)]

    async def _fetch_keyword(
        self, keyword: str, level: Experience | None, min_salary: int | None
    ) -> list[Vacancy]:
        # Salary belongs in the key: it changes the request, so two users with
        # different expectations must not share a cache entry.
        cache_key = (keyword.lower(), level.value if level else None, min_salary)
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]

        xml = await self._request(keyword, level, min_salary)
        vacancies = self._parse_feed(xml)
        self._cache[cache_key] = (now + settings.PARSER_CACHE_TTL, vacancies)
        return vacancies

    async def _request(
        self, keyword: str, level: Experience | None, min_salary: int | None = None
    ) -> str:
        params: dict[str, str | int] = {"primary_keyword": keyword}
        if level is not None:
            params["exp_level"] = level.djinni_exp_level
        if min_salary:
            params["salary"] = min_salary
        url = f"{settings.DJINNI_RSS_URL}?{urlencode(params)}"

        session = await self._get_session()
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ParserError(f"Djinni returned HTTP {response.status}")
                return await response.text()
        except aiohttp.ClientError as exc:
            raise ParserError(f"Djinni request failed: {exc}") from exc
        except TimeoutError as exc:
            raise ParserError("Djinni request timed out") from exc

    @staticmethod
    def _parse_feed(xml: str) -> list[Vacancy]:
        soup = BeautifulSoup(xml, "xml")
        vacancies: list[Vacancy] = []
        for item in soup.find_all("item")[: settings.JOBS_PER_REQUEST]:
            link = item.find("link")
            title = item.find("title")
            if link is None or not link.text.strip():
                continue
            vacancies.append(
                Vacancy(
                    title=title.text.strip() if title else "Untitled vacancy",
                    url=link.text.strip(),
                )
            )
        return vacancies
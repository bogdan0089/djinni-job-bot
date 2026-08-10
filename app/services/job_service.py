import logging

from app.db.models import User
from app.db.repository import UserRepository
from app.schemas.job import Vacancy
from app.services.parser_service import ParserService

logger = logging.getLogger(__name__)


class JobService:
    """Vacancy delivery logic shared by `/jobs` and the daily digest.

    Both entry points go through `fetch_new_for` so a vacancy shown on demand
    is never repeated in the next morning's digest.
    """

    def __init__(self, repo: UserRepository, parser: ParserService) -> None:
        self.repo = repo
        self.parser = parser

    async def fetch_new_for(self, user: User, mark_as_sent: bool = True) -> list[Vacancy]:
        vacancies = await self.parser.get_jobs(
            stack=user.stack,
            experience=user.experience,
            min_salary=user.min_salary,
        )
        if not vacancies:
            return []

        by_url = {v.url: v for v in vacancies}
        unsent_urls = await self.repo.filter_unsent_urls(user.id, list(by_url))
        fresh = [by_url[url] for url in unsent_urls]

        if fresh and mark_as_sent:
            await self.repo.mark_sent(user.id, unsent_urls)

        logger.debug(
            "user=%s fetched=%d new=%d", user.telegram_id, len(vacancies), len(fresh)
        )
        return fresh
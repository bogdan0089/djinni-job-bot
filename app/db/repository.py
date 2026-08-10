from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SentJob, User
from app.schemas.user import RegisterUser


class UserRepository:
    """Data access for users and their delivery history.

    Methods never commit — the caller owns the transaction boundary
    (see `DbSessionMiddleware` and `SchedulerService`).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: RegisterUser) -> User:
        user = User(**data.model_dump())
        self.session.add(user)
        await self.session.flush()  # populates user.id without ending the transaction
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.is_active.is_(True)))
        return list(result.scalars().all())

    async def filter_unsent_urls(self, user_id: int, urls: list[str]) -> list[str]:
        """Return only the urls that were never sent to this user.

        One query for the whole batch instead of one per vacancy.
        """
        if not urls:
            return []
        result = await self.session.execute(
            select(SentJob.job_url).where(
                SentJob.user_id == user_id, SentJob.job_url.in_(urls)
            )
        )
        already_sent = set(result.scalars().all())
        return [url for url in urls if url not in already_sent]

    async def mark_sent(self, user_id: int, urls: list[str]) -> None:
        """Record delivered vacancies. Urls already stored are skipped."""
        if not urls:
            return
        fresh = await self.filter_unsent_urls(user_id, list(dict.fromkeys(urls)))
        self.session.add_all(
            [SentJob(user_id=user_id, job_url=url) for url in fresh]
        )
        await self.session.flush()

    async def deactivate(self, user_id: int) -> None:
        user = await self.session.get(User, user_id)
        if user is not None:
            user.is_active = False
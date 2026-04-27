from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, SendJob
from sqlalchemy import select
from schemas.user_schema import RegisterUser


class RepositoryBot:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def create_user(self, data: RegisterUser) -> User:
        user = User(
            **data.model_dump()
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user(self, telegram_id: int) -> User:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
        )
        return result.scalars().first()
    
    async def update_user(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_all_active_users(self) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
        )
        return result.scalars().all()
    
    async def is_job_sent(self, user_id: int, job_url: str) -> bool:
        result = await self.session.execute(
            select(SendJob)
            .where(SendJob.user_id == user_id, SendJob.job_url == job_url)
        )
        return result.scalar_one_or_none()
    
    async def save_sent_job(self, user_id: int, job_url: str) -> bool:
        sent = SendJob(user_id=user_id, job_url=job_url)
        self.session.add(sent)
        await self.session.commit()
    
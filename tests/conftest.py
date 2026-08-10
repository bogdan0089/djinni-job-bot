import os

os.environ.setdefault("BOT_TOKEN", "test:token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base
from app.db.repository import UserRepository
from app.schemas.user import RegisterUser


@pytest.fixture
async def session() -> AsyncSession:
    """A fresh in-memory database per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def repo(session: AsyncSession) -> UserRepository:
    return UserRepository(session)


@pytest.fixture
async def user(repo: UserRepository):
    created = await repo.create(RegisterUser(telegram_id=1001, username="tester"))
    await repo.session.commit()
    return created

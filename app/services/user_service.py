from app.core.exceptions import UserNotFoundError
from app.db.models import User
from app.db.repository import UserRepository
from app.schemas.user import RegisterUser, UpdateFilters


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def register(self, data: RegisterUser) -> User:
        """Idempotent: `/start` on an existing account refreshes it instead of failing."""
        user = await self.repo.get_by_telegram_id(data.telegram_id)
        if user is None:
            return await self.repo.create(data)
        user.username = data.username
        user.is_active = True  # re-subscribe a user who previously stopped the bot
        return user

    async def get(self, telegram_id: int) -> User:
        user = await self.repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(telegram_id)
        return user

    async def update_filters(self, telegram_id: int, filters: UpdateFilters) -> User:
        user = await self.get(telegram_id)
        # mode="json" turns the Experience enum into a plain str for the DB column
        for field, value in filters.model_dump(mode="json", exclude_unset=True).items():
            if value is not None:
                setattr(user, field, value)
        return user

    async def reset_filters(self, telegram_id: int) -> User:
        user = await self.get(telegram_id)
        user.stack = None
        user.min_salary = None
        user.experience = None
        return user

    async def set_active(self, telegram_id: int, active: bool) -> User:
        user = await self.get(telegram_id)
        user.is_active = active
        return user

    async def is_subscribed(self, telegram_id: int) -> bool:
        """Digest state, used to label the menu button. Unknown users count as on."""
        user = await self.repo.get_by_telegram_id(telegram_id)
        return user.is_active if user else True

    async def get_subscribers(self) -> list[User]:
        """Active users for the daily digest. An empty list is a valid state."""
        return await self.repo.get_active()
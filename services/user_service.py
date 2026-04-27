from database.queries import RepositoryBot
from schemas.user_schema import RegisterUser, UpdateFilters
from database.models import User
from core.exceptions import (
UserNotFoundError,
UsersNotFoundError
)


class UserService:
    def __init__(self, repo: RepositoryBot):
        self.repo = repo

    async def register_user(self, data: RegisterUser) -> User:
        user = await self.repo.get_user(data.telegram_id)
        if not user:
            return await self.repo.create_user(data)
        return user

    async def get_user(self, telegram_id: int) -> User:
        user = await self.repo.get_user(telegram_id)
        if not user:
            raise UserNotFoundError(telegram_id)
        return user

    async def update_filters(self, telegram_id: int, filters: UpdateFilters) -> User:
        user = await self.repo.get_user(telegram_id)
        if not user:
            raise UserNotFoundError(telegram_id)
        if filters.stack is not None:
            user.stack = filters.stack
        if filters.min_salary is not None:
            user.min_salary = filters.min_salary
        if filters.experience is not None:
            user.experience = filters.experience
        return await self.repo.update_user(user)
    
    async def get_all_is_active(self) -> list[User]:
        users = await self.repo.get_all_active_users()
        if not users:
            raise UsersNotFoundError()
        return users


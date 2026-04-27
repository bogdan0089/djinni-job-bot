from pydantic import BaseModel


class RegisterUser(BaseModel):
    telegram_id: int
    username: str | None = None


class UpdateFilters(BaseModel):
    stack: str | None = None
    min_salary: int | None = None
    experience: str | None = None

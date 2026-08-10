from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.job import Experience
from app.utils.validators import split_keywords


class RegisterUser(BaseModel):
    telegram_id: int
    username: str | None = Field(default=None, max_length=64)


class UpdateFilters(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    stack: str | None = Field(default=None, max_length=255)
    min_salary: int | None = Field(default=None, ge=0, le=1_000_000)
    experience: Experience | None = None

    @field_validator("stack")
    @classmethod
    def _must_contain_a_keyword(cls, value: str | None) -> str | None:
        """Last line of defence: a stack Djinni cannot search for is not a stack."""
        if value is not None and not split_keywords(value, 1):
            raise ValueError("stack must contain a latin tech keyword")
        return value
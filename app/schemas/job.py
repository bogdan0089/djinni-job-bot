from enum import StrEnum
from html import escape

from pydantic import BaseModel, ConfigDict


class Experience(StrEnum):
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"

    @property
    def djinni_exp_level(self) -> str:
        return _DJINNI_EXP_LEVEL[self]

    @property
    def excluded_title_words(self) -> tuple[str, ...]:
        """Seniority markers that must not appear in a title for this level."""
        return _EXCLUDED_TITLE_WORDS[self]


_DJINNI_EXP_LEVEL: dict[Experience, str] = {
    Experience.JUNIOR: "1y",
    Experience.MIDDLE: "3y",
    Experience.SENIOR: "5y",
}

_EXCLUDED_TITLE_WORDS: dict[Experience, tuple[str, ...]] = {
    Experience.JUNIOR: ("senior", "lead", "staff", "principal", "head of", "architect"),
    Experience.MIDDLE: ("lead", "staff", "principal", "head of", "architect"),
    Experience.SENIOR: (),
}


class Vacancy(BaseModel):
    """A single Djinni posting.

    The RSS feed carries no salary field, so salary is filtered by Djinni via
    the `salary` query parameter and never shown here.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    url: str

    def as_message_line(self) -> str:
        return f'• <a href="{escape(self.url, quote=True)}">{escape(self.title)}</a>'
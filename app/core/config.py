from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str = Field(min_length=1)

    DATABASE_URL: str = "sqlite+aiosqlite:///bot.db"
    DB_ECHO: bool = False

    LOG_LEVEL: str = "INFO"

    # Daily digest
    TIMEZONE: str = "Europe/Kyiv"
    DIGEST_HOUR: int = Field(default=9, ge=0, le=23)
    DIGEST_MINUTE: int = Field(default=0, ge=0, le=59)

    # Parser
    DJINNI_RSS_URL: str = "https://djinni.co/jobs/rss/"
    HTTP_TIMEOUT: float = Field(default=10.0, gt=0)
    JOBS_PER_REQUEST: int = Field(default=10, ge=1, le=50)
    PARSER_CACHE_TTL: int = Field(default=900, ge=0)

    # Anti-flood: minimum seconds between two updates from the same user
    THROTTLE_RATE: float = Field(default=0.7, ge=0)

    @field_validator("TIMEZONE")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        ZoneInfo(value)  # raises if the zone is unknown
        return value

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


settings = Settings()
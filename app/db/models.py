from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram ids exceed 2^31, so BigInteger is required on PostgreSQL
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), default=None)
    stack: Mapped[str | None] = mapped_column(String(255), default=None)
    min_salary: Mapped[int | None] = mapped_column(default=None)
    experience: Mapped[str | None] = mapped_column(String(16), default=None)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SentJob(Base):
    """One row per (user, vacancy) pair — guarantees a vacancy is sent only once."""

    __tablename__ = "sent_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "job_url", name="uq_sent_jobs_user_url"),
        Index("ix_sent_jobs_user_sent_at", "user_id", "sent_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    job_url: Mapped[str] = mapped_column(String(512))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
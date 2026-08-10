from aiogram import Router

from app.handlers import errors, filters, jobs, start


def build_router() -> Router:
    """Order matters: FSM handlers must be registered before the catch-alls."""
    router = Router(name="root")
    router.include_router(errors.router)
    router.include_router(start.router)
    router.include_router(filters.router)
    router.include_router(jobs.router)
    return router


__all__ = ["build_router"]

import logging

from aiogram import Router
from aiogram.types import ErrorEvent, Message

from app.core.exceptions import UserNotFoundError

logger = logging.getLogger(__name__)
router = Router(name="errors")


def _message_of(event: ErrorEvent) -> Message | None:
    return event.update.message or (
        event.update.callback_query.message if event.update.callback_query else None
    )


@router.error()
async def handle_error(event: ErrorEvent) -> bool:
    """Last line of defence: no traceback ever leaves the user without a reply."""
    message = _message_of(event)

    if isinstance(event.exception, UserNotFoundError):
        if message:
            await message.answer("Please send /start first — I don't know you yet.")
        return True

    logger.exception("Unhandled error while processing update", exc_info=event.exception)
    if message:
        await message.answer("Something went wrong on my side. Please try again later.")
    return True

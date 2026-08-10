class BotError(Exception):
    """Base class for all application errors."""


class UserNotFoundError(BotError):
    def __init__(self, telegram_id: int) -> None:
        self.telegram_id = telegram_id
        super().__init__(f"User {telegram_id} is not registered.")


class ParserError(BotError):
    """Raised when the vacancy source is unreachable or returns garbage."""
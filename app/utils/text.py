from collections.abc import Iterable

from app.schemas.job import Vacancy

TELEGRAM_MESSAGE_LIMIT = 4096


def build_vacancy_messages(
    vacancies: Iterable[Vacancy], header: str | None = None
) -> list[str]:
    """Render vacancies as as few messages as Telegram's 4096-char limit allows.

    Sending one digest beats sending ten separate messages: it avoids the
    per-chat rate limit and keeps the chat readable.
    """
    lines = [v.as_message_line() for v in vacancies]
    if not lines:
        return []
    if header:
        lines.insert(0, header)

    messages: list[str] = []
    current: list[str] = []
    length = 0
    for line in lines:
        # +1 accounts for the newline that joins this line to the previous one
        addition = len(line) + (1 if current else 0)
        if current and length + addition > TELEGRAM_MESSAGE_LIMIT:
            messages.append("\n".join(current))
            current, length = [line], len(line)
        else:
            current.append(line)
            length += addition
    messages.append("\n".join(current))
    return messages
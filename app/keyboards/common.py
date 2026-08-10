from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.schemas.job import Experience

# Reply-keyboard labels. Each one mirrors a command, so typing still works.
BTN_JOBS = "🔍 Vacancies"
BTN_FILTERS = "⚙️ Filters"
BTN_ME = "👤 My filters"
BTN_PAUSE = "⏸ Pause digest"
BTN_RESUME = "▶️ Resume digest"

SKIP = "Skip"
CANCEL = "Cancel"

#: Everything the main menu can send, used to stop a button press from being
#: mistaken for a stack while the /filters flow is running.
MENU_BUTTONS = frozenset({BTN_JOBS, BTN_FILTERS, BTN_ME, BTN_PAUSE, BTN_RESUME})


def main_menu(is_active: bool = True) -> ReplyKeyboardMarkup:
    """Main menu. The last button reflects the current digest state."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_JOBS), KeyboardButton(text=BTN_FILTERS))
    builder.row(
        KeyboardButton(text=BTN_ME),
        KeyboardButton(text=BTN_PAUSE if is_active else BTN_RESUME),
    )
    return builder.as_markup(resize_keyboard=True)


def skip_or_cancel() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=SKIP), KeyboardButton(text=CANCEL))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def experience_levels() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(*(KeyboardButton(text=level.value) for level in Experience))
    builder.row(KeyboardButton(text=SKIP), KeyboardButton(text=CANCEL))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

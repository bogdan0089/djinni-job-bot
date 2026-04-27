# djinni-job-bot

Telegram bot that parses [Djinni.co](https://djinni.co) RSS feed and sends daily job vacancies based on user preferences.

## Features

- Daily job delivery every morning via APScheduler
- Filter vacancies by tech stack, experience level and minimum salary
- Deduplication — the same vacancy is never sent twice
- Multi-step filter setup using aiogram FSM
- Clean layered architecture: handlers → services → repository → database

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Register in the bot |
| `/filters` | Set your stack, experience and salary |
| `/jobs` | Get fresh vacancies right now |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot framework | aiogram 3 |
| Database | SQLAlchemy 2.0 + aiosqlite (SQLite) |
| Scheduler | APScheduler |
| Parser | aiohttp + BeautifulSoup4 (RSS/XML) |
| Validation | Pydantic v2 + pydantic-settings |

## Project Structure

```
Bot/
├── core/
│   ├── config.py            # pydantic-settings config
│   └── exceptions.py        # custom exceptions
├── database/
│   ├── models.py            # SQLAlchemy models
│   └── queries.py           # repository pattern
├── handlers/
│   ├── handlers_start.py    # /start command
│   ├── handlers_filters.py  # /filters FSM flow
│   └── handlers_jobs.py     # /jobs command
├── schemas/
│   └── user_schema.py       # Pydantic schemas
├── services/
│   ├── user_service.py      # user business logic
│   ├── parser_service.py    # Djinni RSS parser
│   └── scheduler_service.py # daily job sender
├── main.py
└── requirements.txt
```

## Setup

**1. Clone the repository**
```bash
git clone https://github.com/bogdan0089/djinni-job-bot.git
cd djinni-job-bot
```

**2. Create virtual environment and install dependencies**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

**3. Create `.env` file**
```
BOT_TOKEN=your_telegram_bot_token
```

**4. Run**
```bash
python main.py
```

> Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram.

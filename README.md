# djinni-job-bot

[![CI](https://github.com/bogdan0089/djinni-job-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/bogdan0089/djinni-job-bot/actions/workflows/ci.yml)

Telegram bot that watches the [Djinni.co](https://djinni.co) RSS feed and delivers vacancies
matching your stack, experience level and salary expectations — on demand and as a daily digest.

## Features

- **Daily digest** at a configurable local time (APScheduler, real timezone support)
- **Filters** by tech stack (up to 3 keywords), experience level and minimum salary
- **Never repeats a vacancy** — `/jobs` and the digest share one delivery history
- **Fault isolation** — a blocked user, a Djinni outage or a bad filter affects that user only
- **Auto-unsubscribe** when a user blocks the bot, so requests are not wasted
- **Response cache** — a digest for N users with the same stack costs 1 HTTP request, not N
- **Anti-flood middleware** so `/jobs` cannot be used to hammer Djinni
- **Stateful menu** — the last button reads *Pause digest* or *Resume digest*
  depending on the subscription, so every command has a one-tap equivalent
- 107 tests, ruff, Docker, GitHub Actions

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Register (or re-subscribe) |
| `/jobs` | Fresh vacancies right now |
| `/filters` | Set stack, salary and experience (FSM flow, `Skip` / `Cancel` at every step) |
| `/me` | Show current filters |
| `/reset` | Clear all filters |
| `/stop` | Pause the daily digest |
| `/help` | Command reference |

## Architecture

```
Telegram update
      │
      ▼
ThrottlingMiddleware      per-user rate limit
      │
      ▼
DbSessionMiddleware       opens a session, injects services, commits once
      │
      ▼
handlers/                 Telegram I/O only — no business logic
      │
      ▼
services/                 UserService · JobService · ParserService · SchedulerService
      │
      ▼
db/repository.py          data access, never commits (caller owns the transaction)
      │
      ▼
SQLite / PostgreSQL
```

Two design decisions worth calling out:

- **The repository never commits.** The middleware commits once after a handler
  returns successfully, so a failed handler rolls back the whole update. In the
  digest, this means vacancies are marked as sent *only* if the message was
  actually delivered — a network failure leaves them queued for the next run.
- **`/jobs` and the digest both go through `JobService.fetch_new_for`.** That is
  what makes deduplication real: a vacancy you pulled manually at 8:55 will not
  show up again in the 09:00 digest.

## Project structure

```
app/
├── core/          config (pydantic-settings), exceptions, logging
├── db/            models, engine/session, repository
├── handlers/      start · filters (FSM) · jobs · global error handler
├── keyboards/     reply keyboards
├── middlewares/   DB session + service injection, anti-flood
├── schemas/       pydantic models (Vacancy, Experience, user DTOs)
├── services/      business logic
├── utils/         message building (Telegram 4096-char splitting)
└── main.py        composition root
tests/             107 tests on an in-memory SQLite DB, no network
```

## Setup

```bash
git clone https://github.com/bogdan0089/djinni-job-bot.git
cd djinni-job-bot

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
cp .env.example .env         # then put your token from @BotFather into BOT_TOKEN

python -m app.main
```

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Configuration

Every setting has a working default except `BOT_TOKEN`. See [.env.example](.env.example).

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | **Required.** Token from [@BotFather](https://t.me/BotFather) |
| `DATABASE_URL` | `sqlite+aiosqlite:///bot.db` | Any async SQLAlchemy URL (PostgreSQL works) |
| `TIMEZONE` | `Europe/Kyiv` | Timezone the digest schedule is interpreted in |
| `DIGEST_HOUR` / `DIGEST_MINUTE` | `9` / `0` | Local time of the daily digest |
| `HTTP_TIMEOUT` | `10` | Djinni request timeout, seconds |
| `JOBS_PER_REQUEST` | `10` | Vacancies taken per keyword |
| `PARSER_CACHE_TTL` | `900` | Feed cache lifetime, seconds |
| `THROTTLE_RATE` | `0.7` | Minimum seconds between two updates from one user |
| `LOG_LEVEL` | `INFO` | Logging level |

## Tech stack

| Layer | Technology |
|-------|-----------|
| Bot framework | aiogram 3 (FSM, middlewares, error handler) |
| Database | SQLAlchemy 2.0 async + aiosqlite / asyncpg |
| Scheduler | APScheduler (`AsyncIOScheduler`, timezone-aware) |
| Parser | aiohttp (shared session) + BeautifulSoup4 (RSS) |
| Validation | Pydantic v2 + pydantic-settings |
| Quality | pytest + pytest-asyncio, ruff, GitHub Actions |

## Known limitations

- Stack, experience and salary are applied by Djinni through the `primary_keyword`,
  `exp_level` and `salary` query parameters. **Djinni answers an unknown value with
  the full unfiltered feed and HTTP 200, not an error** — a junk keyword would look
  like a successful search. Hence the `Experience` enum, the keyword validation in
  `/filters`, and the fallback in `_split_stack` for rows written before it existed.
- `exp_level` matches years of experience, not job titles, so a junior query still
  returns the occasional "Senior"/"Lead" posting. Those are dropped by title locally.
- The RSS feed carries no salary field, so salaries are never displayed — only used
  for filtering.
- The parser cache and the anti-flood counters live in process memory. A multi-replica
  deployment would need Redis (and aiogram's `RedisStorage` for FSM state).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first: a code change must not invalidate this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Never run as root. /app/data must exist *in the image* and be owned by the
# runtime user: Docker copies its ownership when it initialises the named
# volume. Without it the volume is created root-owned and SQLite cannot write.
RUN useradd --create-home --uid 1000 bot \
    && mkdir -p /app/data \
    && chown -R bot:bot /app
USER bot

# Default to the mounted volume so the database survives a rebuild
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/bot.db

CMD ["python", "-m", "app.main"]

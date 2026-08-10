FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Never run as root
RUN useradd --create-home --uid 1000 bot && chown -R bot:bot /app
USER bot

CMD ["python", "-m", "app.main"]

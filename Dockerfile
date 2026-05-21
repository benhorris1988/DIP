# Multi-stage build: Flutter web → Python runtime.
# Single image, single port, single command:
#   docker build -t dip . && docker run --rm -p 8000:8000 dip
# Open http://localhost:8000

# ----------------------------------------------------------------------------
# Stage 1: build the Flutter web bundle
# ----------------------------------------------------------------------------
FROM ghcr.io/cirruslabs/flutter:3.27.1 AS web

WORKDIR /src
COPY flutter_app/ ./flutter_app/

RUN cd flutter_app \
    && git config --global --add safe.directory /sdks/flutter \
    && flutter pub get \
    && flutter build web --release --dart-define=API_BASE_URL=/api

# ----------------------------------------------------------------------------
# Stage 2: Python runtime serving API + Flutter web
# ----------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DIP_DATABASE_URL=sqlite+aiosqlite:////data/dip.db \
    DIP_DEFINITIONS_DIR=/app/definitions \
    DIP_WEB_DIR=/app/web

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gnupg unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=web /src/flutter_app/build/web /app/web

# Persist the SQLite DB across container restarts when /data is mounted.
VOLUME ["/data"]
RUN mkdir -p /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

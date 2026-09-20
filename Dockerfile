# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so application edits don't invalidate this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY core/ ./core/
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Run as a non-root user.
RUN useradd --create-home --uid 10001 mathnova \
    && chown -R mathnova:mathnova /app
USER mathnova

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# A symbolic request can be CPU-heavy, so favour a few workers over
# many threads. Override WEB_CONCURRENCY for the host you deploy to.
ENV WEB_CONCURRENCY=2

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]

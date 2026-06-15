# Cloud MSX Worker — container image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install the se_agent package with the worker extra.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[worker]"

# Non-root user
RUN useradd --create-home --uid 1001 appuser
USER appuser

EXPOSE 8000

# Container Apps sets $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn se_agent.worker.app:app --host 0.0.0.0 --port ${PORT:-8000}"]

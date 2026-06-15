"""Structured logging with secret redaction.

All tool invocations and CRM/LLM activity are logged here. Secret-looking values are
redacted before they ever reach a log record (Constitution: secrets never leak).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

_LOGGER_NAME = "se_agent"

# Keys whose values must always be redacted in logged argument dicts.
_SECRET_KEYS = {
    "client_secret",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "authorization",
    "password",
}

# Patterns that look like bearer tokens / long opaque secrets in free text.
_TOKEN_RE = re.compile(r"(?i)\b(bearer\s+)?[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-.]+")

_REDACTED = "***REDACTED***"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()  # stderr by default
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        level = os.environ.get("SEAGENT_LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level, logging.INFO))
        logger.propagate = False
    return logger


def redact(value: Any) -> Any:
    """Return a copy of ``value`` with secret-looking content removed.

    Works recursively on dicts/lists; redacts by key name and by token-shaped strings.
    """
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if str(k).lower() in _SECRET_KEYS:
                out[k] = _REDACTED
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    if isinstance(value, str):
        return _TOKEN_RE.sub(_REDACTED, value)
    return value

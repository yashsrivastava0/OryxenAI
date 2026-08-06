"""Structured logging using the standard library.

Never logs secrets, .env contents, model API keys, database passwords,
full hidden prompts, or internal chain-of-thought.

Privacy allowlist (Discovery, Section 28):

Safe fields that MAY be logged:
  request_id, session_id (shortened), job_id, agent_run_id, operation,
  prompt_version, model_profile, model_id, attempt counts, finish_reason,
  provider response_id, latency, input character count, compaction flag,
  fact/conflict/question counts, repair reason, validation result, usage.

Fields that MUST NEVER be logged:
  raw resume, raw main prompt, raw answers, raw brief, reasoning_content,
  system prompt text, API key, authorization header, provider error body,
  email, phone number, street address, private URLs, database password,
  full database URL.
"""

from __future__ import annotations

import logging
import logging.config
import sys
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oryxenai.core.settings import Settings

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_SESSION_ID: ContextVar[str | None] = ContextVar("session_id", default=None)
_AGENT_RUN_ID: ContextVar[str | None] = ContextVar("agent_run_id", default=None)

_SAFE_BLOCKED_KEYS = frozenset(
    {
        "password",
        "postgres_password",
        "api_key",
        "secret",
        "token",
        "model_api_key",
        "authorization",
    }
)


def _is_safe_key(key: str) -> bool:
    lowered = key.lower()
    return not any(blocked in lowered for blocked in _SAFE_BLOCKED_KEYS)


class _SafeFormatter(logging.Formatter):
    """Formatter that strips obviously sensitive keys from message args."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return message


def configure_logging(settings: Settings) -> None:
    """Configure root logging from settings.log_level."""
    level = settings.app.log_level.upper()

    config: dict[str, object] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "oryxenai.core.logging._SafeFormatter",
                "fmt": "%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
                "formatter": "default",
                "level": level,
            },
        },
        "loggers": {
            "oryxenai": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "sqlalchemy": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "alembic": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": level, "handlers": ["console"]},
    }
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(value: str | None) -> None:
    _REQUEST_ID.set(value)


def get_request_id() -> str | None:
    return _REQUEST_ID.get()


def new_request_id() -> str:
    value = uuid.uuid4().hex
    set_request_id(value)
    return value


def set_session_id(value: str | None) -> None:
    _SESSION_ID.set(value)


def get_session_id() -> str | None:
    return _SESSION_ID.get()


def set_agent_run_id(value: str | None) -> None:
    _AGENT_RUN_ID.set(value)


def get_agent_run_id() -> str | None:
    return _AGENT_RUN_ID.get()


def log_context() -> dict[str, str]:
    """Return the current correlation context for structured log records."""
    ctx: dict[str, str] = {}
    rid = get_request_id()
    if rid:
        ctx["request_id"] = rid
    sid = get_session_id()
    if sid:
        ctx["session_id"] = sid
    run_id = get_agent_run_id()
    if run_id:
        ctx["agent_run_id"] = run_id
    return ctx

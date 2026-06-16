"""Logging configuration.

A single :func:`configure_logging` entry-point installs a :class:`rich.logging.RichHandler`
on the root logger. The format follows §5 of the project spec: time, level, module, message.
An optional file handler can be added with ``--log-file`` (structured key=value style).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from rich.logging import RichHandler

_LOGGER_NAME: Final[str] = "clash_subcribe"

_FILE_FORMAT: Final[str] = "%(asctime)s %(levelname)-8s %(name)s :: %(message)s"

_CONSOLE_FORMAT: Final[str] = "%(message)s"

_THIRD_PARTY_QUIET_LEVEL: Final[int] = logging.WARNING


def configure_logging(
    *,
    level: str | int = "INFO",
    log_file: str | Path | None = None,
) -> None:
    """Configure root + project loggers.

    Args:
        level: ``"DEBUG"`` / ``"INFO"`` / ``"WARNING"`` / etc. or a numeric level.
        log_file: When set, also tee logs to this file in append mode.

    Notes:
        Idempotent — calling twice (e.g. from tests) replaces handlers instead of
        stacking them, which would otherwise duplicate every log line.
    """
    numeric_level = _coerce_level(level)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        show_time=True,
        show_level=True,
    )
    console.setLevel(numeric_level)
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(console)

    if log_file is not None:
        file_handler = logging.FileHandler(Path(log_file), encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        root.addHandler(file_handler)

    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(_THIRD_PARTY_QUIET_LEVEL)


def get_logger(name: str) -> logging.Logger:
    """Return a project-namespaced logger.

    Use this from every module instead of ``logging.getLogger(__name__)`` so the
    logger always sits under the ``clash_subcribe`` hierarchy — handy when we
    later want to mute the project but keep third-party logs.
    """
    if not name.startswith(_LOGGER_NAME):
        name = f"{_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def _coerce_level(level: str | int) -> int:
    """Accept either a numeric level or a case-insensitive name."""
    if isinstance(level, int):
        return level
    numeric = logging.getLevelName(level.upper())
    if not isinstance(numeric, int):
        raise ValueError(f"unknown log level: {level!r}")
    return numeric

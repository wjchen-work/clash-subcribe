"""Fetcher base class + factory.

A fetcher's job is to deliver the raw subscription text for a single
:class:`~clash_subcribe.config.SourceConfig`. The returned text is
unparsed on purpose — parsers are responsible for shape detection.
"""

from __future__ import annotations

import abc
import logging
import time
from dataclasses import dataclass
from typing import Final

import httpx

from ..exceptions import SourceFetchError

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS: Final[int] = 3
DEFAULT_BACKOFF_SECONDS: Final[float] = 0.5


@dataclass(frozen=True)
class FetchResult:
    """Carrier for a fetched payload plus a few bookkeeping fields.

    The byte count and duration get fed straight into the §5.2 log line.
    """

    text: str
    bytes: int
    duration_seconds: float
    status: int | None = None
    url_redacted: str | None = None


class Fetcher(abc.ABC):
    """Abstract base — subclasses implement :meth:`fetch`."""

    @abc.abstractmethod
    def fetch(self) -> FetchResult:
        """Return the raw subscription text."""

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}()"


def redact_url(url: str) -> str:
    """Replace the path/query of ``url`` with ``***`` for safe logging.

    Garbage input (or anything that doesn't yield a usable scheme+host) collapses
    to a bare ``***`` so we never leak a fragment of the original.
    """
    try:
        parsed = httpx.URL(url)
    except Exception:
        return "***"
    host = parsed.host
    scheme = parsed.scheme
    if not host or not scheme:
        return "***"
    return f"{scheme}://{host}/***"


def time_call(callable_):
    """Tiny helper — record wall-clock duration of ``callable_()``.

    Returns ``(result, duration_seconds)``. Used by fetcher subclasses to
    populate :attr:`FetchResult.duration_seconds` without duplicating the
    timer boilerplate.
    """
    started = time.perf_counter()
    result = callable_()
    return result, time.perf_counter() - started


__all__ = [
    "DEFAULT_BACKOFF_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "FetchResult",
    "Fetcher",
    "SourceFetchError",
    "redact_url",
    "time_call",
]

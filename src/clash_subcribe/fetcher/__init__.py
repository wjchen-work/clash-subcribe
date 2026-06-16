"""Re-exports for the ``fetcher`` package."""

import httpx

from ..config import SourceConfig
from .base import DEFAULT_BACKOFF_SECONDS, DEFAULT_MAX_ATTEMPTS, Fetcher, FetchResult, redact_url
from .file_fetcher import FileFetcher
from .http_fetcher import HttpFetcher


def make_fetcher(
    source: SourceConfig,
    *,
    client: httpx.Client | None = None,
) -> Fetcher:
    """Pick the right fetcher for a :class:`SourceConfig`.

    Kept in ``__init__`` (not ``base``) to avoid the circular import that would
    arise from the concrete fetchers needing the abstract base.
    """
    if source.transport == "http":
        return HttpFetcher(source, client=client)
    return FileFetcher(source)


__all__ = [
    "DEFAULT_BACKOFF_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "FetchResult",
    "Fetcher",
    "FileFetcher",
    "HttpFetcher",
    "make_fetcher",
    "redact_url",
]

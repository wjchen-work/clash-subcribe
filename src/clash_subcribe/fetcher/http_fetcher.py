"""HTTP(S) subscription fetcher.

Uses :mod:`httpx` synchronously — one sequential fetch per source is plenty
fast on the order of dozens of KB. Retries are explicit (not via
``tenacity`` — we deferred that dep) and use exponential backoff.
"""

from __future__ import annotations

import logging

import httpx

from ..config import SourceConfig
from .base import (
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    Fetcher,
    FetchResult,
    redact_url,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})

# 与 Clash Verge Rev 对齐的 User-Agent。许多机场会按 UA 区分客户端返回不同格式
# （Clash YAML / Surge / 原始节点链接 / 流量信息），用主流客户端 UA 抓取最稳。
# Clash Verge Rev 的源码（src-tauri/src/utils/network.rs）拼装格式为
# ``clash-verge/v{CARGO_PKG_VERSION}``；此处固化到当前稳定版本，后续升级时同步即可。
CLASH_VERGE_USER_AGENT: str = "clash-verge/v2.5.1"


class HttpFetcher(Fetcher):
    """Fetch a subscription over HTTP(S)."""

    def __init__(
        self,
        source: SourceConfig,
        *,
        client: httpx.Client | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        timeout_seconds: float = 15.0,
    ) -> None:
        if source.url is None:
            raise ValueError("HttpFetcher requires a source with a URL")
        self._source = source
        self._owns_client = client is None
        self._client = client or httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={"User-Agent": CLASH_VERGE_USER_AGENT},
        )
        self._max_attempts = max_attempts
        self._backoff = backoff_seconds

    def fetch(self) -> FetchResult:
        import time

        from ..exceptions import SourceFetchError

        url = self._source.url  # type: ignore[assignment]
        redacted = redact_url(url)
        last_exc: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            start = time.perf_counter()
            try:
                response = self._client.get(url)
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] %s -> 第 %d/%d 次重试: %s",
                    self._source.name,
                    redacted,
                    attempt,
                    self._max_attempts,
                    type(exc).__name__,
                )
                self._sleep_backoff(attempt)
                continue

            duration = time.perf_counter() - start
            status = response.status_code

            if status >= 400:
                if status in _RETRYABLE_STATUS and attempt < self._max_attempts:
                    logger.warning(
                        "[%s] %s -> HTTP %d (第 %d/%d 次重试)",
                        self._source.name,
                        redacted,
                        status,
                        attempt,
                        self._max_attempts,
                    )
                    self._sleep_backoff(attempt)
                    continue
                raise SourceFetchError(f"[{self._source.name}] {redacted} -> HTTP {status}")

            text = response.text
            logger.info(
                "[%s] %s -> %d OK, %.1f KB, %.2fs",
                self._source.name,
                redacted,
                status,
                len(text.encode("utf-8")) / 1024,
                duration,
            )
            return FetchResult(
                text=text,
                bytes=len(text.encode("utf-8")),
                duration_seconds=duration,
                status=status,
                url_redacted=redacted,
            )

        assert last_exc is not None
        raise SourceFetchError(
            f"[{self._source.name}] {redacted} 抓取失败 ({self._max_attempts} 次重试): {last_exc}"
        ) from last_exc

    def _sleep_backoff(self, attempt: int) -> None:
        import time

        time.sleep(self._backoff * (2 ** (attempt - 1)))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

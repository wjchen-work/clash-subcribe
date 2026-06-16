"""Local-file fetcher.

Used for ``source.path: ./local.yaml``. Reads synchronously.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import SourceConfig
from ..exceptions import SourceFetchError
from .base import Fetcher, FetchResult

logger = logging.getLogger(__name__)


class FileFetcher(Fetcher):
    """Read a subscription from a local file path."""

    def __init__(self, source: SourceConfig) -> None:
        if source.path is None:
            raise ValueError("FileFetcher requires a source with a path")
        self._source = source
        self._path = Path(source.path)

    def fetch(self) -> FetchResult:
        import time

        started = time.perf_counter()
        try:
            text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise SourceFetchError(f"[{self._source.name}] 本地订阅不存在: {self._path}") from exc
        except OSError as exc:
            raise SourceFetchError(f"[{self._source.name}] 读取 {self._path} 失败: {exc}") from exc
        duration = time.perf_counter() - started
        size = len(text.encode("utf-8"))
        logger.info(
            "[%s] %s -> 读取本地文件, %.1f KB, %.3fs",
            self._source.name,
            self._path,
            size / 1024,
            duration,
        )
        return FetchResult(text=text, bytes=size, duration_seconds=duration)

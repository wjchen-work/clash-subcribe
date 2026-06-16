"""File emitter — writes the rendered YAML to a local path."""

from __future__ import annotations

import logging
from pathlib import Path

from ..exceptions import EmitError
from .base import Emitter

logger = logging.getLogger(__name__)


class FileEmitter(Emitter):
    """Write text to a local YAML file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def emit(self, text: str) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise EmitError(f"写入 {self._path} 失败: {exc}") from exc
        logger.info(
            "写入 %s (%.1f KB, %d 字节)",
            self._path,
            len(text.encode("utf-8")) / 1024,
            len(text.encode("utf-8")),
        )

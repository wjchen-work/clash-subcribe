"""Re-exports + factory for the ``emitter`` package."""

from pathlib import Path
from typing import IO

from ..config import OutputConfig
from ..exceptions import EmitError
from .base import Emitter
from .file_emitter import FileEmitter
from .stdout_emitter import StdoutEmitter


def make_emitter(
    output: OutputConfig,
    *,
    stream: IO[str] | None = None,
    path: str | Path | None = None,
) -> Emitter:
    """Pick the right emitter for an :class:`OutputConfig`.

    Args:
        output: validated user output spec.
        stream: override the stdout stream (used in tests to capture output).
        path: override the file output path (used in tests to redirect to tmp).
    """
    kind = output.type
    if kind == "file":
        target = Path(path) if path is not None else Path(output.path)
        return FileEmitter(target)
    if kind == "stdout":
        return StdoutEmitter(stream=stream)
    raise EmitError(f"不支持的 output.type: {kind!r}")


__all__ = ["Emitter", "FileEmitter", "StdoutEmitter", "make_emitter"]

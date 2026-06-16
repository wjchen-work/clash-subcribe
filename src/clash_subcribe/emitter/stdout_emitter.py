"""Stdout emitter — print the rendered YAML to a stream (default: ``sys.stdout``).

Uses :func:`click.echo` for proper terminal handling and ``nl=False`` because
the YAML dump already ends in a newline. The stream is overridable in tests.
"""

from __future__ import annotations

import logging
from typing import IO

import click

from .base import Emitter

logger = logging.getLogger(__name__)


class StdoutEmitter(Emitter):
    """Write the rendered YAML to a text stream (default: ``sys.stdout``)."""

    def __init__(self, stream: IO[str] | None = None) -> None:
        self._stream = stream

    def emit(self, text: str) -> None:
        click.echo(text, nl=False, file=self._stream)
        # click.echo adds a newline when nl=True (default); with nl=False the
        # last newline is preserved if the text already has one.
        size = len(text.encode("utf-8"))
        logger.info("输出到 stdout (%.1f KB)", size / 1024)

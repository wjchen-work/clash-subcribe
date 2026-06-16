"""Unit tests for the file + stdout emitters."""

from __future__ import annotations

import io
from pathlib import Path

from clash_subcribe.emitter import FileEmitter, StdoutEmitter, make_emitter


def test_file_emitter_writes_utf8(tmp_path: Path) -> None:
    target = tmp_path / "out.yaml"
    FileEmitter(target).emit("name: 中文\n")
    assert target.read_text(encoding="utf-8") == "name: 中文\n"


def test_file_emitter_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "out.yaml"
    FileEmitter(target).emit("x: 1\n")
    assert target.is_file()


def test_stdout_emitter_writes_to_stream() -> None:
    buf = io.StringIO()
    StdoutEmitter(stream=buf).emit("hello\n")
    assert buf.getvalue() == "hello\n"


def test_make_emitter_dispatches(tmp_path: Path) -> None:
    from clash_subcribe.config import (
        FileOutputConfig,
        HttpOutputConfig,
        StdoutOutputConfig,
    )

    e = make_emitter(FileOutputConfig(type="file", path=str(tmp_path / "a.yaml")))
    assert isinstance(e, FileEmitter)

    e = make_emitter(StdoutOutputConfig(type="stdout"))
    assert isinstance(e, StdoutEmitter)

    from clash_subcribe.exceptions import EmitError

    with __import__("pytest").raises(EmitError):
        make_emitter(HttpOutputConfig(type="http", port=8080))

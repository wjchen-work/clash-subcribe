"""End-to-end pipeline test — file source → file output, full chain."""

from __future__ import annotations

from pathlib import Path

import yaml

from clash_subcribe.config import (
    FileOutputConfig,
    ProcessorEntry,
    SourceConfig,
    UserConfig,
)
from clash_subcribe.pipeline import run


def _write_sub(tmp_path: Path, name: str = "sub.yaml") -> Path:
    sub = tmp_path / name
    sub.write_text(
        """
        proxies:
          - name: HK-01
            type: ss
            server: 1.1.1.1
            port: 8388
            cipher: aes-256-gcm
            password: sspass
          - name: HK-01
            type: ss
            server: 1.1.1.1
            port: 8388
            cipher: aes-256-gcm
            password: sspass
          - name: US-NY-01
            type: vmess
            server: 2.2.2.2
            port: 443
            uuid: 00000000-0000-0000-0000-000000000001
        """,
        encoding="utf-8",
    )
    return sub


def test_end_to_end_dedup_rename(tmp_path: Path) -> None:
    sub = _write_sub(tmp_path)
    out = tmp_path / "out.yaml"
    cfg = UserConfig(
        sources=[SourceConfig(name="local", path=str(sub))],
        processors=[
            ProcessorEntry.model_validate("dedup"),
            ProcessorEntry.model_validate({"rename": {"prefix": "[A]", "add_index": True}}),
        ],
        output=FileOutputConfig(type="file", path=str(out)),
    )
    result = run(cfg)
    assert result.proxy_count == 2
    assert result.failed_sources == []

    loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    names = [p["name"] for p in loaded["proxies"]]
    assert names == ["[A] 001 HK-01", "[A] 002 US-NY-01"]


def test_end_to_end_failed_source_does_not_abort(tmp_path: Path) -> None:
    sub = _write_sub(tmp_path)
    out = tmp_path / "out.yaml"
    cfg = UserConfig(
        sources=[
            SourceConfig(name="ghost", path=str(tmp_path / "missing.yaml")),
            SourceConfig(name="local", path=str(sub)),
        ],
        processors=[ProcessorEntry.model_validate("dedup")],
        output=FileOutputConfig(type="file", path=str(out)),
    )
    result = run(cfg)
    assert result.proxy_count == 2
    assert result.failed_sources == ["ghost"]

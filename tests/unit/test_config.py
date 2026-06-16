"""Unit tests for ``config.load_config``."""

from __future__ import annotations

from pathlib import Path

import pytest

from clash_subcribe.config import load_config
from clash_subcribe.exceptions import ConfigError


def test_load_minimal_config(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        """
        sources:
          - name: local
            path: ./sub.yaml
        output:
          type: stdout
        """,
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert len(cfg.sources) == 1
    assert cfg.sources[0].name == "local"
    assert cfg.sources[0].transport == "file"
    assert cfg.output.type == "stdout"
    assert cfg.processors == []


def test_processor_bare_name_is_coerced(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        """
        sources:
          - name: a
            path: ./a.yaml
        processors:
          - dedup
          - filter:
              regions: [HK]
        output:
          type: stdout
        """,
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert [p.name for p in cfg.processors] == ["dedup", "filter"]
    assert cfg.processors[1].options == {"regions": ["HK"]}


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("not: [valid: yaml", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(cfg_file)


def test_validation_error_is_wrapped(tmp_path: Path) -> None:
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("sources: []\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(cfg_file)


def test_source_must_have_url_or_path(tmp_path: Path) -> None:
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text(
        """
        sources: [{name: a}]
        output: {type: stdout}
        """,
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(cfg_file)

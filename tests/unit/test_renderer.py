"""Unit tests for the Clash renderer."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from clash_subcribe.exceptions import RenderError
from clash_subcribe.renderer import ClashRenderer


def test_render_without_template_emits_just_proxies(sample_proxies) -> None:
    text = ClashRenderer().render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert len(loaded["proxies"]) == len(sample_proxies)
    # No template → no proxy-groups/rule-providers/rules in output.
    assert "proxy-groups" not in loaded
    assert "rules" not in loaded


def test_render_with_template_preserves_sections(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        mixed-port: 7890
        mode: rule
        proxy-groups:
          - name: G
            type: select
            proxies: [DIRECT]
        rule-providers:
          r1:
            type: http
            behavior: domain
            url: https://example.com/r.yaml
            path: ./r.yaml
        rules:
          - MATCH,G
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert loaded["mixed-port"] == 7890
    assert loaded["mode"] == "rule"
    assert loaded["proxy-groups"] == [{"name": "G", "type": "select", "proxies": ["DIRECT"]}]
    assert "r1" in loaded["rule-providers"]
    assert loaded["rules"] == ["MATCH,G"]
    assert len(loaded["proxies"]) == len(sample_proxies)


def test_render_missing_template_raises(tmp_path: Path) -> None:
    with pytest.raises(RenderError):
        ClashRenderer(tmp_path / "nope.yaml").render([])


def test_render_key_order_matches_template(tmp_path: Path) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        "mixed-port: 7890\nmode: rule\nlog-level: info\n",
        encoding="utf-8",
    )
    text = ClashRenderer(template).render([])
    # Top-level keys from the template come first, in their original order.
    head = text.split("\n", 1)[0]
    assert head.startswith("mixed-port")

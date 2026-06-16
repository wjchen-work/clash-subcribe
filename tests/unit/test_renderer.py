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


def test_render_expands_all_token_in_select_group(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: Proxy
            type: select
            proxies:
              - AUTO
              - DIRECT
              - __ALL__
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    proxies_in_group = loaded["proxy-groups"][0]["proxies"]
    # Static references stay in front, in their original order.
    assert proxies_in_group[:2] == ["AUTO", "DIRECT"]
    # __ALL__ is expanded in place to every proxy name, in pipeline order.
    expected_names = [p.name for p in sample_proxies]
    assert proxies_in_group[2:] == expected_names


def test_render_expands_all_token_in_urltest_group(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: AUTO
            type: url-test
            url: 'http://www.gstatic.com/generate_204'
            interval: 300
            tolerance: 50
            proxies:
              - __ALL__
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert loaded["proxy-groups"][0]["proxies"] == [p.name for p in sample_proxies]


def test_render_expands_all_token_when_proxies_is_empty(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: AUTO
            type: url-test
            proxies:
              - __ALL__
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    # Empty list + __ALL__ → proxies is purely the expanded names.
    assert loaded["proxy-groups"][0]["proxies"] == [p.name for p in sample_proxies]


def test_render_does_not_expand_repeated_all_token(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: AUTO
            type: url-test
            proxies:
              - __ALL__
              - __ALL__
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    proxies_in_group = loaded["proxy-groups"][0]["proxies"]
    expected_names = [p.name for p in sample_proxies]
    # First __ALL__ expands; the second one is preserved verbatim — no duplicate
    # node names inside the group, which mihomo rejects.
    assert proxies_in_group == [*expected_names, "__ALL__"]


def test_render_leaves_groups_without_all_token_untouched(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: Proxy
            type: select
            proxies:
              - AUTO
              - DIRECT
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert loaded["proxy-groups"][0]["proxies"] == ["AUTO", "DIRECT"]


def test_render_leaves_groups_without_proxies_field_untouched(
    tmp_path: Path, sample_proxies
) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: AUTO
            type: url-test
            url: 'http://www.gstatic.com/generate_204'
            interval: 300
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    # No `proxies` key → group is forwarded as-is, no expansion attempted.
    assert "proxies" not in loaded["proxy-groups"][0]


def test_render_without_template_skips_all_expansion(sample_proxies) -> None:
    text = ClashRenderer().render(sample_proxies)
    loaded = yaml.safe_load(text)
    # No template at all → __ALL__ expansion is a no-op.
    assert "proxy-groups" not in loaded
    assert len(loaded["proxies"]) == len(sample_proxies)

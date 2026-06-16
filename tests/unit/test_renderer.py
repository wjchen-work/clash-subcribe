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
    assert proxies_in_group[:2] == ["AUTO", "DIRECT"]
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
    assert "proxies" not in loaded["proxy-groups"][0]


def test_render_without_template_skips_all_expansion(sample_proxies) -> None:
    text = ClashRenderer().render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert "proxy-groups" not in loaded
    assert len(loaded["proxies"]) == len(sample_proxies)


def test_render_expands_filter_token_with_chinese_keyword(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: 美国节点
            type: select
            proxies:
              - __PROXY__:美国
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert loaded["proxy-groups"][0]["proxies"] == []


def test_render_filter_token_with_chinese_keyword_matches_unicode_names(
    tmp_path: Path,
) -> None:
    """Smoke-test: a proxy whose name literally contains 美国 must match.

    Built ad-hoc because the shared :data:`SAMPLE_PROXIES` roster only
    carries Latin tags — adding a 6th proxy there would change the
    behavior every other renderer test relies on.
    """
    from clash_subcribe.models import Proxy

    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: 美国节点
            type: select
            proxies:
              - __PROXY__:美国
        """,
        encoding="utf-8",
    )
    proxies = [
        Proxy(name="🇺🇸【北美洲】美国01丨专线", type="trojan", server="x", port=1, password="p"),
        Proxy(name="🇭🇰【亚洲】香港01", type="trojan", server="y", port=2, password="q"),
    ]
    text = ClashRenderer(template).render(proxies)
    loaded = yaml.safe_load(text)
    assert loaded["proxy-groups"][0]["proxies"] == ["🇺🇸【北美洲】美国01丨专线"]


def test_render_filter_token_is_case_insensitive_and_or_semantics(
    tmp_path: Path, sample_proxies
) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: 美国节点
            type: select
            proxies:
              - __PROXY__:us,JP
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    proxies_in_group = loaded["proxy-groups"][0]["proxies"]
    assert proxies_in_group == ["JP-01", "US-NY-01", "JP-02 免费"]


def test_render_filter_token_preserves_surrounding_group_entries(
    tmp_path: Path, sample_proxies
) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: 美国节点
            type: select
            proxies:
              - AUTO
              - __PROXY__:US
              - DIRECT
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    proxies_in_group = loaded["proxy-groups"][0]["proxies"]
    assert proxies_in_group == ["AUTO", "US-NY-01", "DIRECT"]


def test_render_filter_token_no_match_keeps_group_with_empty_proxies(
    tmp_path: Path, sample_proxies
) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: 德国节点
            type: select
            proxies:
              - __PROXY__:德国
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert loaded["proxy-groups"] == [{"name": "德国节点", "type": "select", "proxies": []}]


def test_render_filter_token_can_coexist_with_all_token(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: 节点选择
            type: select
            proxies:
              - __ALL__
              - 美国节点
              - DIRECT
          - name: 美国节点
            type: select
            proxies:
              - __PROXY__:US
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    expected_names = [p.name for p in sample_proxies]
    assert loaded["proxy-groups"][0]["proxies"] == [*expected_names, "美国节点", "DIRECT"]
    assert loaded["proxy-groups"][1]["proxies"] == ["US-NY-01"]


def test_render_filter_token_repeated_keeps_all_matches(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: US
            type: select
            proxies:
              - __PROXY__:JP
              - __PROXY__:US
        """,
        encoding="utf-8",
    )
    text = ClashRenderer(template).render(sample_proxies)
    loaded = yaml.safe_load(text)
    assert loaded["proxy-groups"][0]["proxies"] == ["JP-01", "JP-02 免费", "US-NY-01"]


def test_render_filter_token_without_keywords_raises(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: Bad
            type: select
            proxies:
              - "__PROXY__:"
        """,
        encoding="utf-8",
    )
    with pytest.raises(RenderError):
        ClashRenderer(template).render(sample_proxies)


def test_render_filter_token_with_only_commas_raises(tmp_path: Path, sample_proxies) -> None:
    template = tmp_path / "t.yaml"
    template.write_text(
        """
        proxy-groups:
          - name: Bad
            type: select
            proxies:
              - "__PROXY__:,  ,"
        """,
        encoding="utf-8",
    )
    with pytest.raises(RenderError):
        ClashRenderer(template).render(sample_proxies)

"""Unit tests for the Clash parser + parser auto-detection."""

from __future__ import annotations

import pytest

from clash_subcribe.exceptions import ParseError
from clash_subcribe.parser import ClashParser, make_parser


def test_parses_valid_proxies(sample_yaml: str) -> None:
    proxies = ClashParser().parse(sample_yaml)
    names = [p.name for p in proxies]
    assert names == ["HK-01", "US-NY-01"]


def test_skips_invalid_entries(sample_yaml: str) -> None:
    proxies = ClashParser().parse(sample_yaml)
    assert len(proxies) == 2


def test_empty_yaml_returns_empty() -> None:
    assert ClashParser().parse("") == []
    assert ClashParser().parse("proxies: []") == []


def test_non_mapping_root_raises() -> None:
    with pytest.raises(ParseError):
        ClashParser().parse("- just a list\n")


def test_make_parser_picks_clash_for_yaml() -> None:
    p = make_parser("proxies:\n  - {name: a, type: ss, server: x, port: 1}\n")
    assert isinstance(p, ClashParser)


def test_make_parser_rejects_unknown() -> None:
    with pytest.raises(ParseError):
        make_parser("not a subscription at all\n")

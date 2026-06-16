"""Unit tests for the 4 core processors."""

from __future__ import annotations

import pytest

from clash_subcribe.config import ProcessorEntry
from clash_subcribe.exceptions import ConfigError
from clash_subcribe.processors import REGISTRY, build
from clash_subcribe.processors.dedup import DedupProcessor


def test_registry_has_four_processors() -> None:
    assert set(REGISTRY) == {"dedup", "filter", "rename", "sort"}


def test_dedup_collapses_duplicates(sample_proxies) -> None:
    out = DedupProcessor()(sample_proxies)
    assert len(out) == len(sample_proxies) - 1
    assert {p.name for p in out} == {"HK-01", "JP-01", "US-NY-01", "JP-02 免费"}


def test_filter_by_regions(sample_proxies) -> None:
    entry = ProcessorEntry.model_validate({"filter": {"regions": ["HK", "JP"]}})
    out = build(entry)(sample_proxies)
    assert {p.name for p in out} == {"HK-01", "HK-01 [reseller]", "JP-01", "JP-02 免费"}


def test_filter_by_keywords(sample_proxies) -> None:
    entry = ProcessorEntry.model_validate({"filter": {"keywords": ["免费"]}})
    out = build(entry)(sample_proxies)
    assert [p.name for p in out] == ["JP-02 免费"]


def test_filter_by_protocols(sample_proxies) -> None:
    entry = ProcessorEntry.model_validate({"filter": {"protocols": ["ss"]}})
    out = build(entry)(sample_proxies)
    assert {p.type for p in out} == {"ss"}


def test_rename_with_prefix_and_region(sample_proxies) -> None:
    entry = ProcessorEntry.model_validate(
        {"rename": {"prefix": "[A]", "add_region_tag": True, "add_index": True}}
    )
    out = build(entry)(sample_proxies)
    assert out[0].name.startswith("[A] [HK] 001")
    out2 = build(entry)(out)
    assert out2[0].name.startswith("[A] [HK] 001")


def test_sort_by_type_groups_protocols(sample_proxies) -> None:
    entry = ProcessorEntry.model_validate({"sort": {"by": "type"}})
    out = build(entry)(sample_proxies)
    types = [p.type for p in out]
    assert types == sorted(types)


def test_unknown_processor_raises() -> None:
    entry = ProcessorEntry.model_validate("nope")
    with pytest.raises(ConfigError):
        build(entry)


def test_processor_rejects_unknown_options() -> None:
    entry = ProcessorEntry.model_validate({"dedup": {"bogus": 1}})
    with pytest.raises(ConfigError):
        build(entry)

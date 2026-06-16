"""Filter proxies by keyword / region / protocol.

Keywords use case-insensitive substring against ``proxy.name``; protocols use
exact (case-insensitive) match against ``proxy.type``. Region tokens are
recognized by a small convention (HK / JP / US / TW / SG / UK / DE) so a
region list works for the most common case.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Proxy
from .base import Processor, register

_REGION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("HK", re.compile(r"(?:\b|_|\-| )HK(?:\b|_|\-| )", re.IGNORECASE)),
    ("JP", re.compile(r"(?:\b|_|\-| )JP(?:\b|_|\-| )", re.IGNORECASE)),
    ("US", re.compile(r"(?:\b|_|\-| )US(?:\b|_|\-| )", re.IGNORECASE)),
    ("TW", re.compile(r"(?:\b|_|\-| )TW(?:\b|_|\-| )", re.IGNORECASE)),
    ("SG", re.compile(r"(?:\b|_|\-| )SG(?:\b|_|\-| )", re.IGNORECASE)),
    ("UK", re.compile(r"(?:\b|_|\-| )UK(?:\b|_|\-| )", re.IGNORECASE)),
    ("DE", re.compile(r"(?:\b|_|\-| )DE(?:\b|_|\-| )", re.IGNORECASE)),
)


def _detect_region(name: str) -> str | None:
    for tag, pattern in _REGION_PATTERNS:
        if pattern.search(name):
            return tag
    return None


class FilterProcessor(Processor):
    name = "filter"

    def __init__(
        self,
        *,
        keywords: list[str] | None = None,
        exclude_keywords: list[str] | None = None,
        regions: list[str] | None = None,
        exclude_regions: list[str] | None = None,
        protocols: list[str] | None = None,
        exclude_protocols: list[str] | None = None,
    ) -> None:
        self._keywords = [k.lower() for k in (keywords or [])]
        self._exclude_keywords = [k.lower() for k in (exclude_keywords or [])]
        self._regions = [r.upper() for r in (regions or [])]
        self._exclude_regions = [r.upper() for r in (exclude_regions or [])]
        self._protocols = [p.lower() for p in (protocols or [])]
        self._exclude_protocols = [p.lower() for p in (exclude_protocols or [])]

    def apply(self, proxies: list[Proxy]) -> list[Proxy]:
        result: list[Proxy] = []
        for proxy in proxies:
            name_lc = proxy.name.lower()
            if self._keywords and not any(k in name_lc for k in self._keywords):
                continue
            if self._exclude_keywords and any(k in name_lc for k in self._exclude_keywords):
                continue
            if self._protocols and proxy.type.lower() not in self._protocols:
                continue
            if self._exclude_protocols and proxy.type.lower() in self._exclude_protocols:
                continue
            if self._regions or self._exclude_regions:
                region = (_detect_region(proxy.name) or "").upper()
                if self._regions and region not in self._regions:
                    continue
                if self._exclude_regions and region in self._exclude_regions:
                    continue
            result.append(proxy)
        return result


def _build(options: dict[str, Any]) -> Processor:
    if not options:
        raise ValueError("filter 至少需要一个选项 (keywords / regions / protocols / ...)")
    return FilterProcessor(
        keywords=options.get("keywords"),
        exclude_keywords=options.get("exclude_keywords"),
        regions=options.get("regions"),
        exclude_regions=options.get("exclude_regions"),
        protocols=options.get("protocols"),
        exclude_protocols=options.get("exclude_protocols"),
    )


register("filter", _build)

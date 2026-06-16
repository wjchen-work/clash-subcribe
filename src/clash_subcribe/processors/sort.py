"""Sort proxies by name / type / custom weight.

Supported ``by`` values: ``name`` (default), ``type``, ``weight``.
"""

from __future__ import annotations

from typing import Any

from ..models import Proxy
from .base import Processor, register

_DEFAULT_WEIGHTS: dict[str, int] = {
    "ss": 10,
    "ssr": 20,
    "trojan": 30,
    "vmess": 40,
    "vless": 50,
    "hysteria2": 60,
    "hysteria": 70,
    "http": 80,
    "socks5": 90,
}


class SortProcessor(Processor):
    name = "sort"

    def __init__(self, *, by: str = "name", weights: dict[str, int] | None = None) -> None:
        if by not in {"name", "type", "weight"}:
            raise ValueError(f"sort.by 必须是 name/type/weight，实际: {by!r}")
        self._by = by
        self._weights = {**_DEFAULT_WEIGHTS, **(weights or {})}

    def apply(self, proxies: list[Proxy]) -> list[Proxy]:
        if self._by == "name":
            return sorted(proxies, key=lambda p: p.name.lower())
        if self._by == "type":
            return sorted(proxies, key=lambda p: (p.type, p.name.lower()))
        return sorted(
            proxies,
            key=lambda p: (self._weights.get(p.type, 999), p.name.lower()),
        )


def _build(options: dict[str, Any]) -> Processor:
    weights = options.get("weights")
    if weights is not None and not isinstance(weights, dict):
        raise ValueError("sort.weights 必须是 {type: int} 映射")
    return SortProcessor(by=options.get("by", "name"), weights=weights)


register("sort", _build)

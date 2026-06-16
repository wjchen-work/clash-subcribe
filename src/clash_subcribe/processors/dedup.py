"""Deduplicate proxies by their :meth:`Proxy.fingerprint`.

Two nodes that point at the same backend (different provider, same server
and credentials) collapse to one. We keep the *first* occurrence so users
get stable ordering relative to their ``sources`` list.
"""

from __future__ import annotations

from typing import Any

from ..models import Proxy
from .base import Processor, register


class DedupProcessor(Processor):
    name = "dedup"

    def apply(self, proxies: list[Proxy]) -> list[Proxy]:
        seen: set[str] = set()
        result: list[Proxy] = []
        for proxy in proxies:
            fp = proxy.fingerprint()
            if fp in seen:
                continue
            seen.add(fp)
            result.append(proxy)
        return result


def _build(options: dict[str, Any]) -> Processor:
    # ``dedup`` takes no options today; reject any to keep config errors loud.
    if options:
        raise ValueError(f"dedup 不支持选项: {sorted(options)}")
    return DedupProcessor()


register("dedup", _build)

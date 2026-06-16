"""Rename proxies with a uniform prefix / region tag / running index.

The index is zero-padded to 3 digits so the YAML diff stays readable.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Proxy
from .base import Processor, register
from .filter import _detect_region


def _strip_existing_prefix(name: str) -> str:
    """Drop a leading ``[xx]`` tag (if any) so re-running the processor doesn't stack them."""
    return re.sub(r"^\s*\[[^\]]+\]\s*", "", name)


class RenameProcessor(Processor):
    name = "rename"

    def __init__(
        self,
        *,
        prefix: str = "",
        add_region_tag: bool = False,
        add_index: bool = True,
    ) -> None:
        self._prefix = prefix
        self._add_region_tag = add_region_tag
        self._add_index = add_index

    def apply(self, proxies: list[Proxy]) -> list[Proxy]:
        result: list[Proxy] = []
        for index, proxy in enumerate(proxies, start=1):
            base = _strip_existing_prefix(proxy.name)
            parts: list[str] = []
            if self._prefix:
                parts.append(self._prefix)
            if self._add_region_tag:
                region = _detect_region(proxy.name)
                if region:
                    parts.append(f"[{region}]")
            if self._add_index:
                parts.append(f"{index:03d}")
            parts.append(base)
            new_name = " ".join(parts)
            result.append(proxy.model_copy(update={"name": new_name}))
        return result


def _build(options: dict[str, Any]) -> Processor:
    if "prefix" in options and not isinstance(options["prefix"], str):
        raise ValueError("`prefix` 必须是字符串")
    return RenameProcessor(
        prefix=options.get("prefix", ""),
        add_region_tag=bool(options.get("add_region_tag", False)),
        add_index=bool(options.get("add_index", True)),
    )


register("rename", _build)

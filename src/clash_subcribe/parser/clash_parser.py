"""Clash YAML parser.

Most subscriptions are a Clash YAML config with a ``proxies:`` list — that's
all we look at. ``proxy-groups``, ``rules``, etc. are ignored at this stage;
the renderer takes care of those from the template.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml
from pydantic import ValidationError

from ..exceptions import ParseError
from ..models import Proxy
from .base import Parser

logger = logging.getLogger(__name__)


class ClashParser(Parser):
    """Parse the ``proxies:`` section of a Clash YAML config."""

    def parse(self, text: str) -> list[Proxy]:
        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ParseError(f"YAML 解析失败: {exc}") from exc

        if loaded is None:
            return []
        if not isinstance(loaded, dict):
            raise ParseError(f"Clash 订阅根节点必须是 mapping，实际: {type(loaded).__name__}")

        raw_proxies: Any = loaded.get("proxies", [])
        if not isinstance(raw_proxies, list):
            raise ParseError("`proxies` 字段必须是列表")

        proxies: list[Proxy] = []
        skipped = 0
        for index, raw in enumerate(raw_proxies):
            if not isinstance(raw, dict):
                skipped += 1
                continue
            try:
                proxies.append(Proxy.model_validate(raw))
            except ValidationError as exc:
                logger.debug("proxy #%d 校验失败: %s", index, exc)
                skipped += 1
        logger.info(
            "解析完成：%d 节点（跳过 %d 条不可解析条目）",
            len(proxies),
            skipped,
        )
        return proxies

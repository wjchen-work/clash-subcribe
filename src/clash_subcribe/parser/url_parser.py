"""URL parser — stub for the MVP.

Full support for ``ss://`` / ``vmess://`` / ``trojan://`` / ``hysteria2://`` /
``vless://`` is on the roadmap. For now we raise a clear error so users know
exactly what's missing.
"""

from __future__ import annotations

import logging

from ..exceptions import ParseError
from ..models import Proxy
from .base import Parser

logger = logging.getLogger(__name__)


class URLParser(Parser):
    """Parser for bare node URL lists (ss://, vmess://, ...)."""

    def parse(self, text: str) -> list[Proxy]:
        raise ParseError(
            "单节点 URL 解析（ss/vmess/trojan/...）尚未实现，欢迎贡献；当前仅支持 Clash YAML 订阅"
        )

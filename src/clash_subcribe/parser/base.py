"""Parser base class + auto-detection.

A parser turns the raw text returned by a fetcher into a list of
:class:`~clash_subcribe.models.Proxy` models. The format is auto-detected
(YAML vs. bare URL); everything else is rejected.
"""

from __future__ import annotations

import abc
import logging
from typing import Final

import yaml

from ..models import Proxy

logger = logging.getLogger(__name__)

_YAML_MARKERS: Final[tuple[str, ...]] = ("---", "{", "\n")


class Parser(abc.ABC):
    """Abstract base — subclasses implement :meth:`parse`."""

    @abc.abstractmethod
    def parse(self, text: str) -> list[Proxy]:
        """Parse ``text`` and return the extracted proxies."""


_URL_PREFIXES: Final[tuple[str, ...]] = (
    "ss://",
    "ssr://",
    "vmess://",
    "trojan://",
    "vless://",
    "hysteria://",
    "hy2://",
    "hysteria2://",
)


def _looks_like_yaml(text: str) -> bool:
    """Heuristic: Clash YAML always contains a top-level ``proxies:`` or similar key."""
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError:
        return False
    return isinstance(loaded, dict) and "proxies" in loaded

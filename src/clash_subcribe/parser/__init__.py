"""Re-exports for the ``parser`` package."""

from ..exceptions import ParseError
from ..models import Proxy
from .base import Parser
from .clash_parser import ClashParser
from .url_parser import URLParser

# Markers for the formats we support. Adding a new parser is just a matter of
# adding a marker and a branch below.
_YAML_MARKERS: tuple[str, ...] = ("---", "{", "\n")
_URL_PREFIXES: tuple[str, ...] = (
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
    """Heuristic: Clash YAML always contains a top-level ``proxies:`` key."""
    import yaml as _yaml

    try:
        loaded = _yaml.safe_load(text)
    except _yaml.YAMLError:
        return False
    return isinstance(loaded, dict) and "proxies" in loaded


def make_parser(text: str) -> Parser:
    """Pick a parser by inspecting the payload."""
    stripped = text.lstrip()
    if stripped.startswith(_YAML_MARKERS) or _looks_like_yaml(stripped):
        return ClashParser()
    if any(stripped.startswith(prefix) for prefix in _URL_PREFIXES):
        return URLParser()
    raise ParseError(
        f"无法识别订阅格式（开头: {stripped[:32]!r}）；支持的格式：Clash YAML / 单节点 URL"
    )


__all__ = ["ClashParser", "Parser", "Proxy", "URLParser", "make_parser"]

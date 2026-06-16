"""Render a proxy list + template into a Clash YAML document.

Template-driven: lift ``proxy-groups`` / ``rule-providers`` / ``rules`` and
other top-level keys verbatim and only replace ``proxies``. Without a
template, emit a minimal valid Clash config.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import RenderError
from ..models import ClashConfig, Proxy

logger = logging.getLogger(__name__)

_KNOWN_KEYS: frozenset[str] = frozenset({"proxies", "proxy-groups", "rule-providers", "rules"})

ALL_PROXIES_TOKEN: str = "__ALL__"

FILTER_TOKEN_PREFIX: str = "__PROXY__:"


class ClashRenderer:
    """Render ``proxies`` + (optional) template → final YAML text."""

    def __init__(self, template_path: str | Path | None = None) -> None:
        self._template_path = Path(template_path) if template_path else None

    def render(self, proxies: list[Proxy]) -> str:
        config = self._build_config(proxies)
        try:
            return yaml.safe_dump(
                config.to_dict(),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=100,
            )
        except yaml.YAMLError as exc:
            raise RenderError(f"YAML 序列化失败: {exc}") from exc

    def _build_config(self, proxies: list[Proxy]) -> ClashConfig:
        if self._template_path is None:
            return ClashConfig(proxies=proxies)
        if not self._template_path.is_file():
            raise RenderError(f"模板文件不存在: {self._template_path}")
        try:
            raw = yaml.safe_load(self._template_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RenderError(f"模板 {self._template_path} 解析失败: {exc}") from exc
        if raw is None:
            return ClashConfig(proxies=proxies)
        if not isinstance(raw, dict):
            raise RenderError(f"模板根节点必须是 mapping，实际: {type(raw).__name__}")

        proxy_names = [p.name for p in proxies]
        return ClashConfig(
            proxies=proxies,
            proxy_groups=[
                _expand_tokens(g, proxy_names) for g in _coerce_list(raw.get("proxy-groups"))
            ],
            rule_providers=_coerce_dict(raw.get("rule-providers")),
            rules=_coerce_str_list(raw.get("rules")),
            extras={k: v for k, v in raw.items() if k not in _KNOWN_KEYS},
        )


def _coerce_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RenderError(f"`proxy-groups` 必须是 list，实际: {type(value).__name__}")
    return [item for item in value if isinstance(item, dict)]


def _coerce_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RenderError(f"`rule-providers` 必须是 dict，实际: {type(value).__name__}")
    return dict(value)


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RenderError(f"`rules` 必须是 list，实际: {type(value).__name__}")
    return [str(item) for item in value]


def _expand_tokens(group: dict[str, Any], proxy_names: list[str]) -> dict[str, Any]:
    """Expand the proxy-name placeholders in a group's ``proxies`` list.

    - :data:`ALL_PROXIES_TOKEN` (``__ALL__``) expands to the full proxy name
      list; only the first occurrence is expanded so a group never ends up
      with duplicate entries (mihomo rejects duplicates inside a group).
    - :data:`FILTER_TOKEN_PREFIX` (``__PROXY__:kw1,kw2,...``) expands to
      every proxy whose ``name`` contains any of the keywords
      (case-insensitive, OR semantics), preserving original proxy ordering.
      An empty match expands to an empty slot; the group is preserved so
      rule references keep resolving.

    Groups without a ``proxies`` list, or with no placeholder, are returned
    unchanged.
    """
    proxies_field = group.get("proxies")
    if not isinstance(proxies_field, list):
        return group
    expanded: list[Any] = []
    all_consumed = False
    for item in proxies_field:
        if not isinstance(item, str):
            expanded.append(item)
            continue
        if item == ALL_PROXIES_TOKEN:
            if all_consumed:
                expanded.append(item)
            else:
                expanded.extend(proxy_names)
                all_consumed = True
            continue
        if item.startswith(FILTER_TOKEN_PREFIX):
            keywords = _parse_filter_keywords(item)
            expanded.extend(_filter_proxy_names(proxy_names, keywords))
            continue
        expanded.append(item)
    return {**group, "proxies": expanded}


def _parse_filter_keywords(token: str) -> list[str]:
    """Extract the keyword list from a ``__PROXY__:...`` placeholder.

    Raises:
        RenderError: if the placeholder is malformed (no keywords).
    """
    suffix = token[len(FILTER_TOKEN_PREFIX) :]
    keywords = [piece.strip() for piece in suffix.split(",")]
    keywords = [k for k in keywords if k]
    if not keywords:
        raise RenderError(
            f"过滤占位符 {token!r} 缺少关键词；期望格式为 '{FILTER_TOKEN_PREFIX}kw1,kw2'"
        )
    return keywords


def _filter_proxy_names(proxy_names: list[str], keywords: list[str]) -> list[str]:
    """Return ``proxy_names`` filtered by an OR-of-keywords match.

    Substring-based and case-insensitive — covers both Chinese region tags
    (``美国``) and Latin tags (``US``) that real-world providers mix.
    """
    lowered = [k.casefold() for k in keywords]
    return [name for name in proxy_names if any(k in name.casefold() for k in lowered)]

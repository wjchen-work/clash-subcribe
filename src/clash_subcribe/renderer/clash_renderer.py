"""Render a proxy list + template into a Clash YAML document.

The renderer is intentionally template-driven: when the user supplies a
``clash.template.yaml`` we lift ``proxy-groups`` / ``rule-providers`` / ``rules``
and any other top-level keys verbatim and only replace the ``proxies`` list.
When no template is provided, we emit a minimal valid Clash config so the
tool still works out of the box.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import RenderError
from ..models import ClashConfig, Proxy

logger = logging.getLogger(__name__)

# Keys that are explicitly modeled on :class:`ClashConfig` — everything else
# in the template YAML is preserved in :attr:`ClashConfig.extras`.
_KNOWN_KEYS: frozenset[str] = frozenset({"proxies", "proxy-groups", "rule-providers", "rules"})


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

        return ClashConfig(
            proxies=proxies,
            proxy_groups=_coerce_list(raw.get("proxy-groups")),
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

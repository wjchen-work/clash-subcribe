"""Clash config model — the rendered output container.

We model the four sections we touch (proxies, proxy-groups, rule-providers,
rules) and keep the rest of the Clash YAML in :attr:`extras` so a template's
``mixed-port`` / ``mode`` / ``log-level`` etc. are preserved verbatim.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .proxy import Proxy


class ClashConfig(BaseModel):
    """Top-level rendered Clash configuration.

    Attributes:
        proxies: The merged, processed proxy list (always present).
        proxy_groups: Auto/manual groups referencing proxies by name.
        rule_providers: External rule sources (rule-sets loaded from URLs/files).
        rules: Routing rules applied in order.
        extras: Any other top-level keys lifted verbatim from the template
            (mixed-port, mode, log-level, sniffer, tun, dns, ...).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    proxies: list[Proxy] = Field(default_factory=list)
    proxy_groups: list[dict[str, Any]] = Field(default_factory=list, alias="proxy-groups")
    rule_providers: dict[str, Any] = Field(default_factory=dict, alias="rule-providers")
    rules: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Render to a plain dict in the canonical Clash key order."""
        out: dict[str, Any] = {}
        out.update(self.extras)
        out["proxies"] = [p.to_clash_dict() for p in self.proxies]
        if self.proxy_groups:
            out["proxy-groups"] = self.proxy_groups
        if self.rule_providers:
            out["rule-providers"] = self.rule_providers
        if self.rules:
            out["rules"] = self.rules
        return out

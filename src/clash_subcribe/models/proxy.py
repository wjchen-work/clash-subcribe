"""Proxy node data model.

A Clash proxy node is polymorphic (different types carry different fields);
we keep one :class:`Proxy` with the union of common fields and enforce
per-type invariants via :meth:`Proxy._validate_type_required_fields`.
:meth:`Proxy.fingerprint` collapses nodes from different providers that
ultimately point at the same backend.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProxyType = Literal[
    "ss",
    "ssr",
    "vmess",
    "trojan",
    "http",
    "socks5",
    "hysteria",
    "hysteria2",
    "hy2",
    "vless",
]

_TYPE_ALIASES: dict[str, str] = {
    "hy2": "hysteria2",
}


class Proxy(BaseModel):
    """A single Clash proxy node.

    Required: ``name``, ``type``, ``server``, ``port``. Use
    :meth:`to_clash_dict` to dump a Clash-compatible dict preserving only
    the fields that were set — keeping diffs stable.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    type: str
    server: str
    port: int = Field(ge=1, le=65535)
    cipher: str | None = None
    password: str | None = None
    uuid: str | None = None
    alter_id: int | None = Field(default=None, alias="alterId")
    udp: bool | None = None
    tls: bool | None = None
    sni: str | None = None
    alpn: list[str] | None = None
    skip_cert_verify: bool | None = Field(default=None, alias="skip-cert-verify")
    network: str | None = None
    ws_path: str | None = Field(default=None, alias="ws-path")
    ws_headers: dict[str, str] | None = Field(default=None, alias="ws-headers")
    protocol: str | None = None
    protocol_param: str | None = Field(default=None, alias="protocol-param")
    obfs: str | None = None
    obfs_param: str | None = Field(default=None, alias="obfs-param")
    username: str | None = None
    auth_str: str | None = Field(default=None, alias="auth_str")
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _normalize_type(cls, value: str) -> str:
        canonical = _TYPE_ALIASES.get(value, value)
        if not canonical:
            raise ValueError("proxy type cannot be empty")
        return canonical

    @model_validator(mode="after")
    def _validate_type_required_fields(self) -> Proxy:
        """Enforce the per-type required-field contract."""
        t = self.type
        if t == "ss":
            if not self.cipher or not self.password:
                raise ValueError("ss proxy requires `cipher` and `password`")
        elif t == "ssr":
            if not self.cipher or not self.password or not self.protocol or not self.obfs:
                raise ValueError("ssr proxy requires `cipher`, `password`, `protocol`, `obfs`")
        elif t == "vmess":
            if not self.uuid:
                raise ValueError("vmess proxy requires `uuid`")
        elif t in ("trojan", "hysteria2"):
            if not self.password:
                raise ValueError(f"{t} proxy requires `password`")
        elif t == "hysteria":
            if not self.auth_str:
                raise ValueError("hysteria proxy requires `auth_str`")
        return self

    def to_clash_dict(self) -> dict[str, Any]:
        """Return a Clash-compatible dict containing only set fields.

        Field names are emitted in a stable, Clash-canonical order so that
        round-tripping a node through this model produces deterministic YAML.
        """
        optional_order: list[tuple[str, str | None]] = [
            ("cipher", "cipher"),
            ("password", "password"),
            ("uuid", "uuid"),
            ("alterId", "alter_id"),
            ("udp", "udp"),
            ("tls", "tls"),
            ("sni", "sni"),
            ("alpn", "alpn"),
            ("skip-cert-verify", "skip_cert_verify"),
            ("network", "network"),
            ("ws-path", "ws_path"),
            ("ws-headers", "ws_headers"),
            ("protocol", "protocol"),
            ("protocol-param", "protocol_param"),
            ("obfs", "obfs"),
            ("obfs-param", "obfs_param"),
            ("username", "username"),
            ("auth_str", "auth_str"),
        ]
        out: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "server": self.server,
            "port": self.port,
        }
        for clash_key, attr in optional_order:
            value = getattr(self, attr)
            if value is not None:
                out[clash_key] = value
        for key, value in self.extra.items():
            out.setdefault(key, value)
        return out

    def fingerprint(self) -> str:
        """Stable identity used for dedup.

        Credentials (uuid/password) are the strongest signal, followed by
        transport (server+port) and crypto details.
        """
        parts: list[tuple[str, Any]] = [
            ("type", self.type),
            ("server", self.server),
            ("port", self.port),
        ]
        for key in (
            "password",
            "uuid",
            "cipher",
            "alter_id",
            "protocol",
            "obfs",
        ):
            value = getattr(self, key)
            if value is not None:
                parts.append((key, value))
        raw = "|".join(f"{k}={v}" for k, v in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

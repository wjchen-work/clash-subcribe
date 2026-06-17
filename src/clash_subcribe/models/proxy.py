"""Proxy node data model.

A Clash proxy node is polymorphic (different types carry different fields);
because protocols keep evolving, this model is intentionally permissive —
unknown fields are preserved verbatim in :attr:`Proxy.model_extra` and only
the truly universal metadata (``name`` / ``type`` / ``server`` / ``port``)
is treated as required. Per-type invariants (``ss`` 必须带 ``cipher`` 之类)
are **not** enforced here; the downstream Clash client is the source of truth
for protocol-level validity. :meth:`Proxy.fingerprint` collapses nodes from
different providers that ultimately point at the same backend.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProxyType = str

_TYPE_ALIASES: dict[str, str] = {
    "hy2": "hysteria2",
}


class Proxy(BaseModel):
    """A single Clash proxy node.

    Required: ``name``, ``type``, ``server``, ``port``. Any additional keys
    present in the source subscription are preserved in :attr:`model_extra`
    and round-tripped through :meth:`to_clash_dict`, so newly-introduced
    protocol fields (e.g. an unknown ``type`` or transport-specific option)
    flow through untouched.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

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

    def to_clash_dict(self) -> dict[str, Any]:
        """Return a Clash-compatible dict containing only set fields.

        Field names are emitted in a stable, Clash-canonical order so that
        round-tripping a node through this model produces deterministic YAML.
        Unknown source fields (``model_extra``) are merged in, last-wins on
        collisions with declared fields, so newly-added protocol options
        survive the round-trip.
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
        for key, value in (self.model_extra or {}).items():
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

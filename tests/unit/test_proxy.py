"""Unit tests for the ``Proxy`` data model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from clash_subcribe.models import Proxy


class TestProxyConstruction:
    def test_minimal_ss(self) -> None:
        p = Proxy(
            name="n",
            type="ss",
            server="1.1.1.1",
            port=8388,
            cipher="aes-256-gcm",
            password="x",
        )
        assert p.type == "ss"
        assert p.to_clash_dict() == {
            "name": "n",
            "type": "ss",
            "server": "1.1.1.1",
            "port": 8388,
            "cipher": "aes-256-gcm",
            "password": "x",
        }

    def test_type_alias_hy2_to_hysteria2(self) -> None:
        p = Proxy(name="n", type="hy2", server="1.1.1.1", port=443, password="x")
        assert p.type == "hysteria2"

    def test_required_field_missing_raises(self) -> None:
        with pytest.raises(ValidationError):
            Proxy(name="n", type="ss", server="1.1.1.1", port=8388, password="x")

    def test_invalid_port_raises(self) -> None:
        with pytest.raises(ValidationError):
            Proxy(
                name="n",
                type="ss",
                server="1.1.1.1",
                port=99999,
                cipher="aes-256-gcm",
                password="x",
            )

    def test_alias_fields_round_trip(self) -> None:
        p = Proxy.model_validate(
            {
                "name": "n",
                "type": "vmess",
                "server": "1.1.1.1",
                "port": 443,
                "uuid": "u",
                "alterId": 1,
                "ws-path": "/ws",
                "ws-headers": {"Host": "h"},
            }
        )
        assert p.alter_id == 1
        assert p.ws_path == "/ws"
        assert p.to_clash_dict()["alterId"] == 1


class TestProxyFingerprint:
    def test_same_backend_collapses(self) -> None:
        a = Proxy(
            name="A", type="ss", server="1.1.1.1", port=8388, cipher="aes-256-gcm", password="x"
        )
        b = Proxy(
            name="B", type="ss", server="1.1.1.1", port=8388, cipher="aes-256-gcm", password="x"
        )
        assert a.fingerprint() == b.fingerprint()

    def test_different_credentials_diverge(self) -> None:
        a = Proxy(
            name="A", type="ss", server="1.1.1.1", port=8388, cipher="aes-256-gcm", password="x"
        )
        b = Proxy(
            name="B", type="ss", server="1.1.1.1", port=8388, cipher="aes-256-gcm", password="y"
        )
        assert a.fingerprint() != b.fingerprint()

    def test_different_type_diverge(self) -> None:
        a = Proxy(
            name="A", type="ss", server="1.1.1.1", port=8388, cipher="aes-256-gcm", password="x"
        )
        b = Proxy(name="B", type="trojan", server="1.1.1.1", port=8388, password="x")
        assert a.fingerprint() != b.fingerprint()

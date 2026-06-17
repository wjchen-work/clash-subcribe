"""Unit tests for the ``Proxy`` data model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from clash_subcribe.models import Proxy


class TestProxyConstruction:
    def test_minimal_node(self) -> None:
        """Only name/type/server/port are required — protocol fields are not."""
        p = Proxy(name="n", type="ss", server="1.1.1.1", port=8388)
        assert p.type == "ss"
        assert p.to_clash_dict() == {
            "name": "n",
            "type": "ss",
            "server": "1.1.1.1",
            "port": 8388,
        }

    def test_full_ss_round_trips(self) -> None:
        p = Proxy(
            name="n",
            type="ss",
            server="1.1.1.1",
            port=8388,
            cipher="aes-256-gcm",
            password="x",
        )
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

    def test_ss_without_cipher_or_password_is_accepted(self) -> None:
        """Protocols evolve; we don't enforce per-type required fields."""
        p = Proxy(name="n", type="ss", server="1.1.1.1", port=8388)
        assert p.cipher is None
        assert p.password is None

    def test_unknown_type_is_kept(self) -> None:
        """A novel protocol type must pass through untouched."""
        p = Proxy(name="n", type="some-future-proxy", server="1.1.1.1", port=443)
        assert p.type == "some-future-proxy"
        assert p.to_clash_dict()["type"] == "some-future-proxy"

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

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Proxy(name="n", type="ss", server="1.1.1.1")
        with pytest.raises(ValidationError):
            Proxy(name="n", type="ss", port=443)
        with pytest.raises(ValidationError):
            Proxy(name="n", server="1.1.1.1", port=443)

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

    def test_unknown_fields_are_preserved(self) -> None:
        """Protocols keep evolving: unknown subscription fields must flow through."""
        p = Proxy.model_validate(
            {
                "name": "n",
                "type": "ss",
                "server": "1.1.1.1",
                "port": 443,
                "cipher": "aes-256-gcm",
                "password": "x",
                "future-option": "rocket-fuel",
                "fingerprint": "chrome",
            }
        )
        out = p.to_clash_dict()
        assert out["future-option"] == "rocket-fuel"
        assert out["fingerprint"] == "chrome"


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

"""Shared test fixtures."""

from __future__ import annotations

from textwrap import dedent

from clash_subcribe.models import Proxy

HK_SS = Proxy(
    name="HK-01",
    type="ss",
    server="1.1.1.1",
    port=8388,
    cipher="aes-256-gcm",
    password="sspass",
)
HK_SS_DUP = Proxy(
    name="HK-01 [reseller]",
    type="ss",
    server="1.1.1.1",
    port=8388,
    cipher="aes-256-gcm",
    password="sspass",
)
JP_TROJAN = Proxy(
    name="JP-01",
    type="trojan",
    server="3.3.3.3",
    port=443,
    password="tjpass",
    sni="jp.example.com",
)
US_VMESS = Proxy(
    name="US-NY-01",
    type="vmess",
    server="2.2.2.2",
    port=443,
    uuid="00000000-0000-0000-0000-000000000001",
    alter_id=0,
)
JP_FREE = Proxy(
    name="JP-02 免费",
    type="trojan",
    server="3.3.3.4",
    port=443,
    password="tjpass",
)

SAMPLE_PROXIES: list[Proxy] = [HK_SS, HK_SS_DUP, JP_TROJAN, US_VMESS, JP_FREE]

SAMPLE_YAML = dedent(
    """
    proxies:
      - name: HK-01
        type: ss
        server: 1.1.1.1
        port: 8388
        cipher: aes-256-gcm
        password: sspass
      - name: broken
        type: ss
        server: 3.3.3.3
        port: 8388
      - name: US-NY-01
        type: vmess
        server: 2.2.2.2
        port: 443
        uuid: 00000000-0000-0000-0000-000000000001
    """
).lstrip()

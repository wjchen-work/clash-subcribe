"""Unit tests for the file + HTTP fetchers.

The HTTP test uses :mod:`respx` to mock httpx without touching the network.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from clash_subcribe.config import SourceConfig
from clash_subcribe.exceptions import SourceFetchError
from clash_subcribe.fetcher import HttpFetcher, redact_url

# --------------------------------------------------------------------------------------
# FileFetcher
# --------------------------------------------------------------------------------------


def test_file_fetcher_reads_local(tmp_path: Path) -> None:
    sub = tmp_path / "sub.yaml"
    sub.write_text("proxies: []\n", encoding="utf-8")
    src = SourceConfig(name="local", path=str(sub))
    result = __import__("clash_subcribe.fetcher", fromlist=["FileFetcher"]).FileFetcher(src).fetch()
    assert result.text == "proxies: []\n"
    assert result.bytes == len(b"proxies: []\n")


def test_file_fetcher_missing_file(tmp_path: Path) -> None:
    from clash_subcribe.fetcher import FileFetcher

    src = SourceConfig(name="local", path=str(tmp_path / "nope.yaml"))
    with pytest.raises(SourceFetchError):
        FileFetcher(src).fetch()


# --------------------------------------------------------------------------------------
# HttpFetcher
# --------------------------------------------------------------------------------------


def test_redact_url_strips_path() -> None:
    assert redact_url("https://sub.example.com/abc?token=secret") == "https://sub.example.com/***"


def test_redact_url_handles_garbage() -> None:
    assert redact_url("not a url") == "***"


@respx.mock
def test_http_fetcher_success() -> None:
    respx.get("https://sub.example.com/abc").mock(
        return_value=httpx.Response(200, text="proxies: []\n")
    )
    src = SourceConfig(name="a", url="https://sub.example.com/abc")
    result = HttpFetcher(src).fetch()
    assert result.status == 200
    assert result.text == "proxies: []\n"


@respx.mock
def test_http_fetcher_4xx_is_unrecoverable() -> None:
    respx.get("https://sub.example.com/abc").mock(return_value=httpx.Response(404))
    src = SourceConfig(name="a", url="https://sub.example.com/abc", required=True)
    with pytest.raises(SourceFetchError):
        HttpFetcher(src).fetch()


@respx.mock
def test_http_fetcher_5xx_retries_then_succeeds() -> None:
    route = respx.get("https://sub.example.com/abc").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, text="proxies: []\n"),
        ]
    )
    src = SourceConfig(name="a", url="https://sub.example.com/abc")
    result = HttpFetcher(src, backoff_seconds=0.0).fetch()
    assert result.text == "proxies: []\n"
    assert route.call_count == 3

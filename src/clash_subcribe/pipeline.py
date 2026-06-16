"""Top-level pipeline orchestrator.

Stages (each one independent, each one testable in isolation)::

    fetch -> parse -> merge -> processors -> render -> emit

The orchestrator's only job is to thread context (timers, partial failures,
final stats) between the stages and emit the §5.2 log lines.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

import httpx

from . import emitter as emitter_pkg
from . import fetcher as fetcher_pkg
from . import parser as parser_pkg
from . import processors as processors_pkg
from .config import UserConfig
from .emitter import Emitter
from .exceptions import SourceFetchError
from .models import Proxy
from .renderer import ClashRenderer

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Summary returned by :func:`run` for the CLI to translate into an exit code."""

    proxy_count: int
    output_target: str
    failed_sources: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


def run(
    config: UserConfig,
    *,
    client: httpx.Client | None = None,
    stream: IO[str] | None = None,
    path: str | Path | None = None,
) -> PipelineResult:
    """Execute the full pipeline against a validated :class:`UserConfig`.

    Args:
        config: validated user config.
        client: optional shared ``httpx.Client`` — pass one from tests to enable mocking.
        stream: override the stdout stream (used in tests).
        path: override the file output path (used in tests).

    Returns:
        A :class:`PipelineResult` summarising what happened.

    Raises:
        SourceFetchError: when a ``required: true`` source fails.
        ConfigError / RenderError / EmitError: from individual stages.
    """
    started = time.perf_counter()
    processor_names = [p.name for p in config.processors]
    logger.info(
        "启动订阅处理 pipeline（%d 个源，%d 个 processors: %s，输出 -> %s）",
        len(config.sources),
        len(processor_names),
        processor_names or "<none>",
        _describe_output(config),
    )

    proxies, failed = _gather_proxies(config, client=client)
    logger.info("合并完成：%d 节点", len(proxies))

    for entry in config.processors:
        processor = processors_pkg.build(entry)
        proxies = processor(proxies)

    renderer = ClashRenderer(_template_path(config))
    yaml_text = renderer.render(proxies)

    emitter: Emitter = emitter_pkg.make_emitter(config.output, stream=stream, path=path)
    emitter.emit(yaml_text)

    duration = time.perf_counter() - started
    logger.info("完成，总耗时 %.2fs, %d 节点", duration, len(proxies))
    return PipelineResult(
        proxy_count=len(proxies),
        output_target=_describe_output(config),
        failed_sources=failed,
        duration_seconds=duration,
    )


# --------------------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------------------


def _gather_proxies(
    config: UserConfig,
    *,
    client: httpx.Client | None,
) -> tuple[list[Proxy], list[str]]:
    """Fetch + parse every source. Collect failures separately so a single bad
    source doesn't kill the whole pipeline (unless it's marked ``required``)."""
    all_proxies: list[Proxy] = []
    failed: list[str] = []
    for index, source in enumerate(config.sources, start=1):
        logger.info("[源 %d/%d] 处理: %s", index, len(config.sources), source.name)
        try:
            fetcher = fetcher_pkg.make_fetcher(source, client=client)
            result = fetcher.fetch()
        except SourceFetchError as exc:
            logger.error("[%s] 抓取失败: %s", source.name, exc, exc_info=True)
            if source.required:
                raise
            failed.append(source.name)
            continue

        parser = parser_pkg.make_parser(result.text)
        try:
            proxies = parser.parse(result.text)
        except Exception as exc:  # parser-level errors are unrecoverable for that source
            logger.error("[%s] 解析失败: %s", source.name, exc, exc_info=True)
            if source.required:
                raise
            failed.append(source.name)
            continue

        all_proxies.extend(proxies)
    return all_proxies, failed


def _template_path(config: UserConfig) -> str | None:
    output = config.output
    if getattr(output, "template", None):
        return output.template
    return None


def _describe_output(config: UserConfig) -> str:
    output = config.output
    if output.type == "file":
        return output.path
    if output.type == "stdout":
        return "stdout"
    if output.type == "http":
        return f"http://{output.host}:{output.port}/"
    return output.type

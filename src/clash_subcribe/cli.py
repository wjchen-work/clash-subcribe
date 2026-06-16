"""Command-line entry point.

Built on :mod:`click`. The CLI is intentionally thin — it parses args, hands
off to :func:`clash_subcribe.pipeline.run`, and translates the result into
the §7 exit codes (0 success, 1 partial, 2 total failure).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import click

from . import __version__
from .config import (
    FileOutputConfig,
    HttpOutputConfig,
    StdoutOutputConfig,
    UserConfig,
    load_config,
)
from .exceptions import ClashSubError, ConfigError
from .logging_setup import configure_logging
from .pipeline import run as run_pipeline

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FAIL = 2


@click.command(
    name="clash-subcribe",
    help="合并多个 Clash 订阅源并按规则处理为单一输出。",
)
@click.version_option(__version__, prog_name="clash-subcribe")
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    required=True,
    help="用户配置 YAML 路径（必填）。",
)
@click.option(
    "-o",
    "--output",
    "output_override",
    type=click.Choice(["file", "stdout", "http"]),
    default=None,
    help="覆盖配置中的 output.type。",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="追加写入日志的文件路径。",
)
@click.option("-v", "--verbose", is_flag=True, help="DEBUG 日志。")
@click.option("-q", "--quiet", is_flag=True, help="仅 WARNING 及以上。")
def main(
    config_path: Path,
    output_override: str | None,
    log_file: Path | None,
    verbose: bool,
    quiet: bool,
) -> int:
    """CLI entry — return value is the process exit code."""
    level = "DEBUG" if verbose else "WARNING" if quiet else "INFO"
    configure_logging(level=level, log_file=log_file)
    logger = logging.getLogger("clash_subcribe.cli")
    logger.debug("加载配置: %s", config_path)

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        logger.error("%s", exc)
        return EXIT_FAIL

    config = _apply_output_override(config, output_override)

    try:
        result = run_pipeline(config)
    except ClashSubError as exc:
        logger.error("%s", exc, exc_info=True)
        return EXIT_FAIL

    if result.failed_sources:
        logger.warning(
            "部分源失败: %s — 输出已生成（%d 节点）",
            result.failed_sources,
            result.proxy_count,
        )
        return EXIT_PARTIAL
    return EXIT_OK


def _apply_output_override(config: UserConfig, override: str | None) -> UserConfig:
    """Build a new :class:`UserConfig` with the overridden output type.

    Preserves the rest of the user's settings (template, file path, etc.)
    by reusing the existing output's fields when relevant.
    """
    if override is None:
        return config
    current = config.output
    if current.type == override:
        return config
    new_output: Any
    if override == "stdout":
        new_output = StdoutOutputConfig(type="stdout", template=getattr(current, "template", None))
    elif override == "file":
        path = getattr(current, "path", "./output.yaml")
        new_output = FileOutputConfig(
            type="file", path=path, template=getattr(current, "template", None)
        )
    elif override == "http":
        host = getattr(current, "host", "127.0.0.1")
        port = getattr(current, "port", 8080)
        new_output = HttpOutputConfig(
            type="http",
            host=host,
            port=port,
            template=getattr(current, "template", None),
        )
    else:  # pragma: no cover — click.Choice already guards this
        raise ConfigError(f"unsupported output override: {override}")
    return config.model_copy(update={"output": new_output})


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

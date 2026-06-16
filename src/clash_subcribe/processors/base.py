"""Processor base class + registry.

A :class:`Processor` is a pure ``list[Proxy] -> list[Proxy]`` function
wrapped in a small adapter that handles timing + the §5.2 INFO log line.
Concrete processors live in sibling modules and register via
:func:`register`.
"""

from __future__ import annotations

import abc
import logging
import time
from collections.abc import Callable
from typing import Any, ClassVar

from ..config import ProcessorEntry
from ..exceptions import ConfigError
from ..models import Proxy

logger = logging.getLogger(__name__)

# A processor builder consumes a YAML options dict and returns a configured
# processor instance. Keeping it as a function (not a class) lets each module
# reject unknown options up-front.
ProcessorBuilder = Callable[[dict[str, Any]], "Processor"]


class Processor(abc.ABC):
    """Abstract processor — :meth:`apply` is the work; :meth:`__call__` is sugar."""

    name: ClassVar[str] = ""

    @abc.abstractmethod
    def apply(self, proxies: list[Proxy]) -> list[Proxy]:
        """Return a (possibly mutated) proxy list. Must be a pure function."""

    def __call__(self, proxies: list[Proxy]) -> list[Proxy]:
        started = time.perf_counter()
        before = len(proxies)
        result = list(self.apply(proxies))
        duration = time.perf_counter() - started
        logger.info(
            "[%s] %d -> %d, %.3fs",
            self.name or type(self).__name__,
            before,
            len(result),
            duration,
        )
        return result


# Registry is populated by sibling modules importing this module's
# :func:`register` function. Sibling modules patch at import time so we avoid a
# hard import order.
REGISTRY: dict[str, ProcessorBuilder] = {}


def register(name: str, builder: ProcessorBuilder) -> None:
    """Register a processor builder. Raises on name collision so typos surface early."""
    if name in REGISTRY:
        raise RuntimeError(f"processor {name!r} already registered")
    REGISTRY[name] = builder


def build(entry: ProcessorEntry) -> Processor:
    """Instantiate a processor from a config entry. Raises :class:`ConfigError`."""
    try:
        builder = REGISTRY[entry.name]
    except KeyError as exc:
        raise ConfigError(f"未知 processor: {entry.name!r}；可用: {sorted(REGISTRY)}") from exc
    try:
        return builder(entry.options)
    except Exception as exc:
        raise ConfigError(f"processor {entry.name!r} 选项无效: {exc}") from exc

"""Emitter base class.

An emitter's only job is to deliver the rendered YAML text to a destination
(file, stdout, or eventually an HTTP server). The renderer has no idea
where its output goes. The factory lives in the package ``__init__`` to
sidestep the circular import the concrete emitters would otherwise create.
"""

from __future__ import annotations

import abc
import logging

logger = logging.getLogger(__name__)


class Emitter(abc.ABC):
    """Abstract emitter — subclasses implement :meth:`emit`."""

    @abc.abstractmethod
    def emit(self, text: str) -> None:
        """Deliver ``text`` to the configured destination."""


__all__ = ["Emitter"]

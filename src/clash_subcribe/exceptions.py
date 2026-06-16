"""Custom exception hierarchy for clash-subcribe.

The base :class:`ClashSubError` anchors every domain-level failure so the CLI
can map any pipeline error to a sensible exit code. Subclasses intentionally
stay small — they carry a human-readable message and the original cause.
"""

from __future__ import annotations


class ClashSubError(Exception):
    """Base class for all clash-subcribe domain errors."""


class ConfigError(ClashSubError):
    """Raised when the user configuration cannot be loaded or validated."""


class SourceFetchError(ClashSubError):
    """Raised when a subscription source cannot be fetched after all retries."""


class ParseError(ClashSubError):
    """Raised when a fetcher payload cannot be turned into Proxy models."""


class RenderError(ClashSubError):
    """Raised when rendering the final Clash YAML fails."""


class EmitError(ClashSubError):
    """Raised when an emitter cannot deliver the rendered output."""

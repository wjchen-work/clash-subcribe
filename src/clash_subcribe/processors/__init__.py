"""Re-exports + import-side registration for the ``processors`` package.

Importing populates :data:`clash_subcribe.processors.base.REGISTRY` with the
built-in processors.
"""

from . import dedup, filter, rename, sort
from .base import REGISTRY, Processor, build, register

DedupProcessor = dedup.DedupProcessor
FilterProcessor = filter.FilterProcessor
RenameProcessor = rename.RenameProcessor
SortProcessor = sort.SortProcessor

__all__ = [
    "DedupProcessor",
    "FilterProcessor",
    "Processor",
    "REGISTRY",
    "RenameProcessor",
    "SortProcessor",
    "build",
    "register",
]

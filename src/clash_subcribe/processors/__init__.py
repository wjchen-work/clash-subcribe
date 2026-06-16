"""Re-exports + import-side registration for the ``processors`` package.

Importing this package has the side effect of populating
:data:`clash_subcribe.processors.base.REGISTRY` with the built-in processors.
Order matters only for readability — registrations are independent.
"""

from . import dedup, filter, rename, sort
from .base import REGISTRY, Processor, build, register

# Re-export the concrete classes for users who want to compose manually.
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

"""Project-wide pytest fixtures.

We keep the fixtures small and explicit — anything fancier (parametrize,
autouse) lives in the individual test files.
"""

from __future__ import annotations

import pytest

from clash_subcribe import logging_setup
from tests._fixtures import SAMPLE_PROXIES, SAMPLE_YAML  # noqa: F401  re-exported

# Quiet the project's loggers during tests so the test runner output stays readable.
logging_setup.configure_logging(level="WARNING")


@pytest.fixture
def sample_proxies() -> list:
    return list(SAMPLE_PROXIES)


@pytest.fixture
def sample_yaml() -> str:
    return SAMPLE_YAML

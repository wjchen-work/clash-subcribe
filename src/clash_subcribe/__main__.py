"""``python -m clash_subcribe`` entry point."""

import click

from .cli import main
from .exceptions import ClashSubError
from .logging_setup import configure_logging


def invoke() -> None:
    """Configure default logging and delegate to the Click command.

    Splitting this from the bare ``main`` import keeps Click's decorator-driven
    exception handling (which we want for proper exit codes on bad args) in
    place even when ``main(standalone_mode=False)`` is used by tests.
    """
    try:
        main(standalone_mode=True)
    except ClashSubError as exc:
        configure_logging(level="INFO")
        click.echo(f"clash-subcribe: {exc}", err=True)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    invoke()

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Shared command line plumbing for the oscclip tools."""

from __future__ import annotations

import argparse
import functools
import logging
import sys
from collections.abc import Callable, Sequence
from importlib import metadata
from typing import NoReturn

from oscclip.clipboard import DEFAULT_TIMEOUT, Protocol, Settings
from oscclip.errors import ClipboardError


def get_version() -> str:
    """Return the installed oscclip version."""
    try:
        return metadata.version("oscclip")
    except metadata.PackageNotFoundError:
        return "unknown"


def die(message: str) -> NoReturn:
    """Print an error message and exit with status 1."""
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def add_bypass_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --bypass argument to a parser."""
    parser.add_argument(
        "--bypass",
        action="store_true",
        help="bypass terminal multiplexers like tmux and screen",
    )


def add_protocol_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --protocol argument to a parser."""
    parser.add_argument(
        "--protocol",
        type=Protocol,
        choices=list(Protocol),
        default=Protocol.AUTO,
        help="clipboard protocol to use (default: %(default)s)",
    )


def add_timeout_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --timeout argument to a parser."""
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="timeout in seconds for terminal responses (default: %(default)s)",
    )


def add_version_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --version argument to a parser."""
    parser.add_argument("--version", action="version", version=f"%(prog)s {get_version()}")


def add_verbose_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --verbose argument to a parser."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log protocol details to stderr",
    )


def configure_logging(verbose: bool) -> None:
    """Configure logging for the command line tools."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )


def settings_from_args(args: argparse.Namespace) -> Settings:
    """Build clipboard settings from parsed command line arguments."""
    return Settings(
        primary=args.primary,
        bypass=args.bypass,
        protocol=args.protocol,
        timeout=args.timeout,
    )


def entrypoint(
    func: Callable[[Sequence[str] | None], int],
) -> Callable[[Sequence[str] | None], int]:
    """Turn a CLI implementation into a console entry point.

    Keyboard interrupts and clipboard/terminal errors are translated into
    friendly messages and exit codes.
    """

    @functools.wraps(func)
    def main(argv: Sequence[str] | None = None) -> int:
        try:
            return func(argv)
        except KeyboardInterrupt:
            print("error: interrupted", file=sys.stderr)
            return 130
        except ClipboardError as e:
            die(str(e))
        except OSError as e:
            die(f"cannot access the controlling terminal: {e}")

    return main

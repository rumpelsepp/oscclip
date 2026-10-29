# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""Shared command line plumbing for the oscclip tools."""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from typing import NoReturn

from .clipboard import DEFAULT_TIMEOUT, Protocol


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

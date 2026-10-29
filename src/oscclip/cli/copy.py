# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""osc-copy: copy data to the system clipboard via terminal escape sequences."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .. import clipboard
from ..term import RawTerminal
from . import (
    add_bypass_arg,
    add_protocol_arg,
    add_timeout_arg,
    add_version_arg,
    entrypoint,
    settings_from_args,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the osc-copy argument parser."""
    parser = argparse.ArgumentParser(
        prog="osc-copy",
        description="Copy data to the system clipboard via terminal escape sequences.",
    )
    parser.add_argument(
        "text",
        nargs="?",
        default="-",
        help="text to copy; '-' or no argument reads from stdin (default: '-')",
    )
    parser.add_argument("-c", "--clear", action="store_true", help="clear the clipboard and exit")
    parser.add_argument(
        "-p", "--primary", action="store_true", help="use the primary X11 selection"
    )
    parser.add_argument("-t", "--trim", action="store_true", help="trim whitespace of the input")
    parser.add_argument(
        "-m", "--mime", default="text/plain", help="MIME type of the data (default: %(default)s)"
    )
    add_bypass_arg(parser)
    add_protocol_arg(parser)
    add_timeout_arg(parser)
    add_version_arg(parser)
    return parser


def read_input(args: argparse.Namespace) -> bytes:
    """Read the data to copy from stdin or the positional argument."""
    if args.text == "-":
        return sys.stdin.buffer.read()
    text: str = args.text
    return text.encode()


def copy(args: argparse.Namespace) -> int:
    """Copy data to the system clipboard."""
    data = b"" if args.clear else read_input(args)
    if args.trim:
        data = data.strip()

    settings = settings_from_args(args)
    with RawTerminal() as term:
        if args.clear:
            clipboard.clear(term, settings)
        else:
            clipboard.copy(term, data, settings, mime=args.mime)
    return 0


@entrypoint
def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for osc-copy."""
    args = build_parser().parse_args(argv)
    return copy(args)

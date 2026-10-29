# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""osc-copy: copy data to the system clipboard via terminal escape sequences."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import clipboard, mux
from .cli import add_bypass_arg, add_protocol_arg, add_timeout_arg, add_version_arg, die
from .errors import ClipboardError
from .term import RawTerminal


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


def run(argv: Sequence[str] | None = None) -> int:
    """Run osc-copy."""
    args = build_parser().parse_args(argv)
    if args.bypass:
        mux.warn_tmux_passthrough(sys.stderr)

    if args.clear:
        data = b""
    elif args.text == "-":
        data = sys.stdin.buffer.read()
    else:
        data = args.text.encode()

    if args.trim:
        data = data.strip()

    try:
        with RawTerminal() as term:
            if args.clear:
                clipboard.clear(
                    term,
                    primary=args.primary,
                    bypass=args.bypass,
                    protocol=args.protocol,
                    timeout=args.timeout,
                )
            else:
                clipboard.copy(
                    term,
                    data,
                    mime=args.mime,
                    primary=args.primary,
                    bypass=args.bypass,
                    protocol=args.protocol,
                    timeout=args.timeout,
                )
    except ClipboardError as e:
        die(str(e))
    except OSError as e:
        die(f"cannot access the controlling terminal: {e}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for osc-copy."""
    try:
        return run(argv)
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130

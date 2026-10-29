# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""osc-paste: read data from the system clipboard via terminal escape sequences."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import clipboard, mux
from .cli import add_bypass_arg, add_protocol_arg, add_timeout_arg, add_version_arg, die
from .clipboard import ClipboardContent
from .errors import ClipboardError, ClipboardTimeoutError
from .term import RawTerminal


def build_parser() -> argparse.ArgumentParser:
    """Build the osc-paste argument parser."""
    parser = argparse.ArgumentParser(
        prog="osc-paste",
        description="Read data from the system clipboard via terminal escape sequences.",
    )
    parser.add_argument(
        "-p", "--primary", action="store_true", help="use the primary X11 selection"
    )
    parser.add_argument("-t", "--trim", action="store_true", help="trim whitespace of the output")
    parser.add_argument(
        "-m",
        "--mime",
        action="append",
        metavar="MIME",
        help="MIME type to read; may be given multiple times (default: text/plain)",
    )
    parser.add_argument(
        "--list-mime",
        action="store_true",
        help="list the MIME types available on the clipboard and exit",
    )
    add_bypass_arg(parser)
    add_protocol_arg(parser)
    add_timeout_arg(parser)
    add_version_arg(parser)
    return parser


def _write_output(content: ClipboardContent, *, trim: bool) -> None:
    """Write clipboard data to stdout."""
    data = content.data
    if trim:
        data = data.strip()
    if content.mime == "text/plain" and not trim and not data.endswith(b"\n"):
        data += b"\n"
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def run(argv: Sequence[str] | None = None) -> int:
    """Run osc-paste."""
    args = build_parser().parse_args(argv)
    if args.bypass:
        mux.warn_tmux_passthrough(sys.stderr)
    mimes = args.mime or ["text/plain"]

    try:
        with RawTerminal() as term:
            if args.list_mime:
                for mime in clipboard.list_mime(
                    term,
                    primary=args.primary,
                    bypass=args.bypass,
                    protocol=args.protocol,
                    timeout=args.timeout,
                ):
                    print(mime)
                return 0
            content = clipboard.paste(
                term,
                mimes=mimes,
                primary=args.primary,
                bypass=args.bypass,
                protocol=args.protocol,
                timeout=args.timeout,
            )
    except ClipboardTimeoutError as e:
        message = str(e)
        if mux.in_tmux():
            message += (
                " (hint: enable tmux's `get-clipboard` option, "
                "e.g. `tmux set -s get-clipboard both`)"
            )
        die(message)
    except ClipboardError as e:
        die(str(e))
    except OSError as e:
        die(f"cannot access the controlling terminal: {e}")

    if not content.data:
        die("the clipboard is empty")
    _write_output(content, trim=args.trim)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for osc-paste."""
    try:
        return run(argv)
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130

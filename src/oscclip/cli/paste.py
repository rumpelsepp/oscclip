# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""osc-paste: read data from the system clipboard via terminal escape sequences."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from oscclip import clipboard
from oscclip.cli import (
    add_bypass_arg,
    add_protocol_arg,
    add_timeout_arg,
    add_version_arg,
    die,
    entrypoint,
    settings_from_args,
)
from oscclip.clipboard import ClipboardContent
from oscclip.term import RawTerminal


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


def write_output(content: ClipboardContent, *, trim: bool) -> None:
    """Write clipboard data to stdout."""
    data = content.data
    if trim:
        data = data.strip()
    if content.mime == "text/plain" and not trim and not data.endswith(b"\n"):
        data += b"\n"
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def paste(args: argparse.Namespace) -> int:
    """Read data from the system clipboard."""
    mimes = args.mime or ["text/plain"]
    settings = settings_from_args(args)

    with RawTerminal() as term:
        if args.list_mime:
            for mime in clipboard.list_mime(term, settings):
                print(mime)
            return 0
        content = clipboard.paste(term, settings, mimes=mimes)

    if not content.data:
        die("the clipboard is empty")
    write_output(content, trim=args.trim)
    return 0


@entrypoint
def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for osc-paste."""
    args = build_parser().parse_args(argv)
    return paste(args)

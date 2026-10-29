# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The OSC 52 clipboard escape sequence protocol."""

from __future__ import annotations

from oscclip.errors import ClipboardTimeoutError
from oscclip.osc52.build import clear_sequence, copy_sequence, query_sequence
from oscclip.osc52.parse import RESPONSE_RE, Osc52Response, parse_response
from oscclip.term import Terminal

__all__ = [
    "RESPONSE_RE",
    "Osc52Response",
    "clear_sequence",
    "copy_sequence",
    "parse_response",
    "query",
    "query_sequence",
]


def query(tty: Terminal, *, primary: bool, timeout: float) -> Osc52Response:
    """Query the system clipboard via OSC 52 and parse the response."""
    tty.write(query_sequence(primary=primary))
    match = tty.read_until([RESPONSE_RE], timeout)
    if match is None:
        raise ClipboardTimeoutError("the terminal did not respond to the clipboard query")
    return parse_response(match)

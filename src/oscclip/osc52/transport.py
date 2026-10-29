# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Terminal I/O for the OSC 52 protocol."""

from __future__ import annotations

import logging

from oscclip.errors import ClipboardTimeoutError
from oscclip.osc52 import build, parse
from oscclip.osc52.parse import Osc52Response
from oscclip.term import Terminal

logger = logging.getLogger(__name__)


def copy(tty: Terminal, data: bytes, *, primary: bool = False) -> None:
    """Copy data to the system clipboard."""
    logger.debug("copying %d bytes to the clipboard via OSC 52", len(data))
    tty.write(build.copy_sequence(data, primary=primary))


def clear(tty: Terminal, *, primary: bool = False) -> None:
    """Clear the system clipboard."""
    logger.debug("clearing the clipboard via OSC 52")
    tty.write(build.clear_sequence(primary=primary))


def query(tty: Terminal, *, primary: bool, timeout: float) -> Osc52Response:
    """Query the system clipboard and parse the response."""
    logger.debug("querying the clipboard via OSC 52")
    tty.write(build.query_sequence(primary=primary))
    match = tty.read_until([parse.RESPONSE_RE], timeout)
    if match is None:
        raise ClipboardTimeoutError("the terminal did not respond to the clipboard query")
    response = parse.parse_response(match)
    logger.debug("received response from source=%s (%d bytes)", response.source, len(response.data))
    return response

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The OSC 52 clipboard escape sequence protocol."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass

from .errors import ClipboardProtocolError

ESC = b"\x1b"
OSC = ESC + b"]"
BEL = b"\x07"
ST = ESC + b"\\"

#: Matches OSC 52 clipboard responses with either BEL or ST terminator.
RESPONSE_RE = re.compile(rb"\x1b\]52;([a-zA-Z0-9]*)(?:;([A-Za-z0-9+/=]*))?(?:\x07|\x1b\\)")


@dataclass(frozen=True)
class Osc52Response:
    """A response to an OSC 52 clipboard query."""

    source: str
    data: bytes


def _loc(primary: bool) -> bytes:
    return b"p" if primary else b"c"


def build_copy(data: bytes, *, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which sets the system clipboard."""
    return OSC + b"52;" + _loc(primary) + b";" + base64.b64encode(data) + BEL


def build_query(*, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which queries the system clipboard."""
    return OSC + b"52;" + _loc(primary) + b";?" + BEL


def build_clear(*, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which clears the system clipboard."""
    return OSC + b"52;" + _loc(primary) + b";!" + BEL


def parse_response(match: re.Match[bytes]) -> Osc52Response:
    """Parse an OSC 52 clipboard response."""
    source = match.group(1).decode()
    data = b""
    if encoded := match.group(2):
        try:
            data = base64.b64decode(encoded, validate=True)
        except binascii.Error as e:
            raise ClipboardProtocolError(f"invalid base64 data in OSC 52 response: {e}") from e
    return Osc52Response(source=source, data=data)

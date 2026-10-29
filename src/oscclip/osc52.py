# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The OSC 52 clipboard escape sequence protocol."""

from __future__ import annotations

import base64
import re

from pydantic import BaseModel, ConfigDict, ValidationError

from oscclip.encoding import Base64Bytes
from oscclip.errors import ClipboardProtocolError

ESC = b"\x1b"
OSC = ESC + b"]"
BEL = b"\x07"
ST = ESC + b"\\"

#: Matches OSC 52 clipboard responses with either BEL or ST terminator.
RESPONSE_RE = re.compile(rb"\x1b\]52;([a-zA-Z0-9]*)(?:;([A-Za-z0-9+/=]*))?(?:\x07|\x1b\\)")


class Osc52Response(BaseModel):
    """A response to an OSC 52 clipboard query."""

    model_config = ConfigDict(frozen=True)

    source: str = ""
    data: Base64Bytes = b""


def _build(payload: bytes, primary: bool) -> bytes:
    loc = b"p" if primary else b"c"
    return OSC + b"52;" + loc + b";" + payload + BEL


def build_copy(data: bytes, *, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which sets the system clipboard."""
    return _build(base64.b64encode(data), primary)


def build_query(*, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which queries the system clipboard."""
    return _build(b"?", primary)


def build_clear(*, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which clears the system clipboard."""
    return _build(b"!", primary)


def parse_response(match: re.Match[bytes]) -> Osc52Response:
    """Parse an OSC 52 clipboard response."""
    raw: dict[str, str | bytes] = {
        "source": match.group(1).decode(),
        "data": match.group(2) or b"",
    }
    try:
        return Osc52Response.model_validate(raw)
    except ValidationError as e:
        raise ClipboardProtocolError(f"invalid OSC 52 response: {e}") from e

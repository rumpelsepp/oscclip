# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Parsing of OSC 52 responses."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, ValidationError

from oscclip.encoding import Base64Bytes
from oscclip.errors import ClipboardProtocolError

#: Matches OSC 52 clipboard responses with either BEL or ST terminator.
RESPONSE_RE = re.compile(rb"\x1b\]52;([a-zA-Z0-9]*)(?:;([A-Za-z0-9+/=]*))?(?:\x07|\x1b\\)")


class Osc52Response(BaseModel):
    """A response to an OSC 52 clipboard query."""

    model_config = ConfigDict(frozen=True)

    source: str = ""
    data: Base64Bytes = b""


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

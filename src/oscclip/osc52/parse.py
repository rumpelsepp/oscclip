# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Parsing of OSC 52 responses."""

from __future__ import annotations

import re
from dataclasses import dataclass

from oscclip import encoding

#: Matches OSC 52 clipboard responses with either BEL or ST terminator.
RESPONSE_RE = re.compile(rb"\x1b\]52;([a-zA-Z0-9]*)(?:;([A-Za-z0-9+/=]*))?(?:\x07|\x1b\\)")


@dataclass(frozen=True)
class Osc52Response:
    """A response to an OSC 52 clipboard query."""

    source: str = ""
    data: bytes = b""


def parse_response(match: re.Match[bytes]) -> Osc52Response:
    """Parse an OSC 52 clipboard response."""
    return Osc52Response(
        source=match.group(1).decode(),
        data=encoding.decode_bytes(match.group(2) or b""),
    )

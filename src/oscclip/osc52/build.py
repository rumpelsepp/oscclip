# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Construction of OSC 52 sequences."""

from __future__ import annotations

import base64

OSC = b"\x1b]"
BEL = b"\x07"


def copy_sequence(data: bytes, *, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which sets the system clipboard."""
    return _build(base64.b64encode(data), primary)


def query_sequence(*, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which queries the system clipboard."""
    return _build(b"?", primary)


def clear_sequence(*, primary: bool = False) -> bytes:
    """Build an OSC 52 sequence which clears the system clipboard."""
    return _build(b"!", primary)


def _build(payload: bytes, primary: bool) -> bytes:
    loc = b"p" if primary else b"c"
    return OSC + b"52;" + loc + b";" + payload + BEL

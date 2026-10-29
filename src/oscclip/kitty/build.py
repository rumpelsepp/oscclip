# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Construction of OSC 5522 sequences."""

from __future__ import annotations

import base64
from collections.abc import Iterator, Sequence

OSC = b"\x1b]"
ST = b"\x1b\\"
CSI = b"\x1b["

#: Data is split into chunks of at most 4096 bytes (before base64 encoding).
CHUNK_SIZE = 4096

#: Special "MIME type" to request the list of available MIME types.
LIST_MIME = "."


def capability_query() -> bytes:
    """Build a DECRQM query for mode 5522."""
    return CSI + b"?5522$p"


def write_sequence(*, primary: bool = False) -> bytes:
    """Build the initial OSC 5522 write packet."""
    return OSC + b"5522;" + _meta(b"type=write", primary) + ST


def wdata_sequence(mime: str, chunk: bytes) -> bytes:
    """Build an OSC 5522 data packet for a single chunk."""
    mime_b64 = base64.b64encode(mime.encode())
    return OSC + b"5522;type=wdata:mime=" + mime_b64 + b";" + base64.b64encode(chunk) + ST


def wdata_end_sequence() -> bytes:
    """Build the end-of-transmission packet."""
    return OSC + b"5522;type=wdata" + ST


def read_sequence(mime_types: Sequence[str], *, primary: bool = False) -> bytes:
    """Build an OSC 5522 read request."""
    payload = base64.b64encode(" ".join(mime_types).encode())
    return OSC + b"5522;" + _meta(b"type=read", primary) + b";" + payload + ST


def chunks(data: bytes, size: int = CHUNK_SIZE) -> Iterator[bytes]:
    """Split data into chunks of at most 4096 bytes."""
    for offset in range(0, len(data), size):
        yield data[offset : offset + size]


def write_sequences(
    data: bytes,
    *,
    mime: str = "text/plain",
    primary: bool = False,
) -> Iterator[bytes]:
    """Yield all sequences of a clipboard write request."""
    yield write_sequence(primary=primary)
    for chunk in chunks(data):
        yield wdata_sequence(mime, chunk)
    yield wdata_end_sequence()


def _meta(kind: bytes, primary: bool) -> bytes:
    meta = kind
    if primary:
        meta += b":loc=primary"
    return meta

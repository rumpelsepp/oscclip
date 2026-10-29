# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Shared helpers for building scripted terminal responses."""

from __future__ import annotations

import base64

from oscclip.sequences import ST

#: DECRPM response indicating kitty clipboard protocol support.
DECRPM_SUPPORTED = b"\x1b[?5522;1$y"


def b64(data: bytes) -> bytes:
    return base64.b64encode(data)


def packet(meta: str, payload: bytes = b"") -> bytes:
    """Build an OSC 5522 packet with an ST terminator."""
    result = b"\x1b]5522;" + meta.encode()
    if payload:
        result += b";" + payload
    return result + ST


def read_ok() -> bytes:
    return packet("type=read:status=OK")


def read_data(mime: str, data: bytes) -> bytes:
    meta = f"type=read:status=DATA:mime={b64(mime.encode()).decode()}"
    return packet(meta, b64(data))


def read_done() -> bytes:
    return packet("type=read:status=DONE")


def write_done() -> bytes:
    return packet("type=write:status=DONE")


def png_bytes(width: int, height: int) -> bytes:
    """Build a minimal PNG header carrying the given pixel size."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"data"
    )

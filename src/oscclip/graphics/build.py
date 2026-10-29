# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Construction of kitty graphics protocol sequences.

Specification: https://sw.kovidgoyal.net/kitty/graphics-protocol/
"""

from __future__ import annotations

import base64
from collections.abc import Iterator

APC = b"\x1b_G"
ST = b"\x1b\\"

#: Chunks of transmitted image data are at most 4096 bytes.
CHUNK_SIZE = 4096

#: Image id used for displaying pasted images.
IMAGE_ID = 31


def support_query() -> bytes:
    """Build a graphics query used to detect protocol support."""
    return APC + b"i=31,s=1,v=1,a=q,t=d,f=24;AAAA" + ST


def device_attributes_query() -> bytes:
    """Build a DA1 request; its response ends the support detection."""
    return b"\x1b[c"


def cell_size_query() -> bytes:
    """Build a CSI 16 t query for the pixel size of a single cell."""
    return b"\x1b[16t"


def window_size_query() -> bytes:
    """Build a CSI 18 t query for the window size in cells."""
    return b"\x1b[18t"


def cursor_down(rows: int) -> bytes:
    """Build a sequence which moves the cursor down by rows lines."""
    return b"\x1b[" + str(rows).encode() + b"B\r"


def display_sequences(
    data: bytes,
    *,
    image_format: int,
    image_id: int = IMAGE_ID,
    columns: int | None = None,
) -> Iterator[bytes]:
    """Yield the sequences which transmit and display an image.

    The image is transmitted and displayed at the current cursor position
    using the transmit action (a=T).
    """
    control = f"a=T,f={image_format},i={image_id}".encode()
    if columns is not None:
        control += f",c={columns}".encode()
    encoded = base64.b64encode(data)
    chunks = [
        encoded[offset : offset + CHUNK_SIZE] for offset in range(0, len(encoded), CHUNK_SIZE)
    ]
    for index, chunk in enumerate(chunks):
        head = control + b",m=" if index == 0 else b"m="
        more = index < len(chunks) - 1
        yield APC + head + (b"1" if more else b"0") + b";" + chunk + ST

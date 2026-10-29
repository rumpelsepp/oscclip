# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Parsing of kitty graphics protocol responses."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from oscclip.errors import ClipboardProtocolError

#: Matches graphics responses, e.g. <ESC>_Gi=31;OK<ESC>\.
RESPONSE_RE = re.compile(rb"\x1b_Gi=(\d+);([\x20-\x7e]*)\x1b\\")

#: Matches DA1 responses, which end the support detection.
DA1_RE = re.compile(rb"\x1b\[\?[\d;]*c")

#: Matches CSI 16 t cell size responses: <ESC>[6;<height>;<width>t
CELL_SIZE_RE = re.compile(rb"\x1b\[6;(\d+);(\d+)t")

#: Matches CSI 18 t window size responses: <ESC>[8;<rows>;<cols>t
WINDOW_SIZE_RE = re.compile(rb"\x1b\[8;(\d+);(\d+)t")


@dataclass(frozen=True)
class GraphicsResponse:
    """A response to a graphics command."""

    image_id: int
    message: str


@dataclass(frozen=True)
class CellSize:
    """The pixel size of a single terminal cell."""

    height: int
    width: int


@dataclass(frozen=True)
class WindowSize:
    """The window size in cells."""

    rows: int
    columns: int


@dataclass(frozen=True)
class Placement:
    """The cell area an image is displayed in."""

    columns: int
    rows: int
    scaled: bool


def parse_response(match: re.Match[bytes]) -> GraphicsResponse:
    """Parse a graphics response."""
    return GraphicsResponse(
        image_id=int(match.group(1)),
        message=match.group(2).decode("ascii", errors="replace"),
    )


def parse_cell_size(match: re.Match[bytes]) -> CellSize:
    """Parse a CSI 16 t cell size response."""
    return CellSize(height=int(match.group(1)), width=int(match.group(2)))


def parse_window_size(match: re.Match[bytes]) -> WindowSize:
    """Parse a CSI 18 t window size response."""
    return WindowSize(rows=int(match.group(1)), columns=int(match.group(2)))


#: Byte offsets of the PNG IHDR chunk (8 byte signature + 4 byte length).
_PNG_HEADER_SIZE = 24
_IHDR_WIDTH_OFFSET = 16
_IHDR_HEIGHT_OFFSET = 20


def png_size(data: bytes) -> tuple[int, int]:
    """Return the pixel size of a PNG image."""
    if len(data) < _PNG_HEADER_SIZE or data[12:16] != b"IHDR":
        raise ClipboardProtocolError("invalid PNG data")
    width = int.from_bytes(data[_IHDR_WIDTH_OFFSET : _IHDR_WIDTH_OFFSET + 4], "big")
    height = int.from_bytes(data[_IHDR_HEIGHT_OFFSET : _IHDR_HEIGHT_OFFSET + 4], "big")
    return width, height


#: JPEG markers which carry no length field (standalone markers).
_JPEG_STANDALONE_MARKERS = frozenset({0x01, *range(0xD0, 0xDA)})

#: Start-of-frame markers; C4 (DHT), C8 (JPG) and CC (DAC) are not SOF.
_JPEG_SOF_MARKERS = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}

#: Minimal JPEG file size (SOI marker plus one segment header).
_JPEG_MIN_SIZE = 4

#: Byte which introduces a JPEG segment marker.
_JPEG_MARKER = 0xFF

#: Minimal SOF payload length (length, precision, height, width, components).
_JPEG_SOF_MIN_LENGTH = 7

#: Minimal SOF segment size: marker (2) + length field (2) + payload.
_JPEG_SOF_MIN_SIZE = 9

#: Size of the RIFF/WebP header.
_WEBP_HEADER_SIZE = 12

#: Minimal chunk payload sizes which carry the image dimensions.
_VP8X_MIN_CHUNK = 10
_VP8_MIN_CHUNK = 10
_VP8L_MIN_CHUNK = 5

#: Signature byte of a VP8L chunk.
_VP8L_SIGNATURE = 0x2F


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Return the pixel size of a JPEG image by scanning for a SOF segment."""
    if len(data) < _JPEG_MIN_SIZE or data[:2] != b"\xff\xd8":
        raise ClipboardProtocolError("invalid JPEG data")
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != _JPEG_MARKER:
            raise ClipboardProtocolError("invalid JPEG segment")
        marker = data[offset + 1]
        if marker in _JPEG_STANDALONE_MARKERS:
            offset += 2
            continue
        length = int.from_bytes(data[offset + 2 : offset + 4], "big")
        if marker in _JPEG_SOF_MARKERS:
            if offset + _JPEG_SOF_MIN_SIZE > len(data) or length < _JPEG_SOF_MIN_LENGTH:
                raise ClipboardProtocolError("invalid JPEG SOF segment")
            height = int.from_bytes(data[offset + 5 : offset + 7], "big")
            width = int.from_bytes(data[offset + 7 : offset + 9], "big")
            return width, height
        offset += 2 + length
    raise ClipboardProtocolError("no SOF segment found in JPEG data")


def webp_size(data: bytes) -> tuple[int, int]:
    """Return the pixel size of a WebP image (VP8X, VP8 or VP8L chunk)."""
    if len(data) < _WEBP_HEADER_SIZE or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ClipboardProtocolError("invalid WebP data")
    offset = _WEBP_HEADER_SIZE
    while offset + 8 <= len(data):
        fourcc = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        chunk = data[offset + 8 : offset + 8 + size]
        if fourcc == b"VP8X" and len(chunk) >= _VP8X_MIN_CHUNK:
            # Canvas size minus one, stored as 24-bit little-endian values.
            width = 1 + int.from_bytes(chunk[4:7], "little")
            height = 1 + int.from_bytes(chunk[7:10], "little")
            return width, height
        if fourcc == b"VP8 " and len(chunk) >= _VP8_MIN_CHUNK:
            # Frame tag (3 bytes) + start code (3 bytes), then 14-bit size fields.
            if chunk[3:6] != b"\x9d\x01\x2a":
                raise ClipboardProtocolError("invalid WebP VP8 chunk")
            width = int.from_bytes(chunk[6:8], "little") & 0x3FFF
            height = int.from_bytes(chunk[8:10], "little") & 0x3FFF
            return width, height
        if fourcc == b"VP8L" and len(chunk) >= _VP8L_MIN_CHUNK:
            if chunk[0] != _VP8L_SIGNATURE:
                raise ClipboardProtocolError("invalid WebP VP8L chunk")
            bits = int.from_bytes(chunk[1:5], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        # Chunks are padded to an even size.
        offset += 8 + size + (size & 1)
    raise ClipboardProtocolError("no image chunk found in WebP data")


def placement_size(
    image: tuple[int, int],
    cell: CellSize,
    window: WindowSize,
) -> Placement:
    """Compute the cell area an image occupies, scaled down to fit the window."""
    image_width, image_height = image
    natural_columns = math.ceil(image_width / cell.width)
    if natural_columns <= window.columns:
        return Placement(
            columns=natural_columns,
            rows=math.ceil(image_height / cell.height),
            scaled=False,
        )
    scale = (window.columns * cell.width) / image_width
    return Placement(
        columns=window.columns,
        rows=math.ceil(image_height * scale / cell.height),
        scaled=True,
    )

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

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The kitty graphics protocol.

The package is layered: build constructs outgoing sequences, parse handles
incoming responses, and transport drives the protocol over a terminal.

Specification: https://sw.kovidgoyal.net/kitty/graphics-protocol/
"""

from oscclip.graphics.parse import (
    RESPONSE_RE,
    CellSize,
    GraphicsResponse,
    Placement,
    WindowSize,
    jpeg_size,
    parse_cell_size,
    parse_response,
    parse_window_size,
    placement_size,
    png_size,
    webp_size,
)
from oscclip.graphics.transport import display, supports

__all__ = [
    "RESPONSE_RE",
    "CellSize",
    "GraphicsResponse",
    "Placement",
    "WindowSize",
    "display",
    "jpeg_size",
    "parse_cell_size",
    "parse_response",
    "parse_window_size",
    "placement_size",
    "png_size",
    "supports",
    "webp_size",
]

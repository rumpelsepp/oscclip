# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The kitty graphics protocol.

The package is layered: build constructs outgoing sequences, parse handles
incoming responses, and transport drives the protocol over a terminal.

Specification: https://sw.kovidgoyal.net/kitty/graphics-protocol/
"""

from oscclip.graphics.parse import CellSize, Placement, WindowSize, placement_size, png_size
from oscclip.graphics.transport import display, supports

__all__ = [
    "CellSize",
    "Placement",
    "WindowSize",
    "display",
    "placement_size",
    "png_size",
    "supports",
]

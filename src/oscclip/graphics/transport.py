# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Terminal I/O for the kitty graphics protocol."""

from __future__ import annotations

import logging

from oscclip.errors import ClipboardError, ClipboardProtocolError, ClipboardTimeoutError
from oscclip.graphics import build, parse
from oscclip.term import Terminal

logger = logging.getLogger(__name__)

#: Supported image formats mapped to the f key of the graphics protocol.
_FORMATS = {
    "image/png": 100,
    "image/jpeg": 32,
    "image/webp": 54,
}


def supports(tty: Terminal, *, timeout: float) -> bool:
    """Query the terminal for kitty graphics protocol support."""
    logger.debug("querying terminal for graphics protocol support")
    tty.write(build.support_query() + build.device_attributes_query())
    match = tty.read_until([parse.RESPONSE_RE, parse.DA1_RE], timeout)
    supported = match is not None and match.re is parse.RESPONSE_RE
    logger.debug("graphics protocol supported: %s", supported)
    return supported


def display(tty: Terminal, data: bytes, *, mime: str, timeout: float) -> None:
    """Transmit an image and display it at the current cursor position."""
    image_format = _FORMATS.get(mime)
    if image_format is None:
        raise ClipboardError(f"cannot display {mime} images in the terminal")
    logger.debug("displaying a %s image (%d bytes)", mime, len(data))

    columns: int | None = None
    rows: int | None = None
    if mime == "image/png":
        cell = _query_cell(tty, timeout)
        window = _query_window(tty, timeout)
        placement = parse.placement_size(parse.png_size(data), cell, window)
        columns = placement.columns if placement.scaled else None
        rows = placement.rows

    for sequence in build.display_sequences(data, image_format=image_format, columns=columns):
        tty.write(sequence)

    response = tty.read_until([parse.RESPONSE_RE], timeout)
    if response is None:
        raise ClipboardTimeoutError("the terminal did not confirm the image display")
    graphics_response = parse.parse_response(response)
    if graphics_response.message != "OK":
        raise ClipboardProtocolError(f"failed to display the image: {graphics_response.message}")
    if rows is not None:
        tty.write(build.cursor_down(rows))
    logger.debug("displayed the image")


def _query_cell(tty: Terminal, timeout: float) -> parse.CellSize:
    """Query the pixel size of a single cell."""
    tty.write(build.cell_size_query())
    match = tty.read_until([parse.CELL_SIZE_RE], timeout)
    if match is None:
        raise ClipboardTimeoutError("the terminal did not report its cell size")
    return parse.parse_cell_size(match)


def _query_window(tty: Terminal, timeout: float) -> parse.WindowSize:
    """Query the window size in cells."""
    tty.write(build.window_size_query())
    match = tty.read_until([parse.WINDOW_SIZE_RE], timeout)
    if match is None:
        raise ClipboardTimeoutError("the terminal did not report its window size")
    return parse.parse_window_size(match)

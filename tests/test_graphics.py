# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tests for the kitty graphics protocol."""

from __future__ import annotations

import base64
from collections.abc import Callable

import pytest

from oscclip import graphics
from oscclip.errors import ClipboardError, ClipboardProtocolError, ClipboardTimeoutError
from oscclip.graphics import build, parse
from oscclip.sequences import ST
from tests.fake_tty import FakeTty
from tests.helpers import png_bytes

#: APC "G" introducer of the kitty graphics protocol.
APC = b"\x1b_G"


def _jpeg(width: int, height: int) -> bytes:
    app0 = b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\x00" + b"\x00" * 9
    sof = (
        b"\xff\xc0"
        + (17).to_bytes(2, "big")
        + b"\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03"
        + b"\x00" * 9
    )
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def _webp(fourcc: bytes, chunk: bytes) -> bytes:
    riff_size = 4 + 8 + len(chunk) + (len(chunk) & 1)
    padding = b"\x00" if len(chunk) & 1 else b""
    return (
        b"RIFF"
        + riff_size.to_bytes(4, "little")
        + b"WEBP"
        + fourcc
        + len(chunk).to_bytes(4, "little")
        + chunk
        + padding
    )


def _webp_vp8x(width: int, height: int) -> bytes:
    chunk = b"\x00" * 4 + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return _webp(b"VP8X", chunk)


def _webp_vp8(width: int, height: int) -> bytes:
    chunk = (
        b"\x00" * 3 + b"\x9d\x01\x2a" + width.to_bytes(2, "little") + height.to_bytes(2, "little")
    )
    return _webp(b"VP8 ", chunk)


def _webp_vp8l(width: int, height: int) -> bytes:
    bits = (width - 1) | ((height - 1) << 14)
    return _webp(b"VP8L", b"\x2f" + bits.to_bytes(4, "little"))


# --- build (pure) ---


def test_display_sequences_single_chunk() -> None:
    sequences = list(build.display_sequences(b"tiny", image_format=100))
    assert sequences == [APC + b"a=T,f=100,i=31,m=0;" + base64.b64encode(b"tiny") + ST]


def test_display_sequences_chunking() -> None:
    data = bytes(5000)  # 6668 base64 characters -> two chunks
    sequences = list(build.display_sequences(data, image_format=100))
    encoded = base64.b64encode(data)
    assert len(sequences) == 2
    assert sequences[0] == APC + b"a=T,f=100,i=31,m=1;" + encoded[:4096] + ST
    assert sequences[1] == APC + b"m=0;" + encoded[4096:] + ST


def test_display_sequences_columns() -> None:
    sequences = list(build.display_sequences(b"x", image_format=100, columns=80))
    assert sequences[0].startswith(APC + b"a=T,f=100,i=31,c=80,m=0;")


def test_cursor_down() -> None:
    assert build.cursor_down(3) == b"\x1b[3B\r"


def test_support_query() -> None:
    assert build.support_query() == APC + b"i=31,s=1,v=1,a=q,t=d,f=24;AAAA" + ST


# --- parse (pure) ---


def test_png_size() -> None:
    assert parse.png_size(png_bytes(1920, 1080)) == (1920, 1080)


def test_png_size_invalid() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.png_size(b"not a png")


def test_jpeg_size() -> None:
    assert parse.jpeg_size(_jpeg(1920, 1080)) == (1920, 1080)


def test_jpeg_size_invalid() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.jpeg_size(b"not a jpeg")


def test_jpeg_size_no_sof() -> None:
    app0 = b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\x00" + b"\x00" * 9
    with pytest.raises(ClipboardProtocolError):
        parse.jpeg_size(b"\xff\xd8" + app0 + b"\xff\xd9")


def test_webp_size_vp8x() -> None:
    assert parse.webp_size(_webp_vp8x(1920, 1080)) == (1920, 1080)


def test_webp_size_vp8() -> None:
    assert parse.webp_size(_webp_vp8(640, 480)) == (640, 480)


def test_webp_size_vp8l() -> None:
    assert parse.webp_size(_webp_vp8l(800, 600)) == (800, 600)


def test_webp_size_invalid() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.webp_size(b"not a webp")


def test_placement_size_fits() -> None:
    cell = parse.CellSize(height=20, width=10)
    window = parse.WindowSize(rows=24, columns=80)
    placement = parse.placement_size((100, 100), cell, window)
    assert placement.columns == 10
    assert placement.rows == 5
    assert placement.scaled is False


def test_placement_size_scales_down() -> None:
    cell = parse.CellSize(height=20, width=10)
    window = parse.WindowSize(rows=24, columns=80)
    placement = parse.placement_size((1920, 1080), cell, window)
    assert placement.columns == 80
    assert placement.rows == 23  # 1080 * (800 / 1920) = 450 px -> 23 rows
    assert placement.scaled is True


def test_parse_response() -> None:
    match = parse.RESPONSE_RE.search(APC + b"i=31;OK" + ST)
    assert match is not None
    response = parse.parse_response(match)
    assert response.image_id == 31
    assert response.message == "OK"


def test_parse_cell_and_window_size() -> None:
    cell_match = parse.CELL_SIZE_RE.search(b"\x1b[6;20;10t")
    window_match = parse.WINDOW_SIZE_RE.search(b"\x1b[8;24;80t")
    assert cell_match is not None
    assert window_match is not None
    assert parse.parse_cell_size(cell_match) == parse.CellSize(height=20, width=10)
    assert parse.parse_window_size(window_match) == parse.WindowSize(rows=24, columns=80)


# --- transport (over a scripted terminal) ---


def test_supports(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(APC + b"i=31;OK" + ST)
    assert graphics.supports(tty, timeout=0.1) is True


def test_supports_da1_only(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(b"\x1b[?62;1;2c")
    assert graphics.supports(tty, timeout=0.1) is False


def test_supports_no_response(make_tty: Callable[..., FakeTty]) -> None:
    assert graphics.supports(make_tty(), timeout=0.1) is False


def test_display(make_tty: Callable[..., FakeTty]) -> None:
    responses = b"\x1b[6;20;10t" + b"\x1b[8;24;80t" + APC + b"i=31;OK" + ST
    tty = make_tty(responses)
    graphics.display(tty, png_bytes(100, 100), mime="image/png", timeout=0.1)
    assert tty.written[0] == b"\x1b[16t"
    assert tty.written[1] == b"\x1b[18t"
    assert tty.written[2].startswith(APC + b"a=T,f=100,i=31,m=0;")
    assert tty.written[-1] == b"\x1b[5B\r"


def test_display_jpeg_moves_cursor(make_tty: Callable[..., FakeTty]) -> None:
    responses = b"\x1b[6;20;10t" + b"\x1b[8;24;80t" + APC + b"i=31;OK" + ST
    tty = make_tty(responses)
    graphics.display(tty, _jpeg(100, 100), mime="image/jpeg", timeout=0.1)
    assert tty.written[0] == b"\x1b[16t"
    assert tty.written[1] == b"\x1b[18t"
    assert tty.written[2].startswith(APC + b"a=T,f=32,i=31,m=0;")
    assert tty.written[-1] == b"\x1b[5B\r"


def test_display_error(make_tty: Callable[..., FakeTty]) -> None:
    responses = b"\x1b[6;20;10t" + b"\x1b[8;24;80t" + APC + b"i=31;EBADF:failed" + ST
    tty = make_tty(responses)
    with pytest.raises(ClipboardProtocolError):
        graphics.display(tty, png_bytes(100, 100), mime="image/png", timeout=0.1)


def test_display_unsupported_mime(make_tty: Callable[..., FakeTty]) -> None:
    with pytest.raises(ClipboardError):
        graphics.display(make_tty(), b"x", mime="image/tiff", timeout=0.1)


def test_display_timeout(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(b"\x1b[6;20;10t" + b"\x1b[8;24;80t")
    with pytest.raises(ClipboardTimeoutError):
        graphics.display(tty, png_bytes(100, 100), mime="image/png", timeout=0.1)

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Conformance tests of oscclip against a real libghostty-vt terminal.

These tests run oscclip's full protocol stack against Ghostty's headless
terminal core: sequences written by the transports are processed by a
real terminal implementation, whose responses and clipboard callbacks
close the loop.  They are skipped when libghostty-vt is not installed.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from collections.abc import Iterator

import pytest

from oscclip import clipboard, kitty, osc52
from oscclip.clipboard import Protocol, Settings
from oscclip.errors import ClipboardDeniedError
from tests.ghostty import LOCATION_PRIMARY, LOCATION_STANDARD, GhosttyTerminalHarness

_LIB_NAME = "ghostty-vt"

#: A payload without NUL bytes; ghostty 1.4.0 handles these fine.
TEXT = b"plain text payload without NUL bytes"

#: A minimal PNG image (32x16 pixels, parsed from the IHDR header).  The
#: data contains NUL bytes.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    + (32).to_bytes(4, "big")
    + (16).to_bytes(4, "big")
    + b"\x08\x06\x00\x00\x00data"
)

#: ghostty 1.4.0 corrupts binary payloads containing NUL bytes in OSC 5522
#: clipboard writes: the data is correct up to the first NUL byte and
#: garbage afterwards.  The strict marker turns into a failure once a
#: fixed ghostty makes the test pass.
GHOSTTY_NUL_BUG = pytest.mark.xfail(
    reason="ghostty 1.4.0 corrupts binary payloads with NUL bytes in OSC 5522 writes",
    strict=True,
)


@pytest.fixture(scope="module")
def libghostty() -> ctypes.CDLL:
    path = ctypes.util.find_library(_LIB_NAME)
    if path is None:
        pytest.skip(f"{_LIB_NAME} is not available on this system")
    return ctypes.CDLL(path)


@pytest.fixture
def ghostty(libghostty: ctypes.CDLL) -> Iterator[GhosttyTerminalHarness]:
    harness = GhosttyTerminalHarness(libghostty)
    yield harness
    harness.close()


# --- kitty clipboard protocol round trips ---


def test_kitty_write_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    kitty.write(ghostty, TEXT, timeout=1.0)
    assert ghostty.clipboard == {"text/plain": TEXT}
    assert ghostty.locations == [LOCATION_STANDARD]


def test_kitty_write_primary_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    kitty.write(ghostty, TEXT, primary=True, timeout=1.0)
    assert ghostty.clipboard == {"text/plain": TEXT}
    assert ghostty.locations == [LOCATION_PRIMARY]


def test_kitty_write_clears_the_clipboard(ghostty: GhosttyTerminalHarness) -> None:
    kitty.write(ghostty, TEXT, timeout=1.0)
    kitty.write(ghostty, b"", timeout=1.0)
    assert ghostty.clipboard == {}


def test_kitty_write_denied(ghostty: GhosttyTerminalHarness) -> None:
    ghostty.deny_writes = True
    with pytest.raises(ClipboardDeniedError):
        kitty.write(ghostty, TEXT, timeout=1.0)


@GHOSTTY_NUL_BUG
def test_kitty_write_binary_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    kitty.write(ghostty, PNG, mime="image/png", timeout=1.0)
    assert ghostty.clipboard == {"image/png": PNG}


def test_kitty_read_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    ghostty.clipboard = {"text/plain": TEXT}
    assert kitty.read(ghostty, ["text/plain"], timeout=1.0) == {"text/plain": TEXT}


def test_kitty_read_binary_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    ghostty.clipboard = {"image/png": PNG}
    assert kitty.read(ghostty, ["image/png"], timeout=1.0) == {"image/png": PNG}


def test_kitty_read_chunked_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    data = bytes(range(65, 91)) * 400  # 10400 bytes -> three DATA packets
    ghostty.clipboard = {"text/plain": data}
    assert kitty.read(ghostty, ["text/plain"], timeout=1.0) == {"text/plain": data}


def test_kitty_read_multiple_mimes_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    ghostty.clipboard = {"text/plain": TEXT, "image/png": PNG}
    result = kitty.read(ghostty, ["text/plain", "image/png"], timeout=1.0)
    assert result == {"text/plain": TEXT, "image/png": PNG}


def test_kitty_list_mime_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    ghostty.clipboard = {"text/plain": TEXT}
    assert kitty.list_mime(ghostty, timeout=1.0) == ["text/plain"]


def test_kitty_supports(ghostty: GhosttyTerminalHarness) -> None:
    assert kitty.supports(ghostty, timeout=1.0) is True


# --- osc52 round trips ---


def test_osc52_write_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    osc52.copy(ghostty, TEXT)
    assert ghostty.clipboard == {"text/plain": TEXT}


def test_osc52_query_round_trip(ghostty: GhosttyTerminalHarness) -> None:
    ghostty.clipboard = {"text/plain": TEXT}
    response = osc52.query(ghostty, primary=False, timeout=1.0)
    assert response.data == TEXT


# --- the full oscclip stack against the real terminal ---


def test_clipboard_copy_and_paste(ghostty: GhosttyTerminalHarness) -> None:
    settings = Settings(protocol=Protocol.KITTY)
    clipboard.copy(ghostty, TEXT, settings)
    content = clipboard.paste(ghostty, settings, mimes=["text/plain"])
    assert content == clipboard.ClipboardContent(mime="text/plain", data=TEXT)

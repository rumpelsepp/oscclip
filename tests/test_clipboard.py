# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tests for the high level clipboard API."""

from __future__ import annotations

import base64
from collections.abc import Callable

import pytest

from oscclip import clipboard
from oscclip.errors import ClipboardError, ClipboardTimeoutError
from tests.fake_tty import FakeTty

DECRPM_SUPPORTED = b"\x1b[?5522;1$y"
ST = b"\x1b\\"


def b64(data: bytes) -> bytes:
    return base64.b64encode(data)


def read_ok() -> bytes:
    return b"\x1b]5522;type=read:status=OK" + ST


def read_data(mime: str, data: bytes) -> bytes:
    meta = f"type=read:status=DATA:mime={b64(mime.encode()).decode()}"
    return b"\x1b]5522;" + meta.encode() + b";" + b64(data) + ST


def read_done() -> bytes:
    return b"\x1b]5522;type=read:status=DONE" + ST


def write_done() -> bytes:
    return b"\x1b]5522;type=write:status=DONE" + ST


def test_copy_kitty_auto(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(DECRPM_SUPPORTED + write_done())
    clipboard.copy(tty, b"data")
    assert tty.written[0] == b"\x1b[?5522$p"
    assert tty.written[1] == b"\x1b]5522;type=write" + ST


def test_copy_osc52_fallback(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    clipboard.copy(tty, b"data")
    assert tty.written == [b"\x1b[?5522$p", b"\x1b]52;c;" + b64(b"data") + b"\x07"]


def test_copy_osc52_explicit(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(DECRPM_SUPPORTED + write_done())
    clipboard.copy(tty, b"data", protocol=clipboard.Protocol.OSC52)
    assert tty.written == [b"\x1b]52;c;" + b64(b"data") + b"\x07"]


def test_copy_kitty_mime(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(DECRPM_SUPPORTED + write_done())
    clipboard.copy(tty, b"\x89PNG", mime="image/png")
    assert any(b"type=wdata:mime=" + b64(b"image/png") + b";" in entry for entry in tty.written)


def test_copy_kitty_explicit_unsupported(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardError):
        clipboard.copy(tty, b"data", protocol=clipboard.Protocol.KITTY)


def test_copy_mime_requires_kitty(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardError):
        clipboard.copy(tty, b"data", mime="image/png")


def test_copy_bypass_wraps_writes(
    make_tty: Callable[..., FakeTty], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("STY", raising=False)
    tty = make_tty()
    clipboard.copy(tty, b"data", bypass=True)
    assert all(entry.startswith(b"\x1bPtmux;") for entry in tty.written)


def test_paste_kitty_auto(make_tty: Callable[..., FakeTty]) -> None:
    responses = DECRPM_SUPPORTED + read_ok() + read_data("text/plain", b"hello") + read_done()
    tty = make_tty(responses)
    content = clipboard.paste(tty)
    assert content.mime == "text/plain"
    assert content.data == b"hello"


def test_paste_kitty_multiple_mimes(make_tty: Callable[..., FakeTty]) -> None:
    responses = (
        DECRPM_SUPPORTED
        + read_ok()
        + read_data("image/png", b"\x89PNG")
        + read_data("text/plain", b"hello")
        + read_done()
    )
    tty = make_tty(responses)
    content = clipboard.paste(tty, mimes=["text/plain", "image/png"])
    assert content.mime == "text/plain"
    assert content.data == b"hello"


def test_paste_kitty_mime_unavailable(make_tty: Callable[..., FakeTty]) -> None:
    responses = DECRPM_SUPPORTED + read_ok() + read_data("text/plain", b"hello") + read_done()
    tty = make_tty(responses)
    with pytest.raises(ClipboardError):
        clipboard.paste(tty, mimes=["image/png"])


def test_paste_osc52_fallback(make_tty: Callable[..., FakeTty]) -> None:
    responses = b"\x1b]52;c;" + b64(b"hello") + b"\x07"
    tty = make_tty(responses)
    content = clipboard.paste(tty)
    assert content.mime == "text/plain"
    assert content.data == b"hello"


def test_paste_osc52_timeout(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardTimeoutError):
        clipboard.paste(tty, timeout=0.1)


def test_paste_mime_requires_kitty(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardError):
        clipboard.paste(tty, mimes=["image/png"])


def test_clear_kitty(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(DECRPM_SUPPORTED + write_done())
    clipboard.clear(tty)
    expected = [
        b"\x1b[?5522$p",
        b"\x1b]5522;type=write" + ST,
        b"\x1b]5522;type=wdata" + ST,
    ]
    assert tty.written == expected


def test_clear_osc52(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    clipboard.clear(tty)
    assert tty.written == [b"\x1b[?5522$p", b"\x1b]52;c;!\x07"]


def test_clear_osc52_explicit(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(DECRPM_SUPPORTED + write_done())
    clipboard.clear(tty, protocol=clipboard.Protocol.OSC52)
    assert tty.written == [b"\x1b]52;c;!\x07"]


def test_list_mime(make_tty: Callable[..., FakeTty]) -> None:
    responses = (
        DECRPM_SUPPORTED + read_ok() + read_data(".", b"text/plain image/png\n") + read_done()
    )
    tty = make_tty(responses)
    assert clipboard.list_mime(tty) == ["text/plain", "image/png"]


def test_list_mime_unsupported(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardError):
        clipboard.list_mime(tty)


def test_list_mime_osc52_explicit(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(DECRPM_SUPPORTED + read_ok() + read_data(".", b"text/plain\n") + read_done())
    with pytest.raises(ClipboardError):
        clipboard.list_mime(tty, protocol=clipboard.Protocol.OSC52)

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""End to end tests for the command line tools."""

from __future__ import annotations

import base64
import io
import sys
from collections.abc import Callable

import pytest

from oscclip import osc_copy, osc_paste
from tests.fake_tty import FakeRawTerminal, FakeTty

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


@pytest.fixture
def fake_term(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeTty]:
    """Factory which patches the CLIs to use a scripted FakeTty."""

    def factory(responses: bytes = b"") -> FakeTty:
        tty = FakeTty(responses)
        monkeypatch.setattr(osc_copy, "RawTerminal", lambda: FakeRawTerminal(tty))
        monkeypatch.setattr(osc_paste, "RawTerminal", lambda: FakeRawTerminal(tty))
        return tty

    return factory


def test_copy_text(fake_term: Callable[..., FakeTty]) -> None:
    tty = fake_term()
    assert osc_copy.main(["hello"]) == 0
    assert b"\x1b]52;c;" + b64(b"hello") + b"\x07" in tty.written


def test_copy_stdin(fake_term: Callable[..., FakeTty], monkeypatch: pytest.MonkeyPatch) -> None:
    tty = fake_term()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"stdin data")))
    assert osc_copy.main([]) == 0
    assert b"\x1b]52;c;" + b64(b"stdin data") + b"\x07" in tty.written


def test_copy_trim(fake_term: Callable[..., FakeTty]) -> None:
    tty = fake_term()
    assert osc_copy.main(["--trim", "  hello  "]) == 0
    assert b"\x1b]52;c;" + b64(b"hello") + b"\x07" in tty.written


def test_copy_primary(fake_term: Callable[..., FakeTty]) -> None:
    tty = fake_term()
    assert osc_copy.main(["-p", "hello"]) == 0
    assert b"\x1b]52;p;" + b64(b"hello") + b"\x07" in tty.written


def test_copy_clear(fake_term: Callable[..., FakeTty]) -> None:
    tty = fake_term()
    assert osc_copy.main(["--clear"]) == 0
    assert b"\x1b]52;c;!\x07" in tty.written


def test_copy_kitty(fake_term: Callable[..., FakeTty]) -> None:
    tty = fake_term(DECRPM_SUPPORTED + write_done())
    assert osc_copy.main(["hello"]) == 0
    assert b"\x1b]5522;type=write" + ST in tty.written


def test_copy_kitty_explicit_unsupported(fake_term: Callable[..., FakeTty]) -> None:
    fake_term()
    with pytest.raises(SystemExit) as excinfo:
        osc_copy.main(["--protocol", "kitty", "hello"])
    assert excinfo.value.code == 1


def test_paste_osc52(
    fake_term: Callable[..., FakeTty], capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    fake_term(b"\x1b]52;c;" + b64(b"hello") + b"\x07")
    assert osc_paste.main([]) == 0
    assert capsysbinary.readouterr().out == b"hello\n"


def test_paste_kitty(
    fake_term: Callable[..., FakeTty], capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    responses = DECRPM_SUPPORTED + read_ok() + read_data("text/plain", b"hello") + read_done()
    fake_term(responses)
    assert osc_paste.main([]) == 0
    assert capsysbinary.readouterr().out == b"hello\n"


def test_paste_trim(
    fake_term: Callable[..., FakeTty], capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    fake_term(b"\x1b]52;c;" + b64(b"hello\n") + b"\x07")
    assert osc_paste.main(["--trim"]) == 0
    assert capsysbinary.readouterr().out == b"hello"


def test_paste_empty(fake_term: Callable[..., FakeTty]) -> None:
    fake_term(b"\x1b]52;c;\x07")
    with pytest.raises(SystemExit) as excinfo:
        osc_paste.main([])
    assert excinfo.value.code == 1


def test_paste_timeout(fake_term: Callable[..., FakeTty]) -> None:
    fake_term()
    with pytest.raises(SystemExit) as excinfo:
        osc_paste.main(["--timeout", "0.1"])
    assert excinfo.value.code == 1


def test_paste_timeout_tmux_hint(
    fake_term: Callable[..., FakeTty],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    fake_term()
    with pytest.raises(SystemExit) as excinfo:
        osc_paste.main(["--timeout", "0.1"])
    assert excinfo.value.code == 1
    assert "get-clipboard" in capsys.readouterr().err


def test_paste_timeout_without_tmux(
    fake_term: Callable[..., FakeTty],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TMUX", raising=False)
    fake_term()
    with pytest.raises(SystemExit) as excinfo:
        osc_paste.main(["--timeout", "0.1"])
    assert excinfo.value.code == 1
    assert "get-clipboard" not in capsys.readouterr().err


def test_paste_list_mime(
    fake_term: Callable[..., FakeTty], capsys: pytest.CaptureFixture[str]
) -> None:
    responses = (
        DECRPM_SUPPORTED + read_ok() + read_data(".", b"text/plain image/png\n") + read_done()
    )
    fake_term(responses)
    assert osc_paste.main(["--list-mime"]) == 0
    assert capsys.readouterr().out == "text/plain\nimage/png\n"


def test_paste_kitty_mime(
    fake_term: Callable[..., FakeTty], capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    responses = DECRPM_SUPPORTED + read_ok() + read_data("image/png", b"\x89PNG") + read_done()
    fake_term(responses)
    assert osc_paste.main(["-m", "image/png"]) == 0
    assert capsysbinary.readouterr().out == b"\x89PNG"


def test_paste_mime_requires_kitty(fake_term: Callable[..., FakeTty]) -> None:
    fake_term(b"\x1b]52;c;" + b64(b"hello") + b"\x07")
    with pytest.raises(SystemExit) as excinfo:
        osc_paste.main(["-m", "image/png"])
    assert excinfo.value.code == 1

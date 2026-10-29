# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tests for terminal multiplexer passthrough support."""

from __future__ import annotations

import sys

import pytest

from oscclip import mux


def test_wrap_without_multiplexer() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    assert mux.wrap_passthrough(data, env={"TERM": "xterm-256color"}) == data


def test_wrap_tmux() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    expected = b"\x1bPtmux;\x1b\x1b]52;c;AAAA\x07\x1b\\"
    assert mux.wrap_passthrough(data, env={"TMUX": "/tmp/sock,1,0"}) == expected


def test_wrap_tmux_doubles_esc() -> None:
    data = b"\x1b]5522;type=write\x1b\\"
    wrapped = mux.wrap_passthrough(data, env={"TMUX": "/tmp/sock,1,0"})
    assert wrapped.count(b"\x1b\x1b") == 2
    assert wrapped.startswith(b"\x1bPtmux;")
    assert wrapped.endswith(b"\x1b\\")


def test_wrap_screen_sty() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    expected = b"\x1bP\x1b]52;c;AAAA\x07\x1b\\"
    assert mux.wrap_passthrough(data, env={"STY": "1", "TERM": "xterm"}) == expected


def test_wrap_screen_term() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    expected = b"\x1bP\x1b]52;c;AAAA\x07\x1b\\"
    assert mux.wrap_passthrough(data, env={"TERM": "screen-256color"}) == expected


def test_wrap_tmux_takes_precedence_over_screen() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    env = {"TMUX": "/tmp/sock,1,0", "TERM": "screen-256color"}
    assert mux.wrap_passthrough(data, env=env).startswith(b"\x1bPtmux;")


def test_is_muxed() -> None:
    assert mux.is_muxed(env={"TERM": "xterm"}) is False
    assert mux.is_muxed(env={"TMUX": "/tmp/sock,1,0"}) is True
    assert mux.is_muxed(env={"STY": "1"}) is True
    assert mux.is_muxed(env={"TERM": "screen"}) is True


def test_tmux_passthrough_enabled_without_tmux() -> None:
    assert mux.tmux_passthrough_enabled(env={"TERM": "xterm"}) is True


def test_tmux_passthrough_enabled_without_tmux_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    monkeypatch.setenv("PATH", "/nonexistent")
    assert mux.tmux_passthrough_enabled() is False


def _fake_tmux(tmp_path: pytest.TempPathFactory, output: str) -> str:
    directory = tmp_path.mktemp("fake-tmux")
    script = directory / "tmux"
    script.write_text(f"#!/bin/sh\nprintf '{output}'\n")
    script.chmod(0o755)
    return str(directory)


def test_tmux_passthrough_enabled_window_option(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    monkeypatch.setenv("PATH", _fake_tmux(tmp_path_factory, "allow-passthrough on\\n"))
    assert mux.tmux_passthrough_enabled() is True


def test_tmux_passthrough_enabled_all(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    monkeypatch.setenv("PATH", _fake_tmux(tmp_path_factory, "allow-passthrough all\\n"))
    assert mux.tmux_passthrough_enabled() is True


def test_tmux_passthrough_disabled(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    monkeypatch.setenv("PATH", _fake_tmux(tmp_path_factory, "allow-passthrough off\\n"))
    assert mux.tmux_passthrough_enabled() is False


def test_warn_tmux_passthrough(
    capsys: pytest.CaptureFixture[str],
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
    monkeypatch.setenv("PATH", _fake_tmux(tmp_path_factory, "allow-passthrough off\\n"))
    mux.warn_tmux_passthrough(sys.stderr)
    captured = capsys.readouterr()
    assert "allow-passthrough" in captured.err

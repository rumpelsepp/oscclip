# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tests for terminal multiplexer passthrough support."""

from __future__ import annotations

from oscclip import mux


def test_wrap_without_multiplexer() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    assert mux.wrap_passthrough(data, env={"TERM": "xterm-256color"}) == data


def test_wrap_tmux() -> None:
    data = b"\x1b]52;c;AAAA\x07"
    expected = b"\x1bPtmux;\x1b\x1b]52;c;AAAA\x07\x1b\\"
    assert mux.wrap_passthrough(data, env={"TMUX": "/tmp/sock,1,0"}) == expected


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


def test_in_tmux() -> None:
    assert mux.in_tmux(env={"TERM": "xterm"}) is False
    assert mux.in_tmux(env={"TMUX": "/tmp/sock,1,0"}) is True

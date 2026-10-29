# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""Terminal multiplexer (tmux and GNU screen) passthrough support."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from typing import TextIO

ESC = b"\x1b"
DCS = b"\x1bP"
TMUX_PASSTHROUGH_PREFIX = b"\x1bPtmux;"
ST = b"\x1b\\"


def in_tmux(env: Mapping[str, str] | None = None) -> bool:
    """Whether the program runs inside tmux."""
    env = os.environ if env is None else env
    return env.get("TMUX") is not None


def _in_screen(env: Mapping[str, str]) -> bool:
    return env.get("STY") is not None or env.get("TERM", "").startswith("screen")


def is_muxed(env: Mapping[str, str] | None = None) -> bool:
    """Whether the program runs inside a terminal multiplexer."""
    env = os.environ if env is None else env
    return in_tmux(env) or _in_screen(env)


def wrap_passthrough(data: bytes, env: Mapping[str, str] | None = None) -> bytes:
    """Wrap escape sequences to bypass a multiplexer, if any.

    Returns data unchanged if no multiplexer is detected.  Within the tmux
    passthrough wrapper, ESC bytes have to be doubled.
    """
    env = os.environ if env is None else env
    if env.get("TMUX") is not None:
        return TMUX_PASSTHROUGH_PREFIX + data.replace(ESC, ESC + ESC) + ST
    if _in_screen(env):
        return DCS + data + ST
    return data


def _show_options(scope: str) -> str:
    """Run tmux show-options for the given scope and return its output."""
    try:
        proc = subprocess.run(
            ["tmux", "show-options", scope],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except OSError, subprocess.SubprocessError:
        return ""
    return proc.stdout.decode(errors="replace")


def tmux_passthrough_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Whether tmux's allow-passthrough option is enabled."""
    env = os.environ if env is None else env
    if not in_tmux(env):
        return True
    # Depending on the tmux version, allow-passthrough is either a server
    # or a window option, so query both scopes.
    options = _show_options("-s") + _show_options("-w")
    if not options:
        return False
    return "allow-passthrough on" in options or "allow-passthrough all" in options


def warn_tmux_passthrough(stream: TextIO, env: Mapping[str, str] | None = None) -> None:
    """Warn if tmux's allow-passthrough option is not enabled."""
    if not tmux_passthrough_enabled(env):
        print("warning: tmux option `allow-passthrough` is not enabled", file=stream)
        print("warning: `--bypass` will not work", file=stream)

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Terminal multiplexer (tmux and GNU screen) passthrough support."""

from __future__ import annotations

import os
from collections.abc import Mapping

from oscclip.sequences import DCS, ESC, ST

TMUX_PASSTHROUGH_PREFIX = b"\x1bPtmux;"


def in_tmux(env: Mapping[str, str] | None = None) -> bool:
    """Whether the program runs inside tmux."""
    env = os.environ if env is None else env
    return env.get("TMUX") is not None


def _in_screen(env: Mapping[str, str]) -> bool:
    return env.get("STY") is not None or env.get("TERM", "").startswith("screen")


def wrap_passthrough(data: bytes, env: Mapping[str, str] | None = None) -> bytes:
    """Wrap escape sequences to bypass a multiplexer, if any.

    Returns data unchanged if no multiplexer is detected.  Within the tmux
    passthrough wrapper, ESC bytes have to be doubled.
    """
    env = os.environ if env is None else env
    if in_tmux(env):
        return TMUX_PASSTHROUGH_PREFIX + data.replace(ESC, ESC + ESC) + ST
    if _in_screen(env):
        return DCS + data + ST
    return data

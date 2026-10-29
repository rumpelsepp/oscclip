# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""High level clipboard operations with automatic protocol selection."""

from __future__ import annotations

import enum
import re
from collections.abc import Sequence
from dataclasses import dataclass

from oscclip import kitty, osc52
from oscclip.errors import ClipboardError, ClipboardTimeoutError
from oscclip.mux import in_tmux, wrap_passthrough
from oscclip.term import Terminal

#: Timeout in seconds for terminal capability queries.
DETECT_TIMEOUT = 0.5

#: Default timeout in seconds for protocol round trips.
DEFAULT_TIMEOUT = 10.0


class Protocol(enum.StrEnum):
    """The clipboard escape sequence protocol to use."""

    AUTO = "auto"
    KITTY = "kitty"
    OSC52 = "osc52"


@dataclass(frozen=True)
class Settings:
    """Settings shared by all clipboard operations."""

    primary: bool = False
    bypass: bool = False
    protocol: Protocol = Protocol.AUTO
    timeout: float = DEFAULT_TIMEOUT


DEFAULT_SETTINGS = Settings()


@dataclass(frozen=True)
class ClipboardContent:
    """Data read from the clipboard together with its MIME type."""

    mime: str
    data: bytes


class _Passthrough:
    """Terminal adapter which wraps writes in multiplexer passthrough sequences."""

    def __init__(self, terminal: Terminal) -> None:
        self._terminal = terminal

    def write(self, data: bytes) -> None:
        self._terminal.write(wrap_passthrough(data))

    def read_until(
        self, patterns: Sequence[re.Pattern[bytes]], timeout: float
    ) -> re.Match[bytes] | None:
        return self._terminal.read_until(patterns, timeout)


def _select(term: Terminal, settings: Settings) -> Terminal:
    return _Passthrough(term) if settings.bypass else term


def _use_kitty(tty: Terminal, settings: Settings) -> bool:
    if settings.protocol is Protocol.OSC52:
        return False
    supported = kitty.supports(tty, timeout=DETECT_TIMEOUT)
    if not supported and settings.protocol is Protocol.KITTY:
        raise ClipboardError("the terminal does not support the kitty clipboard protocol")
    return supported


def _require_plain_text(mimes: Sequence[str]) -> None:
    if any(mime != "text/plain" for mime in mimes):
        raise ClipboardError(
            "MIME types other than text/plain require the kitty clipboard protocol"
        )


def _get_clipboard_hint() -> str:
    """Hint for tmux's get-clipboard option (tmux >= 3.7)."""
    return " (hint: enable tmux's `get-clipboard` option, e.g. `tmux set -s get-clipboard both`)"


def copy(
    term: Terminal,
    data: bytes,
    settings: Settings = DEFAULT_SETTINGS,
    *,
    mime: str = "text/plain",
) -> None:
    """Copy data to the system clipboard."""
    tty = _select(term, settings)
    if _use_kitty(tty, settings):
        kitty.write(tty, data, mime=mime, primary=settings.primary, timeout=settings.timeout)
    else:
        _require_plain_text([mime])
        osc52.copy(tty, data, primary=settings.primary)


def paste(
    term: Terminal,
    settings: Settings = DEFAULT_SETTINGS,
    *,
    mimes: Sequence[str] = ("text/plain",),
) -> ClipboardContent:
    """Read data from the system clipboard."""
    tty = _select(term, settings)
    if _use_kitty(tty, settings):
        available = kitty.read(tty, mimes, primary=settings.primary, timeout=settings.timeout)
        for mime in mimes:
            if mime in available:
                return ClipboardContent(mime=mime, data=available[mime])
        raise ClipboardError("none of the requested MIME types are available on the clipboard")
    _require_plain_text(mimes)
    try:
        response = osc52.query(tty, primary=settings.primary, timeout=settings.timeout)
    except ClipboardTimeoutError as e:
        if in_tmux():
            raise ClipboardTimeoutError(f"{e}{_get_clipboard_hint()}") from e
        raise
    return ClipboardContent(mime="text/plain", data=response.data)


def clear(term: Terminal, settings: Settings = DEFAULT_SETTINGS) -> None:
    """Clear the system clipboard."""
    tty = _select(term, settings)
    if _use_kitty(tty, settings):
        # The kitty protocol has no dedicated clear operation; writing an
        # empty payload clears the clipboard.
        kitty.write(tty, b"", primary=settings.primary, timeout=settings.timeout)
    else:
        osc52.clear(tty, primary=settings.primary)


def list_mime(term: Terminal, settings: Settings = DEFAULT_SETTINGS) -> list[str]:
    """List the MIME types available on the system clipboard."""
    tty = _select(term, settings)
    if settings.protocol is Protocol.OSC52 or not kitty.supports(tty, timeout=DETECT_TIMEOUT):
        raise ClipboardError("listing MIME types requires the kitty clipboard protocol")
    return kitty.list_mime(tty, primary=settings.primary, timeout=settings.timeout)

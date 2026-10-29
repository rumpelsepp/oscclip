# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""High level clipboard operations with automatic protocol selection."""

from __future__ import annotations

import enum
import re
from collections.abc import Sequence
from dataclasses import dataclass

from . import kitty, osc52
from .errors import ClipboardError, ClipboardTimeoutError
from .mux import wrap_passthrough
from .term import Terminal

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


def _select(term: Terminal, bypass: bool) -> Terminal:
    return _Passthrough(term) if bypass else term


def _use_kitty(tty: Terminal, protocol: Protocol) -> bool:
    if protocol is Protocol.OSC52:
        return False
    supported = kitty.supports(tty, timeout=DETECT_TIMEOUT)
    if not supported and protocol is Protocol.KITTY:
        raise ClipboardError("the terminal does not support the kitty clipboard protocol")
    return supported


def _require_plain_text(mimes: Sequence[str]) -> None:
    if any(mime != "text/plain" for mime in mimes):
        raise ClipboardError(
            "MIME types other than text/plain require the kitty clipboard protocol"
        )


def copy(
    term: Terminal,
    data: bytes,
    *,
    mime: str = "text/plain",
    primary: bool = False,
    bypass: bool = False,
    protocol: Protocol = Protocol.AUTO,
    timeout: float = DEFAULT_TIMEOUT,
) -> None:
    """Copy data to the system clipboard."""
    tty = _select(term, bypass)
    if _use_kitty(tty, protocol):
        kitty.write(tty, data, mime=mime, primary=primary, timeout=timeout)
    else:
        _require_plain_text([mime])
        tty.write(osc52.build_copy(data, primary=primary))


def paste(
    term: Terminal,
    *,
    mimes: Sequence[str] = ("text/plain",),
    primary: bool = False,
    bypass: bool = False,
    protocol: Protocol = Protocol.AUTO,
    timeout: float = DEFAULT_TIMEOUT,
) -> ClipboardContent:
    """Read data from the system clipboard."""
    tty = _select(term, bypass)
    if _use_kitty(tty, protocol):
        available = kitty.read(tty, mimes, primary=primary, timeout=timeout)
        for mime in mimes:
            if mime in available:
                return ClipboardContent(mime=mime, data=available[mime])
        raise ClipboardError("none of the requested MIME types are available on the clipboard")
    _require_plain_text(mimes)
    tty.write(osc52.build_query(primary=primary))
    match = tty.read_until([osc52.RESPONSE_RE], timeout)
    if match is None:
        raise ClipboardTimeoutError("the terminal did not respond to the clipboard query")
    response = osc52.parse_response(match)
    return ClipboardContent(mime="text/plain", data=response.data)


def clear(
    term: Terminal,
    *,
    primary: bool = False,
    bypass: bool = False,
    protocol: Protocol = Protocol.AUTO,
    timeout: float = DEFAULT_TIMEOUT,
) -> None:
    """Clear the system clipboard."""
    tty = _select(term, bypass)
    if _use_kitty(tty, protocol):
        # The kitty protocol has no dedicated clear operation; writing an
        # empty payload clears the clipboard.
        kitty.write(tty, b"", primary=primary, timeout=timeout)
    else:
        tty.write(osc52.build_clear(primary=primary))


def list_mime(
    term: Terminal,
    *,
    primary: bool = False,
    bypass: bool = False,
    protocol: Protocol = Protocol.AUTO,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[str]:
    """List the MIME types available on the system clipboard."""
    tty = _select(term, bypass)
    if protocol is Protocol.OSC52 or not kitty.supports(tty, timeout=DETECT_TIMEOUT):
        raise ClipboardError("listing MIME types requires the kitty clipboard protocol")
    return kitty.list_mime(tty, primary=primary, timeout=timeout)

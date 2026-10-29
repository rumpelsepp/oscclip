# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The kitty clipboard protocol (OSC 5522).

Specification: https://sw.kovidgoyal.net/kitty/clipboard/
"""

from __future__ import annotations

from collections.abc import Sequence

from oscclip.errors import ClipboardProtocolError, ClipboardTimeoutError
from oscclip.kitty import build, parse
from oscclip.kitty.parse import PACKET_RE, Packet
from oscclip.term import Terminal

#: Special "MIME type" to request the list of available MIME types.
LIST_MIME = "."

__all__ = [
    "LIST_MIME",
    "PACKET_RE",
    "Packet",
    "list_mime",
    "read",
    "supports",
    "write",
]


def supports(tty: Terminal, *, timeout: float) -> bool:
    """Query the terminal for kitty clipboard protocol support (mode 5522)."""
    tty.write(build.capability_query())
    match = tty.read_until([parse.DECRPM_RE], timeout)
    if match is None:
        return False
    return parse.parse_decrpm(match)


def write(
    tty: Terminal,
    data: bytes,
    *,
    mime: str = "text/plain",
    primary: bool = False,
    timeout: float,
) -> None:
    """Write data to the system clipboard and wait for the terminal's confirmation."""
    tty.write(build.write_sequence(primary=primary))
    for chunk in build.chunks(data):
        tty.write(build.wdata_sequence(mime, chunk))
    tty.write(build.wdata_end_sequence())

    response = tty.read_until([parse.PACKET_RE], timeout)
    if response is None:
        raise ClipboardTimeoutError("the terminal did not confirm the clipboard write request")
    match parse.parse_packet(response):
        case parse.Packet(type="write", status="DONE"):
            return
        case parse.Packet(status=status) if parse.is_error(status):
            parse.raise_for_status(status)
        case packet:
            raise ClipboardProtocolError(
                f"unexpected response to the clipboard write request: {packet}"
            )


def read(
    tty: Terminal,
    mime_types: Sequence[str],
    *,
    primary: bool = False,
    timeout: float,
) -> dict[str, bytes]:
    """Read the given MIME types from the system clipboard."""
    tty.write(build.read_sequence(mime_types, primary=primary))

    result: dict[str, bytes] = {}
    while True:
        response = tty.read_until([parse.PACKET_RE], timeout)
        if response is None:
            raise ClipboardTimeoutError(
                "the terminal did not respond to the clipboard read request"
            )
        packet = parse.parse_packet(response)
        if packet.type != "read":
            raise ClipboardProtocolError(
                f"unexpected packet type in clipboard read response: {packet.type}"
            )
        match packet:
            case parse.Packet(status="DATA", mime=mime, payload=payload):
                result[mime] = result.get(mime, b"") + payload
            case parse.Packet(status="DONE"):
                return result
            case parse.Packet(status=status) if parse.is_error(status):
                parse.raise_for_status(status)
            case parse.Packet(status="OK"):
                pass
            case parse.Packet(status=status):
                raise ClipboardProtocolError(
                    f"unexpected status in clipboard read response: {status}"
                )


def list_mime(tty: Terminal, *, primary: bool = False, timeout: float) -> list[str]:
    """List the MIME types available on the system clipboard."""
    result = read(tty, [LIST_MIME], primary=primary, timeout=timeout)
    return result.get(LIST_MIME, b"").decode(errors="replace").split()

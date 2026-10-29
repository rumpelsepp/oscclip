# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The kitty clipboard protocol (OSC 5522).

Specification: https://sw.kovidgoyal.net/kitty/clipboard/
"""

from __future__ import annotations

import base64
import re
from collections.abc import Iterator, Sequence
from typing import NoReturn

from pydantic import BaseModel, ConfigDict, ValidationError

from oscclip.encoding import Base64Bytes, Base64Str
from oscclip.errors import (
    ClipboardDeniedError,
    ClipboardProtocolError,
    ClipboardTimeoutError,
)
from oscclip.term import Terminal

OSC = b"\x1b]"
ST = b"\x1b\\"
CSI = b"\x1b["

#: Data is split into chunks of at most 4096 bytes (before base64 encoding).
CHUNK_SIZE = 4096

#: Special "MIME type" to request the list of available MIME types.
LIST_MIME = "."

_DECRQM = CSI + b"?5522$p"
#: DECRPM status values: 0 = not recognized, 1 = set, 2 = reset,
#: 3 = permanently set, 4 = permanently reset.
DECRPM_RE = re.compile(rb"\x1b\[\?5522;(\d)\$y")
_SUPPORTED_MODES = frozenset("123")

#: Matches OSC 5522 packets with either BEL or ST terminator.
PACKET_RE = re.compile(rb"\x1b\]5522;([^\x1b\x07;]*)(?:;([A-Za-z0-9+/=]*))?(?:\x07|\x1b\\)")

_ERROR_MESSAGES = {
    "EIO": "an I/O error occurred while processing the clipboard data",
    "EINVAL": "the terminal rejected the clipboard data as invalid",
    "ENOSYS": "the requested clipboard type is not available on this system",
    "EPERM": "permission to access the clipboard was denied",
    "EBUSY": "another program is currently accessing the clipboard",
    "EFBIG": "the clipboard data exceeds the maximum size allowed by the terminal",
}


class Packet(BaseModel):
    """A single OSC 5522 packet."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    type: str = ""
    status: str = ""
    mime: Base64Str = ""
    payload: Base64Bytes = b""


def supports(tty: Terminal, *, timeout: float) -> bool:
    """Query the terminal for kitty clipboard protocol support (mode 5522)."""
    tty.write(_DECRQM)
    match = tty.read_until([DECRPM_RE], timeout)
    if match is None:
        return False
    return match.group(1).decode() in _SUPPORTED_MODES


def write(
    tty: Terminal,
    data: bytes,
    *,
    mime: str = "text/plain",
    primary: bool = False,
    timeout: float,
) -> None:
    """Write data to the system clipboard and wait for the terminal's confirmation."""
    tty.write(OSC + b"5522;" + _meta(b"type=write", primary) + ST)
    mime_b64 = base64.b64encode(mime.encode())
    for chunk in _chunks(data):
        tty.write(OSC + b"5522;type=wdata:mime=" + mime_b64 + b";" + base64.b64encode(chunk) + ST)
    tty.write(OSC + b"5522;type=wdata" + ST)

    response = tty.read_until([PACKET_RE], timeout)
    if response is None:
        raise ClipboardTimeoutError("the terminal did not confirm the clipboard write request")
    match _parse_packet(response):
        case Packet(type="write", status="DONE"):
            return
        case Packet(status=status) if status in _ERROR_MESSAGES:
            _raise_for_status(status)
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
    payload = base64.b64encode(" ".join(mime_types).encode())
    tty.write(OSC + b"5522;" + _meta(b"type=read", primary) + b";" + payload + ST)

    result: dict[str, bytes] = {}
    while True:
        response = tty.read_until([PACKET_RE], timeout)
        if response is None:
            raise ClipboardTimeoutError(
                "the terminal did not respond to the clipboard read request"
            )
        packet = _parse_packet(response)
        if packet.type != "read":
            raise ClipboardProtocolError(
                f"unexpected packet type in clipboard read response: {packet.type}"
            )
        match packet:
            case Packet(status="DATA", mime=mime, payload=payload):
                result[mime] = result.get(mime, b"") + payload
            case Packet(status="DONE"):
                return result
            case Packet(status=status) if status in _ERROR_MESSAGES:
                _raise_for_status(status)
            case Packet(status="OK"):
                pass
            case Packet(status=status):
                raise ClipboardProtocolError(
                    f"unexpected status in clipboard read response: {status}"
                )


def list_mime(tty: Terminal, *, primary: bool = False, timeout: float) -> list[str]:
    """List the MIME types available on the system clipboard."""
    result = read(tty, [LIST_MIME], primary=primary, timeout=timeout)
    return result.get(LIST_MIME, b"").decode(errors="replace").split()


def _meta(kind: bytes, primary: bool) -> bytes:
    meta = kind
    if primary:
        meta += b":loc=primary"
    return meta


def _chunks(data: bytes, size: int = CHUNK_SIZE) -> Iterator[bytes]:
    for offset in range(0, len(data), size):
        yield data[offset : offset + size]


def _parse_packet(match: re.Match[bytes]) -> Packet:
    """Parse an OSC 5522 packet."""
    metadata: dict[str, str | bytes] = {}
    for record in match.group(1).decode("ascii", errors="replace").split(":"):
        key, sep, value = record.partition("=")
        if sep:
            metadata[key] = value
    metadata["payload"] = match.group(2) or b""
    try:
        return Packet.model_validate(metadata)
    except ValidationError as e:
        raise ClipboardProtocolError(f"invalid OSC 5522 packet: {e}") from e


def _raise_for_status(status: str) -> NoReturn:
    if status == "EPERM":
        raise ClipboardDeniedError(_ERROR_MESSAGES[status])
    if status in _ERROR_MESSAGES:
        raise ClipboardProtocolError(_ERROR_MESSAGES[status])
    raise ClipboardProtocolError(f"the terminal reported an unknown clipboard error: {status}")

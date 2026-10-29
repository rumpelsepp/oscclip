# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The kitty clipboard protocol (OSC 5522).

Specification: https://sw.kovidgoyal.net/kitty/clipboard/
"""

from __future__ import annotations

import base64
import binascii
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import NoReturn

from .errors import (
    ClipboardDeniedError,
    ClipboardProtocolError,
    ClipboardTimeoutError,
)
from .term import Terminal

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

_STATUS_OK = "OK"
_STATUS_DATA = "DATA"
_STATUS_DONE = "DONE"

_ERROR_MESSAGES = {
    "EIO": "an I/O error occurred while processing the clipboard data",
    "EINVAL": "the terminal rejected the clipboard data as invalid",
    "ENOSYS": "the requested clipboard type is not available on this system",
    "EPERM": "permission to access the clipboard was denied",
    "EBUSY": "another program is currently accessing the clipboard",
    "EFBIG": "the clipboard data exceeds the maximum size allowed by the terminal",
}

#: Metadata values of these keys are base64 encoded.
_BASE64_KEYS = frozenset({"mime", "name", "pw"})


@dataclass(frozen=True)
class Packet:
    """A single OSC 5522 packet."""

    type: str
    status: str = ""
    mime: str = ""
    payload: bytes = b""


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
    meta = b"type=write"
    if primary:
        meta += b":loc=primary"
    tty.write(OSC + b"5522;" + meta + ST)
    mime_b64 = base64.b64encode(mime.encode())
    for chunk in _chunks(data):
        tty.write(OSC + b"5522;type=wdata:mime=" + mime_b64 + b";" + base64.b64encode(chunk) + ST)
    tty.write(OSC + b"5522;type=wdata" + ST)

    match = tty.read_until([PACKET_RE], timeout)
    if match is None:
        raise ClipboardTimeoutError("the terminal did not confirm the clipboard write request")
    packet = _parse_packet(match)
    if packet.type == "write" and packet.status == _STATUS_DONE:
        return
    if packet.status in _ERROR_MESSAGES:
        _raise_for_status(packet.status)
    raise ClipboardProtocolError(f"unexpected response to the clipboard write request: {packet}")


def read(
    tty: Terminal,
    mime_types: Sequence[str],
    *,
    primary: bool = False,
    timeout: float,
) -> dict[str, bytes]:
    """Read the given MIME types from the system clipboard."""
    meta = b"type=read"
    if primary:
        meta += b":loc=primary"
    payload = base64.b64encode(" ".join(mime_types).encode())
    tty.write(OSC + b"5522;" + meta + b";" + payload + ST)

    result: dict[str, bytes] = {}
    while True:
        match = tty.read_until([PACKET_RE], timeout)
        if match is None:
            raise ClipboardTimeoutError(
                "the terminal did not respond to the clipboard read request"
            )
        packet = _parse_packet(match)
        if packet.type != "read":
            raise ClipboardProtocolError(
                f"unexpected packet type in clipboard read response: {packet.type}"
            )
        if packet.status in _ERROR_MESSAGES:
            _raise_for_status(packet.status)
        if packet.status == _STATUS_DATA:
            result[packet.mime] = result.get(packet.mime, b"") + packet.payload
        elif packet.status == _STATUS_DONE:
            return result
        elif packet.status != _STATUS_OK:
            raise ClipboardProtocolError(
                f"unexpected status in clipboard read response: {packet.status}"
            )


def list_mime(tty: Terminal, *, primary: bool = False, timeout: float) -> list[str]:
    """List the MIME types available on the system clipboard."""
    result = read(tty, [LIST_MIME], primary=primary, timeout=timeout)
    return result.get(LIST_MIME, b"").decode(errors="replace").split()


def _chunks(data: bytes, size: int = CHUNK_SIZE) -> Iterator[bytes]:
    for offset in range(0, len(data), size):
        yield data[offset : offset + size]


def _decode_metadata_value(key: str, value: str) -> str:
    if key not in _BASE64_KEYS:
        return value
    try:
        return base64.b64decode(value.encode(), validate=True).decode("utf-8", errors="replace")
    except binascii.Error as e:
        raise ClipboardProtocolError(f"invalid base64 value in OSC 5522 metadata: {e}") from e


def _parse_packet(match: re.Match[bytes]) -> Packet:
    metadata: dict[str, str] = {}
    for record in match.group(1).decode("ascii", errors="replace").split(":"):
        key, sep, value = record.partition("=")
        if sep:
            metadata[key] = _decode_metadata_value(key, value)
    payload = b""
    if encoded := match.group(2):
        try:
            payload = base64.b64decode(encoded, validate=True)
        except binascii.Error as e:
            raise ClipboardProtocolError(f"invalid base64 payload in OSC 5522 packet: {e}") from e
    return Packet(
        type=metadata.get("type", ""),
        status=metadata.get("status", ""),
        mime=metadata.get("mime", ""),
        payload=payload,
    )


def _raise_for_status(status: str) -> NoReturn:
    if status == "EPERM":
        raise ClipboardDeniedError(_ERROR_MESSAGES[status])
    if status in _ERROR_MESSAGES:
        raise ClipboardProtocolError(_ERROR_MESSAGES[status])
    raise ClipboardProtocolError(f"the terminal reported an unknown clipboard error: {status}")

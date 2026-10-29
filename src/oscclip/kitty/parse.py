# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Parsing of OSC 5522 responses."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import NoReturn

from oscclip import encoding
from oscclip.errors import ClipboardDeniedError, ClipboardProtocolError

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

#: Metadata keys whose values are base64 encoded.
_BASE64_KEYS = frozenset({"mime", "name", "pw"})


@dataclass(frozen=True)
class Packet:
    """A single OSC 5522 packet."""

    type: str = ""
    status: str = ""
    mime: str = ""
    payload: bytes = b""


def parse_decrpm(match: re.Match[bytes]) -> bool:
    """Whether a DECRPM response indicates kitty clipboard protocol support."""
    return match.group(1).decode() in _SUPPORTED_MODES


def parse_packet(match: re.Match[bytes]) -> Packet:
    """Parse an OSC 5522 packet."""
    metadata: dict[str, str] = {}
    for record in match.group(1).decode("ascii", errors="replace").split(":"):
        key, sep, value = record.partition("=")
        if sep:
            metadata[key] = encoding.decode_str(value) if key in _BASE64_KEYS else value
    return Packet(
        type=metadata.get("type", ""),
        status=metadata.get("status", ""),
        mime=metadata.get("mime", ""),
        payload=encoding.decode_bytes(match.group(2) or b""),
    )


def is_error(status: str) -> bool:
    """Whether a packet status is an error status."""
    return status in _ERROR_MESSAGES


def check_write_response(packet: Packet) -> None:
    """Validate the terminal's response to a write request."""
    match packet:
        case Packet(type="write", status="DONE"):
            return
        case Packet(status=status) if is_error(status):
            raise_for_status(status)
        case _:
            raise ClipboardProtocolError(
                f"unexpected response to the clipboard write request: {packet}"
            )


def read_packets(packets: Iterable[Packet]) -> dict[str, bytes]:
    """Fold the packets of a read response into a result."""
    result: dict[str, bytes] = {}
    for packet in packets:
        if packet.type != "read":
            raise ClipboardProtocolError(
                f"unexpected packet type in clipboard read response: {packet.type}"
            )
        match packet:
            case Packet(status="DATA", mime=mime, payload=payload):
                result[mime] = result.get(mime, b"") + payload
            case Packet(status="DONE"):
                return result
            case Packet(status=status) if is_error(status):
                raise_for_status(status)
            case Packet(status="OK"):
                pass
            case Packet(status=status):
                raise ClipboardProtocolError(
                    f"unexpected status in clipboard read response: {status}"
                )
    raise ClipboardProtocolError("incomplete clipboard read response")


def raise_for_status(status: str) -> NoReturn:
    """Raise the domain error for a terminal error status."""
    if status == "EPERM":
        raise ClipboardDeniedError(_ERROR_MESSAGES[status])
    if status in _ERROR_MESSAGES:
        raise ClipboardProtocolError(_ERROR_MESSAGES[status])
    raise ClipboardProtocolError(f"the terminal reported an unknown clipboard error: {status}")

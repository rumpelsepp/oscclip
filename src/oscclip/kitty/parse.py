# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Parsing of OSC 5522 responses."""

from __future__ import annotations

import re
from typing import NoReturn

from pydantic import BaseModel, ConfigDict, ValidationError

from oscclip.encoding import Base64Bytes, Base64Str
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


class Packet(BaseModel):
    """A single OSC 5522 packet."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    type: str = ""
    status: str = ""
    mime: Base64Str = ""
    payload: Base64Bytes = b""


def parse_decrpm(match: re.Match[bytes]) -> bool:
    """Whether a DECRPM response indicates kitty clipboard protocol support."""
    return match.group(1).decode() in _SUPPORTED_MODES


def parse_packet(match: re.Match[bytes]) -> Packet:
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


def is_error(status: str) -> bool:
    """Whether a packet status is an error status."""
    return status in _ERROR_MESSAGES


def raise_for_status(status: str) -> NoReturn:
    """Raise the domain error for a terminal error status."""
    if status == "EPERM":
        raise ClipboardDeniedError(_ERROR_MESSAGES[status])
    if status in _ERROR_MESSAGES:
        raise ClipboardProtocolError(_ERROR_MESSAGES[status])
    raise ClipboardProtocolError(f"the terminal reported an unknown clipboard error: {status}")

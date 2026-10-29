# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Terminal I/O for the kitty clipboard protocol."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence

from oscclip.errors import ClipboardTimeoutError
from oscclip.kitty import build, parse
from oscclip.kitty.parse import Packet
from oscclip.term import Terminal

logger = logging.getLogger(__name__)


def supports(tty: Terminal, *, timeout: float) -> bool:
    """Query the terminal for kitty clipboard protocol support (mode 5522)."""
    logger.debug("querying terminal for kitty clipboard protocol support")
    tty.write(build.capability_query())
    match = tty.read_until([parse.DECRPM_RE], timeout)
    if match is None:
        logger.debug("terminal did not answer the capability query")
        return False
    supported = parse.parse_decrpm(match)
    logger.debug("kitty clipboard protocol supported: %s", supported)
    return supported


def write(
    tty: Terminal,
    data: bytes,
    *,
    mime: str = "text/plain",
    primary: bool = False,
    timeout: float,
) -> None:
    """Write data to the system clipboard and wait for the terminal's confirmation."""
    sequences = list(build.write_sequences(data, mime=mime, primary=primary))
    logger.debug("sending %d OSC 5522 sequences (%d bytes of data)", len(sequences), len(data))
    for sequence in sequences:
        tty.write(sequence)
    response = tty.read_until([parse.PACKET_RE], timeout)
    if response is None:
        raise ClipboardTimeoutError("the terminal did not confirm the clipboard write request")
    logger.debug("received write response")
    parse.check_write_response(parse.parse_packet(response))


def read(
    tty: Terminal,
    mime_types: Sequence[str],
    *,
    primary: bool = False,
    timeout: float,
) -> dict[str, bytes]:
    """Read the given MIME types from the system clipboard."""
    logger.debug("reading MIME types from the clipboard: %s", ", ".join(mime_types))
    tty.write(build.read_sequence(mime_types, primary=primary))
    return parse.read_packets(_packets(tty, timeout))


def list_mime(tty: Terminal, *, primary: bool = False, timeout: float) -> list[str]:
    """List the MIME types available on the system clipboard."""
    logger.debug("listing the MIME types available on the clipboard")
    result = read(tty, [build.LIST_MIME], primary=primary, timeout=timeout)
    return result.get(build.LIST_MIME, b"").decode(errors="replace").split()


def _packets(tty: Terminal, timeout: float) -> Iterator[Packet]:
    """Iterate packets as they arrive on the terminal."""
    while True:
        response = tty.read_until([parse.PACKET_RE], timeout)
        if response is None:
            raise ClipboardTimeoutError(
                "the terminal did not respond to the clipboard read request"
            )
        packet = parse.parse_packet(response)
        logger.debug(
            "received packet type=%s status=%s mime=%s payload=%d bytes",
            packet.type,
            packet.status,
            packet.mime,
            len(packet.payload),
        )
        yield packet

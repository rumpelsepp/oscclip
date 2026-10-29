# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The kitty clipboard protocol (OSC 5522).

The package is layered: build constructs outgoing sequences, parse handles
incoming responses, and transport drives the protocol over a terminal.

Specification: https://sw.kovidgoyal.net/kitty/clipboard/
"""

from oscclip.kitty.build import LIST_MIME
from oscclip.kitty.parse import PACKET_RE, Packet, parse_packet
from oscclip.kitty.transport import list_mime, read, supports, write

__all__ = [
    "LIST_MIME",
    "PACKET_RE",
    "Packet",
    "list_mime",
    "parse_packet",
    "read",
    "supports",
    "write",
]

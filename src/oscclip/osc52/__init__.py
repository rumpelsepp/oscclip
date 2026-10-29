# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""The OSC 52 clipboard escape sequence protocol.

The package is layered: build constructs outgoing sequences, parse handles
incoming responses, and transport drives the protocol over a terminal.
"""

from oscclip.osc52.build import clear_sequence, copy_sequence, query_sequence
from oscclip.osc52.parse import RESPONSE_RE, Osc52Response, parse_response
from oscclip.osc52.transport import clear, copy, query

__all__ = [
    "RESPONSE_RE",
    "Osc52Response",
    "clear",
    "clear_sequence",
    "copy",
    "copy_sequence",
    "parse_response",
    "query",
    "query_sequence",
]

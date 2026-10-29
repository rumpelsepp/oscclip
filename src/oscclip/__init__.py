# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Utilities to access the system clipboard via terminal escape sequences."""

import logging

from oscclip.clipboard import ClipboardContent, Protocol, Settings, clear, copy, list_mime, paste
from oscclip.errors import (
    ClipboardDeniedError,
    ClipboardError,
    ClipboardProtocolError,
    ClipboardTimeoutError,
)

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "ClipboardContent",
    "ClipboardDeniedError",
    "ClipboardError",
    "ClipboardProtocolError",
    "ClipboardTimeoutError",
    "Protocol",
    "Settings",
    "clear",
    "copy",
    "list_mime",
    "paste",
]

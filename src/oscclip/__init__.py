# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Utilities to access the system clipboard via terminal escape sequences."""

from .clipboard import ClipboardContent, Protocol, Settings, clear, copy, list_mime, paste
from .errors import (
    ClipboardDeniedError,
    ClipboardError,
    ClipboardProtocolError,
    ClipboardTimeoutError,
)

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

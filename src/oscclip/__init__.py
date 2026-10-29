# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""Utilities to access the system clipboard via terminal escape sequences."""

from .errors import (
    ClipboardDeniedError,
    ClipboardError,
    ClipboardProtocolError,
    ClipboardTimeoutError,
)

__all__ = [
    "ClipboardDeniedError",
    "ClipboardError",
    "ClipboardProtocolError",
    "ClipboardTimeoutError",
]

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

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

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Strict base64 (RFC 4648) handling for clipboard escape sequences."""

from __future__ import annotations

import base64

from oscclip.errors import ClipboardProtocolError


def decode_bytes(value: str | bytes) -> bytes:
    """Decode a base64 encoded value into bytes."""
    try:
        return base64.b64decode(value, validate=True)
    # binascii.Error (invalid base64) and ValueError (non-ASCII str input)
    # are both subclasses of ValueError.
    except ValueError as e:
        raise ClipboardProtocolError(f"invalid base64 data: {e}") from e


def decode_str(value: str | bytes) -> str:
    """Decode a base64 encoded value into an UTF-8 string."""
    return decode_bytes(value).decode("utf-8", errors="replace")

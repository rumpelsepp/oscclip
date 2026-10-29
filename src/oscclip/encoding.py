# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Strict base64 (RFC 4648) handling for clipboard escape sequences."""

from __future__ import annotations

import base64
import binascii
from typing import Annotated

from pydantic import BeforeValidator

from oscclip.errors import ClipboardProtocolError


def _decode_bytes(value: object) -> object:
    """Decode a base64 encoded value into bytes."""
    if isinstance(value, str | bytes):
        try:
            return base64.b64decode(value, validate=True)
        except binascii.Error as e:
            raise ClipboardProtocolError(f"invalid base64 data: {e}") from e
    return value


def _decode_str(value: object) -> object:
    """Decode a base64 encoded value into an UTF-8 string."""
    if isinstance(value, str | bytes):
        try:
            decoded = base64.b64decode(value, validate=True)
        except binascii.Error as e:
            raise ClipboardProtocolError(f"invalid base64 data: {e}") from e
        return decoded.decode("utf-8", errors="replace")
    return value


#: A base64 encoded field which is decoded into bytes.
Base64Bytes = Annotated[bytes, BeforeValidator(_decode_bytes)]

#: A base64 encoded field which is decoded into an UTF-8 string.
Base64Str = Annotated[str, BeforeValidator(_decode_str)]

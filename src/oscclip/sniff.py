# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""MIME type sniffing for clipboard data."""

from __future__ import annotations

#: The MIME type used when the data type cannot be detected.
TEXT_PLAIN = "text/plain"

#: Magic bytes mapped to their MIME type.
_MAGIC_NUMBERS: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"%PDF-", "application/pdf"),
)


#: Minimal length of RIFF/WebP data: 4 bytes "RIFF", 4 bytes size, 4 bytes "WEBP".
_WEBP_HEADER_SIZE = 12


def sniff_mime(data: bytes) -> str:
    """Guess the MIME type of data from its magic bytes.

    Falls back to text/plain for unknown data.
    """
    for magic, mime in _MAGIC_NUMBERS:
        if data.startswith(magic):
            return mime
    if len(data) >= _WEBP_HEADER_SIZE and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return TEXT_PLAIN

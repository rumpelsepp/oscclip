# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tests for MIME type sniffing."""

from __future__ import annotations

import pytest

from oscclip import sniff


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRdata", "image/png"),
        (b"\xff\xd8\xff\xe0jpeg", "image/jpeg"),
        (b"GIF89aanimation", "image/gif"),
        (b"II*\x00\x00\x00\x00tiff", "image/tiff"),
        (b"MM\x00*\x00tiff", "image/tiff"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 data", "image/webp"),
        (b"%PDF-1.7 document", "application/pdf"),
        (b"hello world", "text/plain"),
        (b"", "text/plain"),
        (b"BM\x00\x00bmp", "text/plain"),  # BMP is not sniffed; too ambiguous
    ],
)
def test_sniff_mime(data: bytes, expected: str) -> None:
    assert sniff.sniff_mime(data) == expected

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""Tests for the OSC 52 protocol."""

from __future__ import annotations

import base64
import re

import pytest

from oscclip import osc52
from oscclip.errors import ClipboardProtocolError


def test_build_copy() -> None:
    assert osc52.build_copy(b"hello") == b"\x1b]52;c;" + base64.b64encode(b"hello") + b"\x07"


def test_build_copy_primary() -> None:
    assert osc52.build_copy(b"x", primary=True) == b"\x1b]52;p;" + base64.b64encode(b"x") + b"\x07"


def test_build_query() -> None:
    assert osc52.build_query() == b"\x1b]52;c;?\x07"


def test_build_query_primary() -> None:
    assert osc52.build_query(primary=True) == b"\x1b]52;p;?\x07"


def test_build_clear() -> None:
    assert osc52.build_clear() == b"\x1b]52;c;!\x07"


def test_build_clear_primary() -> None:
    assert osc52.build_clear(primary=True) == b"\x1b]52;p;!\x07"


def _match(response: bytes) -> re.Match[bytes]:
    match = osc52.RESPONSE_RE.search(response)
    assert match is not None
    return match


def test_parse_response_bel() -> None:
    response = b"\x1b]52;c;" + base64.b64encode(b"hello") + b"\x07"
    result = osc52.parse_response(_match(response))
    assert result.source == "c"
    assert result.data == b"hello"


def test_parse_response_st() -> None:
    response = b"\x1b]52;c;" + base64.b64encode(b"hello") + b"\x1b\\"
    result = osc52.parse_response(_match(response))
    assert result.source == "c"
    assert result.data == b"hello"


def test_parse_response_primary() -> None:
    response = b"\x1b]52;p;" + base64.b64encode(b"hello") + b"\x07"
    result = osc52.parse_response(_match(response))
    assert result.source == "p"


def test_parse_response_empty_source() -> None:
    response = b"\x1b]52;;" + base64.b64encode(b"hello") + b"\x07"
    result = osc52.parse_response(_match(response))
    assert result.source == ""
    assert result.data == b"hello"


def test_parse_response_empty_data() -> None:
    result = osc52.parse_response(_match(b"\x1b]52;c;\x1b\\"))
    assert result.data == b""


def test_parse_response_invalid_base64() -> None:
    with pytest.raises(ClipboardProtocolError):
        osc52.parse_response(_match(b"\x1b]52;c;QQ\x07"))

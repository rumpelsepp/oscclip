# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Tests for the kitty clipboard protocol (OSC 5522)."""

from __future__ import annotations

import base64
from collections.abc import Callable

import pytest

from oscclip import kitty
from oscclip.errors import (
    ClipboardDeniedError,
    ClipboardProtocolError,
    ClipboardTimeoutError,
)
from oscclip.kitty import build, parse
from oscclip.kitty.parse import Packet
from oscclip.sequences import ST
from tests.fake_tty import FakeTty
from tests.helpers import b64, packet, read_data, read_done, read_ok, write_done


@pytest.mark.parametrize(("status", "expected"), [("1", True), ("2", True), ("3", True)])
def test_supports(make_tty: Callable[..., FakeTty], status: str, expected: bool) -> None:
    tty = make_tty(f"\x1b[?5522;{status}$y".encode())
    assert kitty.supports(tty, timeout=0.1) is expected


@pytest.mark.parametrize("status", ["0", "4"])
def test_supports_unsupported(make_tty: Callable[..., FakeTty], status: str) -> None:
    tty = make_tty(f"\x1b[?5522;{status}$y".encode())
    assert kitty.supports(tty, timeout=0.1) is False


def test_supports_no_response(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    assert kitty.supports(tty, timeout=0.1) is False
    assert tty.written == [b"\x1b[?5522$p"]


def test_write_primary(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(write_done())
    kitty.write(tty, b"x", primary=True, timeout=0.1)
    assert tty.written[0] == b"\x1b]5522;type=write:loc=primary" + ST


def test_write_chunking(make_tty: Callable[..., FakeTty]) -> None:
    data = bytes(range(256)) * 20  # 5120 bytes -> 6828 base64 characters
    tty = make_tty(write_done())
    kitty.write(tty, data, timeout=0.1)
    wdata = tty.written[1:-1]
    assert len(wdata) == 2
    chunks = []
    for entry in wdata:
        match = kitty.PACKET_RE.search(entry)
        assert match is not None
        assert match.group(2) is not None
        chunks.append(match.group(2))
    assert [len(chunk) for chunk in chunks] == [4096, 2732]
    assert base64.b64decode(b"".join(chunks)) == data


def test_write_empty_data(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(write_done())
    kitty.write(tty, b"", timeout=0.1)
    assert tty.written == [b"\x1b]5522;type=write" + ST, b"\x1b]5522;type=wdata" + ST]


def test_write_permission_denied(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(packet("type=write:status=EPERM"))
    with pytest.raises(ClipboardDeniedError):
        kitty.write(tty, b"x", timeout=0.1)


@pytest.mark.parametrize("status", ["EIO", "EINVAL", "ENOSYS", "EBUSY", "EFBIG"])
def test_write_errors(make_tty: Callable[..., FakeTty], status: str) -> None:
    tty = make_tty(packet(f"type=write:status={status}"))
    with pytest.raises(ClipboardProtocolError):
        kitty.write(tty, b"x", timeout=0.1)


def test_write_timeout(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardTimeoutError):
        kitty.write(tty, b"x", timeout=0.1)


def test_read(make_tty: Callable[..., FakeTty]) -> None:
    responses = read_ok() + read_data("text/plain", b"hello") + read_done()
    tty = make_tty(responses)
    assert kitty.read(tty, ["text/plain"], timeout=0.1) == {"text/plain": b"hello"}


def test_read_permission_denied(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty(packet("type=read:status=EPERM"))
    with pytest.raises(ClipboardDeniedError):
        kitty.read(tty, ["text/plain"], timeout=0.1)


def test_read_timeout(make_tty: Callable[..., FakeTty]) -> None:
    tty = make_tty()
    with pytest.raises(ClipboardTimeoutError):
        kitty.read(tty, ["text/plain"], timeout=0.1)


def test_read_invalid_base64_payload(make_tty: Callable[..., FakeTty]) -> None:
    meta = f"type=read:status=DATA:mime={b64(b'text/plain').decode()}"
    responses = read_ok() + packet(meta, b"QQ") + read_done()
    tty = make_tty(responses)
    with pytest.raises(ClipboardProtocolError):
        kitty.read(tty, ["text/plain"], timeout=0.1)


def test_read_invalid_base64_metadata(make_tty: Callable[..., FakeTty]) -> None:
    responses = read_ok() + packet("type=read:status=DATA:mime=QQ", b64(b"hello")) + read_done()
    tty = make_tty(responses)
    with pytest.raises(ClipboardProtocolError):
        kitty.read(tty, ["text/plain"], timeout=0.1)


def test_parse_packet_non_ascii_base64_metadata() -> None:
    # Found by the atheris fuzzer: a non-ASCII byte in a base64 metadata
    # value made b64decode raise ValueError instead of a domain error.
    data = b"\x1b]5522;type=read:status=DATA:mime=dGV4d\xc28=\x1b\\"
    match = kitty.PACKET_RE.search(data)
    assert match is not None
    with pytest.raises(ClipboardProtocolError):
        parse.parse_packet(match)


def test_list_mime(make_tty: Callable[..., FakeTty]) -> None:
    responses = read_ok() + read_data(".", b"text/plain image/png\n") + read_done()
    tty = make_tty(responses)
    assert kitty.list_mime(tty, timeout=0.1) == ["text/plain", "image/png"]


# --- pure protocol logic (no terminal involved) ---


def test_write_sequences() -> None:
    sequences = list(build.write_sequences(b"hello"))
    assert sequences == [
        b"\x1b]5522;type=write" + ST,
        b"\x1b]5522;type=wdata:mime=" + b64(b"text/plain") + b";" + b64(b"hello") + ST,
        b"\x1b]5522;type=wdata" + ST,
    ]


def test_write_sequences_primary() -> None:
    sequences = list(build.write_sequences(b"x", primary=True))
    assert sequences[0] == b"\x1b]5522;type=write:loc=primary" + ST


def test_write_sequences_chunking() -> None:
    data = bytes(10000)  # 13336 base64 characters -> 4 chunks
    sequences = list(build.write_sequences(data))
    encoded = base64.b64encode(data)
    wdata = sequences[1:-1]
    assert len(wdata) == 4
    chunks = []
    for entry in wdata:
        match = kitty.PACKET_RE.search(entry)
        assert match is not None
        assert match.group(2) is not None
        chunks.append(match.group(2))
    assert b"".join(chunks) == encoded
    assert [len(chunk) for chunk in chunks] == [4096, 4096, 4096, 1048]


def _packet(
    type_: str,
    status: str = "",
    mime: str = "",
    payload: bytes = b"",
) -> Packet:
    return Packet(type=type_, status=status, mime=mime, payload=payload)


def test_check_write_response_done() -> None:
    parse.check_write_response(_packet("write", status="DONE"))


def test_check_write_response_eperm() -> None:
    with pytest.raises(ClipboardDeniedError):
        parse.check_write_response(_packet("write", status="EPERM"))


def test_check_write_response_unexpected() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.check_write_response(_packet("read", status="DONE"))


def test_read_packets() -> None:
    packets = [
        _packet("read", status="OK"),
        _packet("read", status="DATA", mime="text/plain", payload=b"hello"),
        _packet("read", status="DONE"),
    ]
    assert parse.read_packets(packets) == {"text/plain": b"hello"}


def test_read_packets_accumulates_chunks() -> None:
    packets = [
        _packet("read", status="DATA", mime="text/plain", payload=b"hel"),
        _packet("read", status="DATA", mime="text/plain", payload=b"lo"),
        _packet("read", status="DONE"),
    ]
    assert parse.read_packets(packets) == {"text/plain": b"hello"}


def test_read_packets_multiple_mime_types() -> None:
    packets = [
        _packet("read", status="DATA", mime="text/plain", payload=b"hello"),
        _packet("read", status="DATA", mime="image/png", payload=b"\x89PNG"),
        _packet("read", status="DONE"),
    ]
    result = parse.read_packets(packets)
    assert result == {"text/plain": b"hello", "image/png": b"\x89PNG"}


def test_read_packets_error() -> None:
    with pytest.raises(ClipboardDeniedError):
        parse.read_packets([_packet("read", status="EPERM")])


def test_read_packets_unexpected_status() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.read_packets([_packet("read", status="WEIRD")])


def test_read_packets_wrong_packet_type() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.read_packets([_packet("write", status="DONE")])


def test_read_packets_incomplete() -> None:
    with pytest.raises(ClipboardProtocolError):
        parse.read_packets([_packet("read", status="OK")])

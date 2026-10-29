# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Property-based tests (hypothesis) for the parsers and builders.

Run with the extended profile via `just fuzz` (HYPOTHESIS_PROFILE=fuzz).
For coverage-guided fuzzing with a corpus and crash artifacts, see
fuzz/fuzz_parsers.py (`just fuzz-native`).
"""

from __future__ import annotations

import base64
import contextlib
import os
from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from oscclip import encoding, graphics, kitty, mux, osc52, sniff
from oscclip.errors import ClipboardError
from oscclip.sequences import ST
from tests.fake_tty import FakeTty
from tests.helpers import png_bytes, read_data, read_done, read_ok

settings.register_profile("fuzz", max_examples=2000, deadline=timedelta(seconds=2))
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE") or "default")

#: ASCII text, e.g. as a MIME type (always UTF-8 encodable).
_TEXT = st.text(alphabet=st.characters(codec="ascii"), min_size=1)


# --- round trips: build -> parse yields the original data ---


@given(st.binary())
def test_osc52_copy_sequence_round_trip(data: bytes) -> None:
    match = osc52.RESPONSE_RE.search(osc52.copy_sequence(data))
    assert match is not None
    assert osc52.parse_response(match).data == data


@given(st.binary())
def test_osc52_query_round_trip(data: bytes) -> None:
    tty = FakeTty(b"\x1b]52;c;" + base64.b64encode(data) + b"\x07")
    assert osc52.query(tty, primary=False, timeout=1.0).data == data


@given(st.binary(), _TEXT)
def test_kitty_write_sequences_round_trip(data: bytes, mime: str) -> None:
    sequences = list(kitty.build.write_sequences(data, mime=mime))
    chunks = b""
    for seq in sequences[1:-1]:
        match = kitty.PACKET_RE.search(seq)
        assert match is not None
        assert kitty.parse_packet(match).mime == mime
        assert match.group(2) is not None
        chunks += match.group(2)
    assert chunks == base64.b64encode(data)


@given(st.binary(), _TEXT)
def test_kitty_read_round_trip(data: bytes, mime: str) -> None:
    tty = FakeTty(read_ok() + read_data(mime, data) + read_done())
    assert kitty.read(tty, [mime], timeout=1.0) == {mime: data}


@given(st.binary(min_size=1), _TEXT)
def test_kitty_read_multi_packet_round_trip(data: bytes, mime: str) -> None:
    half = len(data) // 2
    responses = (
        read_ok() + read_data(mime, data[:half]) + read_data(mime, data[half:]) + read_done()
    )
    tty = FakeTty(responses)
    assert kitty.read(tty, [mime], timeout=1.0) == {mime: data}


@given(st.binary())
def test_base64_round_trip(data: bytes) -> None:
    assert encoding.decode_bytes(base64.b64encode(data)) == data


@given(st.integers(min_value=1, max_value=2**31 - 1), st.integers(min_value=1, max_value=2**31 - 1))
def test_png_size_round_trip(width: int, height: int) -> None:
    assert graphics.png_size(png_bytes(width, height)) == (width, height)


# --- parsers never raise anything but domain errors ---


@given(st.binary())
def test_osc52_parse_domain_errors(data: bytes) -> None:
    match = osc52.RESPONSE_RE.search(data)
    if match is not None:
        with contextlib.suppress(ClipboardError):
            osc52.parse_response(match)


@given(st.binary())
def test_kitty_parse_domain_errors(data: bytes) -> None:
    match = kitty.PACKET_RE.search(data)
    if match is not None:
        with contextlib.suppress(ClipboardError):
            kitty.parse_packet(match)


@given(st.binary())
def test_image_size_parsers_domain_errors(data: bytes) -> None:
    for parser in (graphics.png_size, graphics.jpeg_size, graphics.webp_size):
        with contextlib.suppress(ClipboardError):
            parser(data)


@given(st.binary())
def test_base64_decode_domain_errors(data: bytes) -> None:
    with contextlib.suppress(ClipboardError):
        encoding.decode_bytes(data)


@given(st.text())
def test_base64_decode_str_domain_errors(value: str) -> None:
    with contextlib.suppress(ClipboardError):
        encoding.decode_bytes(value)


@given(st.binary())
def test_sniff_mime_never_raises(data: bytes) -> None:
    assert isinstance(sniff.sniff_mime(data), str)


# --- multiplexer passthrough ---


@given(st.binary())
def test_tmux_passthrough_round_trip(data: bytes) -> None:
    wrapped = mux.wrap_passthrough(data, env={"TMUX": "/tmp/sock,1,0"})
    assert wrapped.startswith(b"\x1bPtmux;")
    assert wrapped.endswith(ST)
    inner = wrapped[len(b"\x1bPtmux;") : -len(ST)]
    assert inner.replace(b"\x1b\x1b", b"\x1b") == data


@given(st.binary())
def test_screen_passthrough_round_trip(data: bytes) -> None:
    assert mux.wrap_passthrough(data, env={"STY": "1"}) == b"\x1bP" + data + ST


@given(st.binary())
def test_passthrough_identity_without_mux(data: bytes) -> None:
    assert mux.wrap_passthrough(data, env={"TERM": "xterm-256color"}) == data


# --- the response regexes must terminate quickly even on large garbage ---


@settings(deadline=timedelta(seconds=2))
@given(st.binary(min_size=1, max_size=100_000))
def test_response_regexes_terminate(data: bytes) -> None:
    osc52.RESPONSE_RE.search(data)
    kitty.PACKET_RE.search(data)
    graphics.RESPONSE_RE.search(data)

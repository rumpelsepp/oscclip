# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Coverage-guided fuzzing of the oscclip parsers with atheris (libFuzzer).

This is the Go-style equivalent of `go test -fuzz`: libFuzzer mutates inputs
guided by coverage, keeps interesting ones in the corpus directory and writes
crashes/hangs as artifacts.

Usage (from the project root):
    uv run python -m fuzz.fuzz_parsers fuzz/corpus -max_total_time=60 \
        -artifact_prefix=fuzz/crashes/

Seeds live in fuzz/corpus/; crashes and hangs are written to fuzz/crashes/.
Only ClipboardError (the domain error type) is tolerated; anything else
(ValueError, re.error, hangs, ...) is a bug and stops the fuzzer.
"""

from __future__ import annotations

import contextlib
import sys

import atheris

# Give coverage feedback for regex internals; must be enabled before the
# parser modules call re.compile at import time.
atheris.enabled_hooks.add("RegEx")

with atheris.instrument_imports():
    from tests.fake_tty import FakeTty

    from oscclip import encoding, mux, sniff
    from oscclip.errors import ClipboardError
    from oscclip.graphics import parse as graphics_parse
    from oscclip.kitty import parse as kitty_parse
    from oscclip.kitty import transport as kitty_transport
    from oscclip.osc52 import parse as osc52_parse
    from oscclip.osc52 import transport as osc52_transport


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Feed arbitrary bytes through every parser; domain errors are fine."""
    with contextlib.suppress(ClipboardError):
        match = osc52_parse.RESPONSE_RE.search(data)
        if match is not None:
            osc52_parse.parse_response(match)

        match = kitty_parse.PACKET_RE.search(data)
        if match is not None:
            packet = kitty_parse.parse_packet(match)
            kitty_parse.read_packets([packet])

        for regex in (
            graphics_parse.RESPONSE_RE,
            graphics_parse.DA1_RE,
            graphics_parse.CELL_SIZE_RE,
            graphics_parse.WINDOW_SIZE_RE,
        ):
            regex.search(data)
        for parser in (
            graphics_parse.png_size,
            graphics_parse.jpeg_size,
            graphics_parse.webp_size,
        ):
            parser(data)

        sniff.sniff_mime(data)
        encoding.decode_bytes(data)
        mux.wrap_passthrough(data, env={"TMUX": "x", "STY": "y", "TERM": "screen"})
        mux.wrap_passthrough(data, env={})

        # Transport level: run the capability/query round trips on the raw
        # bytes; a missing response raises ClipboardTimeoutError (suppressed).
        tty = FakeTty(data)
        osc52_transport.query(tty, primary=False, timeout=0.01)
        kitty_transport.supports(tty, timeout=0.01)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

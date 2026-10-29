# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""Fake terminal implementations for the test suite."""

from __future__ import annotations

import re
from collections.abc import Sequence


class FakeTty:
    """A scripted terminal implementation.

    Responses are provided upfront as a single blob; read_until() returns
    matches from that blob in order, mimicking RawTerminal's buffering.
    """

    def __init__(self, responses: bytes = b"") -> None:
        self.responses = responses
        self.position = 0
        self.written: list[bytes] = []
        self.timeouts: list[float] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    def read_until(
        self, patterns: Sequence[re.Pattern[bytes]], timeout: float
    ) -> re.Match[bytes] | None:
        self.timeouts.append(timeout)
        for pattern in patterns:
            match = pattern.search(self.responses, self.position)
            if match is not None:
                self.position = match.end()
                return match
        return None


class FakeRawTerminal:
    """A stand-in for RawTerminal which yields a FakeTty."""

    def __init__(self, tty: FakeTty) -> None:
        self._tty = tty

    def __enter__(self) -> FakeTty:
        return self._tty

    def __exit__(self, *_args: object) -> None:
        return None

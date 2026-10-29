# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Raw terminal I/O on the controlling terminal."""

from __future__ import annotations

import logging
import os
import re
import selectors
import termios
import time
import tty as tty_module
from collections.abc import Sequence
from typing import Any, Protocol, Self

_READ_CHUNK_SIZE = 4096

logger = logging.getLogger(__name__)


class Terminal(Protocol):
    """Minimal two-way terminal interface used by the clipboard protocols."""

    def write(self, data: bytes) -> None: ...

    def read_until(
        self, patterns: Sequence[re.Pattern[bytes]], timeout: float
    ) -> re.Match[bytes] | None: ...


class RawTerminal:
    """The controlling terminal switched to raw mode.

    Escape sequences are written to and terminal responses are read back from
    the same file descriptor.  Input typed by the user in the meantime is
    discarded.
    """

    def __init__(self, path: str = "/dev/tty", *, max_buffer_size: int = 64 * 1024 * 1024) -> None:
        self._path = path
        self._max_buffer_size = max_buffer_size
        self._fd: int | None = None
        self._saved_attrs: list[Any] | None = None
        self._buffer = b""

    def __enter__(self) -> Self:
        logger.debug("opening terminal %s", self._path)
        fd = os.open(self._path, os.O_RDWR)
        try:
            self._saved_attrs = termios.tcgetattr(fd)
            tty_module.setraw(fd)
            # Keep ISIG enabled so that the user can still interrupt the
            # program with Ctrl+C while it is waiting for responses.
            attrs = termios.tcgetattr(fd)
            attrs[3] |= termios.ISIG
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        except BaseException:
            os.close(fd)
            self._saved_attrs = None
            raise
        os.set_blocking(fd, False)
        self._fd = fd
        return self

    def __exit__(self, *_args: object) -> None:
        if (fd := self._fd) is None:
            return
        if self._saved_attrs is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, self._saved_attrs)
        os.close(fd)
        self._fd = None
        self._saved_attrs = None
        self._buffer = b""

    def write(self, data: bytes) -> None:
        """Write data to the terminal."""
        if (fd := self._fd) is None:
            raise RuntimeError("terminal is not open")
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view) :]

    def read_until(
        self, patterns: Sequence[re.Pattern[bytes]], timeout: float
    ) -> re.Match[bytes] | None:
        """Read from the terminal until one of the given patterns matches.

        Everything up to and including the match is consumed.  Returns None
        if no pattern matches within the given timeout.
        """
        if (fd := self._fd) is None:
            raise RuntimeError("terminal is not open")
        with selectors.DefaultSelector() as selector:
            selector.register(fd, selectors.EVENT_READ)
            deadline = time.monotonic() + timeout
            while True:
                for pattern in patterns:
                    if (match := pattern.search(self._buffer)) is not None:
                        self._buffer = self._buffer[match.end() :]
                        return match
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    return None
                chunk = os.read(fd, _READ_CHUNK_SIZE)
                if not chunk:
                    return None
                self._buffer += chunk
                if len(self._buffer) > self._max_buffer_size:
                    self._buffer = self._buffer[-self._max_buffer_size :]

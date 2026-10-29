# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""ctypes binding for libghostty-vt used by the conformance tests.

The structs, enum values and callback contracts follow the documented
API in the ghostty source tree (include/ghostty/vt/).  The library uses
sized structs: the first field of every struct is its byte size, and
replies are only read up to the size the library knows about.

GhosttyTerminalHarness implements oscclip's Terminal protocol on top of
a real libghostty-vt terminal.  Everything is synchronous: the terminal
emits response bytes through the write_pty callback while
ghostty_terminal_vt_write() runs, so read_until() only has to search the
buffered output.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import re
from collections.abc import Sequence

LIB_NAME = "ghostty-vt"

# Option values passed to ghostty_terminal_set().
OPT_WRITE_PTY = 1
OPT_CLIPBOARD_WRITE = 26
OPT_CLIPBOARD_READ = 38

# GhosttyClipboardLocation values.
LOCATION_STANDARD = 0
LOCATION_PRIMARY = 2

# GhosttyClipboardWriteResult and GhosttyClipboardReadResult values.
WRITE_RESULT_SUCCESS = 0
WRITE_RESULT_DENIED = 1
READ_RESULT_SUCCESS = 0


def find_library() -> str | None:
    """Return the path of libghostty-vt, or None if it is not available."""
    return ctypes.util.find_library(LIB_NAME)


class GhosttyString(ctypes.Structure):
    """A borrowed, non-null-terminated string."""

    _fields_ = [
        ("ptr", ctypes.c_char_p),
        ("len", ctypes.c_size_t),
    ]

    def to_bytes(self) -> bytes:
        if self.ptr is None:
            return b""
        return ctypes.string_at(self.ptr, self.len)


class GhosttyClipboardContent(ctypes.Structure):
    """One MIME representation of clipboard contents."""

    _fields_ = [
        ("mime", GhosttyString),
        ("data", GhosttyString),
    ]


class GhosttyClipboardWriteReply(ctypes.Structure):
    """The reply to a clipboard write request."""

    _fields_ = [
        ("size", ctypes.c_size_t),
        ("result", ctypes.c_int),
        ("remember", ctypes.c_bool),
    ]


class GhosttyClipboardWrite(ctypes.Structure):
    """A synchronous clipboard write request."""

    _fields_ = [
        ("size", ctypes.c_size_t),
        ("location", ctypes.c_int),
        ("contents", ctypes.POINTER(GhosttyClipboardContent)),
        ("contents_len", ctypes.c_size_t),
        ("name", GhosttyString),
        ("granted", ctypes.c_bool),
        ("can_remember", ctypes.c_bool),
        ("ctx", ctypes.c_void_p),
        ("reply", ctypes.c_void_p),
    ]


class GhosttyClipboardReadReply(ctypes.Structure):
    """The reply to a clipboard read request."""

    _fields_ = [
        ("size", ctypes.c_size_t),
        ("result", ctypes.c_int),
        ("contents", ctypes.POINTER(GhosttyClipboardContent)),
        ("contents_len", ctypes.c_size_t),
        ("available", ctypes.POINTER(GhosttyString)),
        ("available_len", ctypes.c_size_t),
        ("remember", ctypes.c_bool),
    ]


class GhosttyClipboardRead(ctypes.Structure):
    """A synchronous clipboard read request."""

    _fields_ = [
        ("size", ctypes.c_size_t),
        ("location", ctypes.c_int),
        ("mimes", ctypes.POINTER(GhosttyString)),
        ("mimes_len", ctypes.c_size_t),
        ("list", ctypes.c_bool),
        ("name", GhosttyString),
        ("granted", ctypes.c_bool),
        ("can_remember", ctypes.c_bool),
        ("ctx", ctypes.c_void_p),
        ("reply", ctypes.c_void_p),
    ]


# Callback types.  The reply functions are cast at the call site; typed
# signatures would be circular here.
WRITE_REPLY_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
READ_REPLY_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)

# Type aliases; function calls are not valid in annotations directly.
_UbytePtr = ctypes.POINTER(ctypes.c_ubyte)
_WritePtr = ctypes.POINTER(GhosttyClipboardWrite)
_ReadPtr = ctypes.POINTER(GhosttyClipboardRead)
WRITE_PTY_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, _UbytePtr, ctypes.c_size_t)
CLIPBOARD_WRITE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, _WritePtr)
CLIPBOARD_READ_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, _ReadPtr)


class GhosttyTerminalHarness:
    """A real libghostty-vt terminal wired as an oscclip Terminal."""

    def __init__(self, library: ctypes.CDLL, cols: int = 80, rows: int = 24) -> None:
        self._library = library
        self._output = bytearray()
        self.clipboard: dict[str, bytes] = {}
        self.locations: list[int] = []
        self.deny_writes = False

        library.ghostty_terminal_new.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_uint16,
            ctypes.c_uint16,
        ]
        library.ghostty_terminal_new.restype = ctypes.c_int
        library.ghostty_terminal_free.argtypes = [ctypes.c_void_p]
        library.ghostty_terminal_free.restype = None
        library.ghostty_terminal_set.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        library.ghostty_terminal_set.restype = ctypes.c_int
        library.ghostty_terminal_vt_write.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]
        library.ghostty_terminal_vt_write.restype = None

        terminal = ctypes.c_void_p()
        result = library.ghostty_terminal_new(None, ctypes.byref(terminal), cols, rows)
        if result != 0:
            raise RuntimeError(f"failed to create the terminal: {result}")
        self._terminal = terminal

        # Keep the callback objects alive; the library stores raw pointers.
        self._write_pty_fn = WRITE_PTY_FN(self._on_write_pty)
        self._clipboard_write_fn = CLIPBOARD_WRITE_FN(self._on_clipboard_write)
        self._clipboard_read_fn = CLIPBOARD_READ_FN(self._on_clipboard_read)
        for option, callback in (
            (OPT_WRITE_PTY, self._write_pty_fn),
            (OPT_CLIPBOARD_WRITE, self._clipboard_write_fn),
            (OPT_CLIPBOARD_READ, self._clipboard_read_fn),
        ):
            value = ctypes.cast(callback, ctypes.c_void_p)
            library.ghostty_terminal_set(terminal, option, value)

    def close(self) -> None:
        self._library.ghostty_terminal_free(self._terminal)

    # --- oscclip.term.Terminal protocol ---

    def write(self, data: bytes) -> None:
        self._library.ghostty_terminal_vt_write(self._terminal, data, len(data))

    def read_until(
        self, patterns: Sequence[re.Pattern[bytes]], timeout: float
    ) -> re.Match[bytes] | None:
        buffer = bytes(self._output)
        for pattern in patterns:
            match = pattern.search(buffer)
            if match is not None:
                del self._output[: match.end()]
                return match
        return None

    # --- library callbacks ---

    def _on_write_pty(self, terminal: int, userdata: int, data: ctypes._CData, length: int) -> None:
        self._output += ctypes.string_at(ctypes.cast(data, ctypes.c_void_p), length)

    def _on_clipboard_write(self, terminal: int, userdata: int, write: ctypes._CData) -> None:
        request = ctypes.cast(write, _WritePtr).contents
        self.locations.append(request.location)
        self.clipboard.clear()
        for index in range(request.contents_len):
            content = request.contents[index]
            mime = content.mime.to_bytes().decode("utf-8", errors="replace")
            self.clipboard[mime] = content.data.to_bytes()
        result = WRITE_RESULT_DENIED if self.deny_writes else WRITE_RESULT_SUCCESS
        reply = GhosttyClipboardWriteReply(ctypes.sizeof(GhosttyClipboardWriteReply), result, False)
        reply_fn = ctypes.cast(request.reply, WRITE_REPLY_FN)
        reply_fn(ctypes.cast(write, ctypes.c_void_p), ctypes.byref(reply))

    def _on_clipboard_read(self, terminal: int, userdata: int, read: ctypes._CData) -> None:
        request = ctypes.cast(read, _ReadPtr).contents
        contents = []
        available = []
        for mime, data in self.clipboard.items():
            mime_buf = ctypes.cast(ctypes.create_string_buffer(mime.encode()), ctypes.c_char_p)
            data_buf = ctypes.cast(ctypes.create_string_buffer(data), ctypes.c_char_p)
            contents.append(
                GhosttyClipboardContent(
                    GhosttyString(mime_buf, len(mime)),
                    GhosttyString(data_buf, len(data)),
                )
            )
            available.append(GhosttyString(mime_buf, len(mime)))
        contents_array = (GhosttyClipboardContent * len(contents))(*contents)
        available_array = (GhosttyString * len(available))(*available)
        reply = GhosttyClipboardReadReply(
            ctypes.sizeof(GhosttyClipboardReadReply),
            READ_RESULT_SUCCESS,
            contents_array,
            len(contents_array),
            available_array,
            len(available_array),
            False,
        )
        reply_fn = ctypes.cast(request.reply, READ_REPLY_FN)
        reply_fn(ctypes.cast(read, ctypes.c_void_p), ctypes.byref(reply))

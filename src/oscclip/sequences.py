# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Terminal escape sequence constants shared by the protocol implementations."""

from __future__ import annotations

#: Escape byte which introduces all control sequences.
ESC = b"\x1b"

#: Bell terminator for OSC sequences.
BEL = b"\x07"

#: Operating System Command sequence introducer.
OSC = ESC + b"]"

#: String Terminator; terminates OSC, DCS and APC sequences.
ST = ESC + b"\\"

#: Control Sequence Introducer.
CSI = ESC + b"["

#: Device Control String introducer.
DCS = ESC + b"P"

#: Application Program Command introducer (kitty graphics protocol).
APC = ESC + b"_"

# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: EUPL-1.2

"""Exception types shared by the clipboard protocol implementations."""


class ClipboardError(Exception):
    """Base class for all clipboard related errors."""


class ClipboardTimeoutError(ClipboardError):
    """The terminal did not respond in time."""


class ClipboardProtocolError(ClipboardError):
    """The terminal sent an invalid or unexpected response."""


class ClipboardDeniedError(ClipboardError):
    """Access to the clipboard was denied by the user or the system."""

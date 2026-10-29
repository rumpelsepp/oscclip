# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.fake_tty import FakeTty


@pytest.fixture
def make_tty() -> Callable[..., FakeTty]:
    """Factory for scripted FakeTty instances."""

    def factory(responses: bytes = b"") -> FakeTty:
        return FakeTty(responses)

    return factory

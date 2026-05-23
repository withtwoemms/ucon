# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core.exceptions
====================

Exception classes for the ucon core layer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ucon.core.unit import Unit


class DimensionNotCovered(Exception):
    """Raised when a BaseUnits mapping doesn't cover a requested dimension."""
    pass


class UnknownUnitError(Exception):
    """Raised when a unit string cannot be resolved to a known unit."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Unknown unit: {name!r}")


class NonScalableError(UnknownUnitError):
    """Raised when a scale prefix is applied to a unit marked non-scalable.

    Subclass of :class:`UnknownUnitError` so that callers that catch the
    parent class continue to work. Callers that want the richer diagnostic
    can catch :class:`NonScalableError` directly and inspect :attr:`base`
    and :attr:`prefix`.

    Attributes
    ----------
    attempted : str
        The full unit string that failed to parse (e.g. ``"Pflop"``).
    base : Unit
        The base unit that was found but is marked non-scalable.
    prefix : str
        The prefix shorthand that was attempted (e.g. ``"P"`` for peta).
    """

    def __init__(self, attempted: str, base: 'Unit', prefix: str):
        self.attempted = attempted
        self.base = base
        self.prefix = prefix
        # Bypass UnknownUnitError.__init__ to install a precise message.
        Exception.__init__(
            self,
            f"Unit {attempted!r} not found: base unit {base.name!r} is "
            f"registered but marked non-scalable, so prefix {prefix!r} "
            f"cannot be applied.",
        )
        self.name = attempted

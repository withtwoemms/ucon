"""
ucon.unit
==========

Defines the **Unit** abstraction — the symbolic and algebraic representation of
a measurable quantity associated with a :class:`ucon.dimension.Dimension`.

A :class:`Unit` pairs a human-readable name and aliases with its underlying
dimension.

Units are composable:

    >>> from ucon import units
    >>> units.meter / units.second
    <velocity | (m/s)>

They can be multiplied or divided to form compound units, and their dimensional
relationships are preserved algebraically.
"""
from ucon.dimension import Dimension



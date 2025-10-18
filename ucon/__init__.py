"""
ucon
====

*ucon* (Unit Conversion & Dimensional Analysis) is a lightweight,
introspective library for reasoning about physical quantities.

Unlike conventional unit libraries that focus purely on arithmetic convenience,
*ucon* models the **semantics** of measurement-—exposing the algebra of
dimensions and the structure of compound units.

Overview
--------
*ucon* is organized into a small set of composable modules:

- :mod:`ucon.dimension` — defines the algebra of physical dimensions using
  exponent vectors. Provides the foundation for all dimensional reasoning.
- :mod:`ucon.unit` — defines the :class:`Unit` abstraction, representing a
  measurable quantity with an associated dimension, factor, and offset.
- :mod:`ucon.core` — implements numeric handling via :class:`Number`,
  :class:`Scale`, and :class:`Ratio`, along with unified conversion logic.
- :mod:`ucon.units` — declares canonical SI base and derived units for immediate use.

Design Philosophy
-----------------
*ucon* treats unit conversion not as a lookup problem but as an **algebra**:

- **Dimensional Algebra** — all physical quantities are represented as
  exponent vectors over the seven SI bases, ensuring strict composability.
- **Explicit Semantics** — units, dimensions, and scales are first-class
  objects, not strings or tokens.
- **Unified Conversion Model** — all conversions are expressed through one
  data-driven framework that is generalizable to arbitrary unit systems.
"""
from ucon import units
from ucon.unit import Unit
from ucon.core import Exponent, Number, Scale, Ratio
from ucon.dimension import Dimension


__all__ = [
    'Exponent',
    'Dimension',
    'Number',
    'Ratio',
    'Scale',
    'Unit',
    'units',
]

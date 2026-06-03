# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon._algebra_cache
===================

Per-instance cache for Dimension algebraic operations and the accessor
that routes through the active UnitSystem.

This module imports only :mod:`ucon._active`, placing it at Layer 0/1
in the import DAG — below :mod:`ucon.dimension` (Layer 2).

It lives at the package root rather than inside ``ucon.system`` so that
:mod:`ucon.dimension` can import it without triggering
``ucon.system/__init__.py`` execution, which would close cycles back
through ``resolver`` → ``core``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ucon._active import _active


@dataclass
class AlgebraCache:
    """Per-instance cache for ``Dimension`` algebraic operations.

    Holds three sub-caches keyed by argument tuples:

    - ``mul``: ``(Dimension, Dimension) -> Dimension``
    - ``div``: ``(Dimension, Dimension) -> Dimension``
    - ``pow``: ``(Dimension, exponent) -> Dimension``

    Owned by each :class:`~ucon.system.UnitSystem` instance.
    """

    mul: dict = field(default_factory=dict)
    div: dict = field(default_factory=dict)
    pow: dict = field(default_factory=dict)

    def clear(self) -> None:
        """Empty all three sub-caches."""
        self.mul.clear()
        self.div.clear()
        self.pow.clear()


def _get_active_cache() -> AlgebraCache:
    """Return the algebra cache that ``Dimension`` algebra should use now.

    Routes through the active :class:`UnitSystem`'s per-instance cache
    via the :class:`~ucon.system.ActiveContext` pushed by :func:`use`.

    During bootstrap (before eager init completes) no active context
    exists; a fresh :class:`AlgebraCache` is returned so that dimension
    algebra works uncached.  Post-init, the active system's cache is
    always returned.
    """
    ctx = _active.get()
    if ctx is None:
        return AlgebraCache()
    return ctx.system._algebra_cache


__all__ = ['AlgebraCache', '_get_active_cache']

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

    Owned by each :class:`~ucon.system.UnitSystem` instance.  The module-level
    :data:`_DEFAULT_ALGEBRA_CACHE` serves as the fallback when no system has
    been activated via :func:`~ucon.system.use`.
    """

    mul: dict = field(default_factory=dict)
    div: dict = field(default_factory=dict)
    pow: dict = field(default_factory=dict)

    def clear(self) -> None:
        """Empty all three sub-caches."""
        self.mul.clear()
        self.div.clear()
        self.pow.clear()


#: Module-level fallback used by ``_get_active_cache`` when no
#: ``UnitSystem`` has been activated via :func:`use`.
_DEFAULT_ALGEBRA_CACHE: AlgebraCache = AlgebraCache()


def _get_active_cache() -> AlgebraCache:
    """Return the algebra cache that ``Dimension`` algebra should use now.

    Routes through the active :class:`UnitSystem`'s per-instance cache when
    an :class:`~ucon.system.ActiveContext` has been pushed via :func:`use`.
    Falls back to :data:`_DEFAULT_ALGEBRA_CACHE` otherwise.

    The fallback is intentionally a stable module-level object rather than
    a fresh snapshot: that would construct a new :class:`AlgebraCache` on
    every call and defeat memoization.
    """
    ctx = _active.get()
    if ctx is None:
        return _DEFAULT_ALGEBRA_CACHE
    return ctx.system._algebra_cache


__all__ = ['AlgebraCache', '_get_active_cache', '_DEFAULT_ALGEBRA_CACHE']

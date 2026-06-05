# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon._active
============

The ``_active`` ContextVar that tracks the currently active UnitSystem.

This module has **zero** intra-ucon imports, placing it at the bottom of the
import DAG (Layer 0). It lives at the package root rather than inside
``ucon.system`` so that low-level modules (e.g. ``ucon.core._types``) can
import it without triggering ``ucon.system/__init__.py`` execution, which
would close cycles back through ``resolver`` → ``core``.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Typed as Any to avoid importing UnitSystem (which lives at a higher layer).
# The actual value is always ``UnitSystem | None`` at runtime.
_active: ContextVar[Any] = ContextVar('ucon_active_system', default=None)


def active():
    """Return the currently active UnitSystem, or None.

    This is the **raw** accessor — it returns whatever is stored in the
    ContextVar without any fallback logic.
    """
    return _active.get()


def resolve_basis(*, system: Any = None, fallback: Any = None) -> Any:
    """Resolve a basis using the standard precedence cascade.

    Precedence: explicit ``system`` argument > active ``UnitSystem`` >
    ``fallback``. The fallback is only consulted when no active system
    is set (bootstrap path).

    Parameters
    ----------
    system : UnitSystem, optional
        When provided, ``system.basis`` is returned directly.
    fallback : Basis, optional
        Returned when no system is supplied and no system is active.

    Returns
    -------
    Basis
        The resolved basis.

    Notes
    -----
    ``system`` and ``fallback`` are duck-typed so this resolver can live
    at Layer 0 without importing higher-layer modules.
    """
    if system is not None:
        return system.basis
    ctx = _active.get()
    return ctx.system.basis if ctx is not None else fallback


def resolve_basis_graph(
    *, system: Any = None, graph: Any = None, fallback: Any = None
) -> Any:
    """Resolve a basis graph using the standard precedence cascade.

    Precedence: explicit ``graph`` > explicit ``system.basis_graph`` >
    active ``UnitSystem``'s ``basis_graph`` > ``fallback``. The fallback
    may be a callable, in which case it is invoked lazily only when
    needed (typical for ``_build_standard_basis_graph``, which is
    expensive to construct).

    Parameters
    ----------
    system : UnitSystem, optional
        Used when ``graph`` is not given; contributes ``system.basis_graph``.
    graph : BasisGraph, optional
        Explicit graph override; wins over everything.
    fallback : BasisGraph or callable, optional
        Used when no other source is available. If callable, called with
        no arguments.

    Returns
    -------
    BasisGraph
        The resolved basis graph.
    """
    if graph is not None:
        return graph
    if system is not None:
        return system.basis_graph
    ctx = _active.get()
    if ctx is not None:
        return ctx.system.basis_graph
    return fallback() if callable(fallback) else fallback


__all__ = ['_active', 'active', 'resolve_basis', 'resolve_basis_graph']

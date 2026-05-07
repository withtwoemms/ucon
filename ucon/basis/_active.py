# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ContextVar-scoped active basis and basis graph.

Holds the module-level mutable defaults and the per-context overrides for
the basis subpackage. Living in a leaf module breaks what would otherwise
be a load-order cycle: ``vector.py`` imports the accessor at top of file;
``graph.py`` re-exports the names below for back-compat. The single
deferred import in the subpackage is the lazy default-graph factory inside
:func:`get_basis_graph`.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from ucon.basis.builtin import SI
from ucon.basis.types import Basis

if TYPE_CHECKING:
    from ucon.basis.graph import BasisGraph


_default_basis: ContextVar[Basis | None] = ContextVar("basis", default=None)
_basis_graph_context: ContextVar["BasisGraph | None"] = ContextVar(
    "basis_graph", default=None
)
_default_basis_graph: "BasisGraph | None" = None


def get_default_basis() -> Basis:
    """Get the current default basis.

    Returns the context-local basis if one has been set via
    :func:`using_basis`, otherwise returns SI.

    Returns
    -------
    Basis
        The active basis for the current context.
    """
    return _default_basis.get() or SI


def get_basis_graph() -> "BasisGraph":
    """Get the current basis graph.

    Priority:

    1. Context-local graph (from :func:`using_basis_graph`)
    2. Module-level default graph (lazily built with standard transforms)

    Returns
    -------
    BasisGraph
        The active basis graph for the current context.
    """
    global _default_basis_graph
    ctx_graph = _basis_graph_context.get()
    if ctx_graph is not None:
        return ctx_graph
    if _default_basis_graph is None:
        # Deferred import: graph.py owns the standard-graph factory and
        # imports types from this subpackage. Importing it at module load
        # would cycle through builtin -> types -> _active (this file).
        from ucon.basis.graph import _build_standard_basis_graph

        _default_basis_graph = _build_standard_basis_graph()
    return _default_basis_graph


def set_default_basis_graph(graph: "BasisGraph") -> None:
    """Replace the module-level default basis graph.

    Parameters
    ----------
    graph : BasisGraph
        The new default basis graph.
    """
    global _default_basis_graph
    _default_basis_graph = graph


def reset_default_basis_graph() -> None:
    """Reset to the standard basis graph on next access.

    The standard graph (with SI, CGS, CGS-ESU, and NATURAL transforms)
    is lazily rebuilt when :func:`get_basis_graph` is next called.
    """
    global _default_basis_graph
    _default_basis_graph = None


@contextmanager
def using_basis(basis: Basis):
    """Context manager for scoped basis override.

    Within the ``with`` block, :func:`get_default_basis` returns the
    provided basis instead of SI. Thread-safe via ContextVar.

    Parameters
    ----------
    basis : Basis
        The basis to use within this context.

    Yields
    ------
    Basis
        The provided basis.
    """
    token = _default_basis.set(basis)
    try:
        yield basis
    finally:
        _default_basis.reset(token)


@contextmanager
def using_basis_graph(graph: "BasisGraph | None"):
    """Context manager for scoped basis graph override.

    Within the ``with`` block, :func:`get_basis_graph` returns the
    provided graph. Thread-safe via ContextVar.

    Parameters
    ----------
    graph : BasisGraph or None
        The basis graph to use, or None to fall back to the module default.

    Yields
    ------
    BasisGraph or None
        The provided graph.
    """
    token = _basis_graph_context.set(graph)
    try:
        yield graph
    finally:
        _basis_graph_context.reset(token)

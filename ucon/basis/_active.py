# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Active basis context: scoped overrides for the default basis and basis graph.

Owns the ContextVars and accessors used by :class:`Vector` arithmetic and
unit-resolution code paths to discover the currently-active :class:`Basis`
and :class:`BasisGraph`. Split out from :mod:`ucon.basis.graph` so that
``ucon.basis.__init__`` (where ``Vector`` lives) can reference
:func:`get_basis_graph` at module load without circular-import gymnastics:

- :mod:`ucon.basis._active` depends on :mod:`ucon.basis` (for ``Basis``) and
  :mod:`ucon.basis.builtin` (for ``SI``), nothing else at module load.
- :mod:`ucon.basis.graph` imports the ContextVars from this module and
  re-exports the accessors for back-compat with callers that import them
  directly from ``ucon.basis.graph``.

The default :class:`BasisGraph` is built lazily on first access via a
deferred import of :func:`ucon.basis.graph._build_standard_basis_graph`.
"""

from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager
from typing import TYPE_CHECKING

from ucon.basis import Basis
from ucon.basis.builtin import SI

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
    """
    return _default_basis.get() or SI


def get_basis_graph() -> "BasisGraph":
    """Get the current basis graph.

    Priority:

    1. Context-local graph (from :func:`using_basis_graph`)
    2. Module-level default graph (lazily built with standard transforms)
    """
    global _default_basis_graph
    ctx_graph = _basis_graph_context.get()
    if ctx_graph is not None:
        return ctx_graph
    if _default_basis_graph is None:
        # Deferred import: graph.py imports this module at load time.
        from ucon.basis.graph import _build_standard_basis_graph

        _default_basis_graph = _build_standard_basis_graph()
    return _default_basis_graph


def set_default_basis_graph(graph: "BasisGraph") -> None:
    """Replace the module-level default basis graph."""
    global _default_basis_graph
    _default_basis_graph = graph


def reset_default_basis_graph() -> None:
    """Reset to the standard basis graph on next access.

    The standard graph is lazily rebuilt on the next call to
    :func:`get_basis_graph`.
    """
    global _default_basis_graph
    _default_basis_graph = None


@contextmanager
def using_basis(basis: Basis):
    """Context manager for scoped basis override.

    Within the ``with`` block, :func:`get_default_basis` returns the
    provided basis instead of SI. Thread-safe via ContextVar.
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
    """
    token = _basis_graph_context.set(graph)
    try:
        yield graph
    finally:
        _basis_graph_context.reset(token)

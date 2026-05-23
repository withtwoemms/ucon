# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.graph_registry
====================

Default :class:`~ucon.graph.ConversionGraph` lifecycle management.

Functions
---------
- :func:`get_default_graph` — Get the current default graph.
- :func:`set_default_graph` — Replace the default graph (deprecated).
- :func:`reset_default_graph` — Reset to standard graph on next access (deprecated).
- :func:`using_conversion_graph` — Context manager for scoped graph override.
- :func:`using_graph` — Deprecated alias for :func:`using_conversion_graph`.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from ucon.core._parsing_graph import _parsing_graph
from ucon.system._active import _active as _active_system

if TYPE_CHECKING:
    from ucon.graph import ConversionGraph

__all__ = [
    'get_default_graph',
    'set_default_graph',
    'reset_default_graph',
    'using_conversion_graph',
    'using_graph',
]


_default_graph: ConversionGraph | None = None
_graph_context: ContextVar[ConversionGraph | None] = ContextVar("graph", default=None)


def get_default_graph() -> ConversionGraph:
    """Get the current conversion graph.

    Priority:
    1. Context-local graph (from ``using_conversion_graph``)
    2. Active :class:`~ucon.system.UnitSystem`'s ``conversion_graph``
    3. Module-level default graph (lazily built — legacy fallback)
    """
    # Check context first
    graph = _graph_context.get()
    if graph is not None:
        return graph

    # Check active system
    system = _active_system.get()
    if system is not None:
        return system.conversion_graph

    # Fall back to module default
    global _default_graph
    if _default_graph is None:
        _default_graph = _build_standard_graph()
    return _default_graph


def set_default_graph(graph: ConversionGraph) -> None:
    """Replace the module-level default graph.

    .. deprecated:: 1.11
       The module-level default graph is being retired in favor of
       :class:`~ucon.system.UnitSystem` ownership.  With eager system
       initialization the active system's ``conversion_graph`` (tier 2)
       takes precedence, so mutations via this function are invisible to
       :func:`get_default_graph`.  Use ``using_conversion_graph(graph)``
       for scoped overrides or ``use(system)`` to switch the entire
       active system.  Scheduled for removal in ucon 2.0.

    Parameters
    ----------
    graph : ConversionGraph
        The new default conversion graph.
    """
    import warnings
    warnings.warn(
        "ucon.graph.set_default_graph is deprecated; the module-level "
        "default graph is being retired in favor of UnitSystem ownership. "
        "Use 'using_conversion_graph(graph)' for scoped overrides or "
        "'use(system)' to switch the active system. "
        "Scheduled for removal in ucon 2.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _default_graph
    _default_graph = graph


def reset_default_graph() -> None:
    """Reset to the standard graph on next access.

    .. deprecated:: 1.11
       The module-level default graph is being retired in favor of
       :class:`~ucon.system.UnitSystem` ownership.  With eager system
       initialization the active system's ``conversion_graph`` (tier 2)
       takes precedence, so this function has no visible effect.  Leave
       the ``use(system)`` block instead of resetting a global.
       Scheduled for removal in ucon 2.0.

    The standard graph (with all built-in unit conversions) is lazily
    rebuilt when :func:`get_default_graph` is next called.
    """
    import warnings
    warnings.warn(
        "ucon.graph.reset_default_graph is deprecated; the module-level "
        "default graph is being retired in favor of UnitSystem ownership. "
        "Leave the 'use(system)' block instead of resetting a global. "
        "Scheduled for removal in ucon 2.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _default_graph
    _default_graph = None


@contextmanager
def using_conversion_graph(graph: ConversionGraph):
    """Context manager for scoped :class:`ConversionGraph` override.

    Sets both the conversion graph and parsing graph contexts, so that
    name resolution and conversions both use the same graph.

    The canonical name as of v1.8. The older :func:`using_graph` is a
    :class:`PendingDeprecationWarning` alias preserved for one release
    cycle; new code should call ``using_conversion_graph`` to align with
    :attr:`UnitSystem.basis_graph` / ``UnitSystem.conversion_graph``
    naming.

    Usage::

        with using_conversion_graph(custom_graph):
            result = value.to(target)        # uses custom_graph
            unit = parse_unit("custom_unit") # resolves in custom_graph

    Parameters
    ----------
    graph : ConversionGraph
        The graph to use within this context.

    Yields
    ------
    ConversionGraph
        The same graph passed in.
    """
    token_graph = _graph_context.set(graph)
    token_parsing = _parsing_graph.set(graph)
    try:
        yield graph
    finally:
        _graph_context.reset(token_graph)
        _parsing_graph.reset(token_parsing)


@contextmanager
def using_graph(graph: ConversionGraph):
    """Deprecated alias for :func:`using_conversion_graph`.

    .. deprecated:: 1.8
       The name is ambiguous next to :func:`ucon.basis.using_basis_graph`.
       Use :func:`using_conversion_graph` instead. Scheduled for removal
       in ucon 2.0.

    Parameters
    ----------
    graph : ConversionGraph
        The graph to use within this context.

    Yields
    ------
    ConversionGraph
        The same graph passed in.
    """
    import warnings
    warnings.warn(
        "ucon.using_graph is deprecated; use ucon.using_conversion_graph "
        "for symmetry with using_basis_graph. Scheduled for removal in "
        "ucon 2.0.",
        DeprecationWarning,
        stacklevel=3,
    )
    with using_conversion_graph(graph) as g:
        yield g


def _build_standard_graph() -> ConversionGraph:
    """Load the default conversion graph from comprehensive.ucon.toml."""
    from ucon._loader import get_graph
    return get_graph()


def _build_standard_edges(graph: ConversionGraph) -> None:  # pragma: no cover
    """Legacy stub — edges are now loaded from TOML via _build_standard_graph().

    Retained as a no-op for any external code that references it.
    """
    return

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core._parsing_graph
========================

ContextVar that tracks the graph used for name resolution during parsing.
Shared between graph.py and units.py.
"""
from __future__ import annotations

from contextvars import ContextVar

_parsing_graph: ContextVar = ContextVar("parsing_graph", default=None)


def _get_parsing_graph():
    """Get the graph to use for name resolution during parsing.

    Returns the context-local parsing graph if set, otherwise None.
    Used by _lookup_factor() to check graph-local registry first.

    Returns
    -------
    ConversionGraph | None
        The parsing graph, or None if not in a using_graph() context.
    """
    return _parsing_graph.get()

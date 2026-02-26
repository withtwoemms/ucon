# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.mcp.session
================

Injectable session state for MCP tools.

Provides session persistence across tool calls using FastMCP's lifespan context.
ContextVar-based isolation doesn't work for MCP because each tool call runs in
a separate async task. The lifespan context persists for the server's lifetime
and is accessible to all tools via Context injection.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ucon.constants import Constant
    from ucon.graph import ConversionGraph


@runtime_checkable
class SessionState(Protocol):
    """Protocol for injectable MCP session state.

    Allows dependency injection of session management for testing
    and custom implementations.

    Concurrency Model
    -----------------
    MCP protocol is request-response: client waits for each response before
    the next request. Tool calls are sequential by protocol design, so no
    locks are needed. Session state modifications are single-writer.
    """

    def get_graph(self) -> "ConversionGraph":
        """Get the session's conversion graph."""
        ...

    def get_constants(self) -> dict[str, "Constant"]:
        """Get the session's custom constants."""
        ...

    def reset(self) -> None:
        """Reset session to default state."""
        ...


class DefaultSessionState:
    """Default session state implementation.

    Maintains a single conversion graph and constants dict
    for the lifetime of the MCP server session.

    Parameters
    ----------
    base_graph : ConversionGraph | None
        Optional base graph to copy from. If None, uses get_default_graph().

    Examples
    --------
    >>> session = DefaultSessionState()
    >>> graph = session.get_graph()
    >>> graph.register_unit(custom_unit)
    >>> # Unit persists across subsequent get_graph() calls
    >>> graph2 = session.get_graph()
    >>> assert graph is graph2  # Same instance
    """

    def __init__(self, base_graph: "ConversionGraph | None" = None):
        self._base_graph = base_graph
        self._graph: "ConversionGraph | None" = None
        self._constants: dict[str, "Constant"] = {}

    def get_graph(self) -> "ConversionGraph":
        """Get or create the session graph.

        Returns a copy of the base graph on first access, then reuses
        the session graph for subsequent calls.
        """
        if self._graph is None:
            from ucon.graph import get_default_graph
            base = self._base_graph or get_default_graph()
            self._graph = base.copy()
        return self._graph

    def get_constants(self) -> dict[str, "Constant"]:
        """Get the session's custom constants dictionary."""
        return self._constants

    def reset(self) -> None:
        """Reset session to default state.

        Creates a fresh copy of the base graph and clears custom constants.
        """
        from ucon.graph import get_default_graph
        base = self._base_graph or get_default_graph()
        self._graph = base.copy()
        self._constants = {}

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.contexts
=============

Cross-dimensional conversion contexts for physical relationships.

A :class:`ConversionContext` bundles a set of cross-dimensional edges
(e.g., wavelength <-> frequency via *c*, or temperature <-> energy via *k_B*).
These edges are only active within a ``using_context()`` block.

Built-in contexts
-----------------
- :data:`spectroscopy` -- wavelength/frequency/energy via *c* and *h*
- :data:`boltzmann` -- temperature/energy via *k_B*

Examples
--------
>>> from ucon import units
>>> from ucon.contexts import spectroscopy, using_context
>>> with using_context(spectroscopy):
...     result = units.meter(500e-9).to(units.hertz)
...     print(f"{result.quantity:.3e} Hz")
5.996e+14 Hz
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Union

from ucon import units
from ucon.core import Unit, UnitProduct
from ucon.graph import get_default_graph, using_graph
from ucon.maps import Map, LinearMap, ReciprocalMap


@dataclass(frozen=True)
class ContextEdge:
    """A single cross-dimensional edge specification.

    Parameters
    ----------
    src : Unit or UnitProduct
        Source unit expression.
    dst : Unit or UnitProduct
        Destination unit expression.
    map : Map
        Conversion morphism from src to dst.
    """
    src: Union[Unit, UnitProduct]
    dst: Union[Unit, UnitProduct]
    map: Map


@dataclass(frozen=True)
class ConversionContext:
    """An immutable bundle of cross-dimensional conversion edges.

    Contexts are activated via :func:`using_context`, which copies
    the current graph, inserts the context edges, and scopes the
    copy for the duration of the ``with`` block.

    Parameters
    ----------
    name : str
        Human-readable name (e.g., "spectroscopy").
    edges : tuple[ContextEdge, ...]
        The cross-dimensional edge specifications.
    description : str
        Optional description of the physical basis.
    """
    name: str
    edges: tuple[ContextEdge, ...]
    description: str = ""


@contextmanager
def using_context(*contexts: ConversionContext):
    """Activate one or more conversion contexts.

    Creates a copy of the current graph, inserts all context edges,
    and scopes the extended graph via ``using_graph()``.

    Parameters
    ----------
    *contexts : ConversionContext
        One or more contexts to activate.

    Yields
    ------
    ConversionGraph
        The extended graph with context edges.

    Examples
    --------
    >>> with using_context(spectroscopy):
    ...     result = units.meter(500e-9).to(units.hertz)

    >>> with using_context(spectroscopy, boltzmann):
    ...     result = units.kelvin(300).to(units.joule)
    """
    extended = get_default_graph().copy()
    for ctx in contexts:
        for edge in ctx.edges:
            _add_context_edge(extended, edge)
    with using_graph(extended) as g:
        yield g


def _add_context_edge(graph, edge: ContextEdge) -> None:
    """Insert a context edge into both dimension partitions.

    Cross-dimensional edges need to be visible from BFS starting
    in either the source or destination dimension partition.
    """
    src = edge.src
    dst = edge.dst

    # Get the dimension for each side
    src_dim = src.dimension
    dst_dim = dst.dimension

    # Store in source's dimension partition
    graph._ensure_dimension(src_dim)
    graph._unit_edges[src_dim].setdefault(src, {})[dst] = edge.map

    # Store in destination's dimension partition (inverse)
    graph._ensure_dimension(dst_dim)
    graph._unit_edges[dst_dim].setdefault(dst, {})[src] = edge.map.inverse()


# ---------------------------------------------------------------------------
# Built-in contexts
# ---------------------------------------------------------------------------

def _build_spectroscopy() -> ConversionContext:
    """Build the spectroscopy context (c, h, hc relationships)."""

    c = 299792458.0             # m/s (exact)
    h = 6.62607015e-34          # J*s (exact)
    hc = c * h                  # J*m

    return ConversionContext(
        name="spectroscopy",
        edges=(
            # f = c / lambda  (frequency from wavelength)
            ContextEdge(
                src=units.meter,
                dst=units.hertz,
                map=ReciprocalMap(c),
            ),
            # E = h * f  (energy from frequency)
            ContextEdge(
                src=units.hertz,
                dst=units.joule,
                map=LinearMap(h),
            ),
            # E = hc / lambda  (energy from wavelength)
            ContextEdge(
                src=units.meter,
                dst=units.joule,
                map=ReciprocalMap(hc),
            ),
            # k = E / (hc)  (wavenumber from energy)
            ContextEdge(
                src=units.joule,
                dst=units.reciprocal_meter,
                map=LinearMap(1.0 / hc),
            ),
        ),
        description="Spectroscopy: wavelength/frequency/energy via c and h.",
    )


def _build_boltzmann() -> ConversionContext:
    """Build the Boltzmann context (k_B relationship)."""

    k_B = 1.380649e-23  # J/K (exact)

    return ConversionContext(
        name="boltzmann",
        edges=(
            # E = k_B * T  (energy from temperature)
            ContextEdge(
                src=units.kelvin,
                dst=units.joule,
                map=LinearMap(k_B),
            ),
        ),
        description="Boltzmann: temperature/energy via k_B.",
    )


# Lazy singletons
_spectroscopy: ConversionContext | None = None
_boltzmann: ConversionContext | None = None


def __getattr__(name: str):
    global _spectroscopy, _boltzmann
    if name == "spectroscopy":
        if _spectroscopy is None:
            _spectroscopy = _build_spectroscopy()
        return _spectroscopy
    if name == "boltzmann":
        if _boltzmann is None:
            _boltzmann = _build_boltzmann()
        return _boltzmann
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'ContextEdge',
    'ConversionContext',
    'using_context',
    'spectroscopy',
    'boltzmann',
]

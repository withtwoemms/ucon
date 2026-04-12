# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon._loader
=============

Central TOML loader with single-load caching.

Parses ``comprehensive.ucon.toml`` exactly once and provides shared
access to the resulting :class:`ConversionGraph`, units, and constants.
All consumers receive the same object instances, guaranteeing identity::

    from ucon._loader import get_units, get_graph
    assert get_units()["meter"] is get_graph()._name_registry_cs["meter"]
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ucon.constants import Constant
    from ucon.core import Unit
    from ucon.graph import ConversionGraph

_cache: dict = {}


def _ensure_loaded() -> None:
    """Parse the TOML once and populate the cache."""
    if _cache:
        return

    from ucon.serialization import from_toml

    path = Path(__file__).parent / "comprehensive.ucon.toml"
    graph = from_toml(path)

    # Extract units by canonical name (case-sensitive registry)
    units: dict[str, Unit] = {}
    for name, unit in graph._name_registry_cs.items():
        # Use the canonical name (unit.name), skip alias entries
        if name == unit.name:
            units[name] = unit

    # Extract constants keyed by symbol, aliases, and descriptive name
    constants: dict[str, Constant] = {}
    for const in graph._package_constants:
        constants[const.symbol] = const
        # Canonical name derived from full name (e.g., "speed_of_light_in_vacuum")
        safe_name = const.name.replace(" ", "_").replace("-", "_").lower()
        constants[safe_name] = const
        # Register all aliases (e.g., "speed_of_light", "Eh", "hbar")
        for alias in getattr(const, 'aliases', ()):
            constants[alias] = const

    _cache['graph'] = graph
    _cache['units'] = units
    _cache['constants'] = constants


def get_graph() -> ConversionGraph:
    """Return the default ConversionGraph loaded from TOML."""
    _ensure_loaded()
    return _cache['graph']


def get_units() -> dict[str, Unit]:
    """Return all units keyed by canonical name."""
    _ensure_loaded()
    return _cache['units']


def get_constants() -> dict[str, Constant]:
    """Return all constants keyed by symbol and descriptive name."""
    _ensure_loaded()
    return _cache['constants']


def reset() -> None:
    """Clear the cache (for testing)."""
    _cache.clear()

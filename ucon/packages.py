# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.packages
=============

UnitPackage loading and composition for domain-specific unit extensions.

This module provides the infrastructure for defining custom units and
conversions in TOML config files that can be loaded at application startup.

Classes
-------
- :class:`UnitDef` — Serializable unit definition.
- :class:`EdgeDef` — Serializable conversion edge definition.
- :class:`UnitPackage` — Immutable bundle of units and conversions.

Functions
---------
- :func:`load_package` — Load a UnitPackage from a TOML file.

Exceptions
----------
- :class:`PackageLoadError` — Raised when package loading fails.

Example
-------
>>> from ucon.packages import load_package
>>> from ucon import get_default_graph
>>>
>>> aero = load_package("aerospace.ucon.toml")
>>> graph = get_default_graph().with_package(aero)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import ast
import operator

from ucon.core import Unit, UnknownUnitError
from ucon.dimension import Dimension, all_dimensions
from ucon.maps import AffineMap, LinearMap

if TYPE_CHECKING:
    from ucon.graph import ConversionGraph


def _parse_factor(value) -> float:
    """Parse a factor value from TOML.

    Accepts either a numeric value (int/float) or an arithmetic expression
    string containing integers, ``/``, and ``*``.  This allows TOML files
    to express exact ratios like ``"1852 / 3600"`` instead of truncated
    decimals like ``0.514444``.

    Parameters
    ----------
    value : int, float, or str
        The factor as a number or arithmetic expression.

    Returns
    -------
    float
        The evaluated factor.

    Raises
    ------
    PackageLoadError
        If the string is not a valid arithmetic expression.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        raise PackageLoadError(f"factor must be a number or expression string, got {type(value).__name__}")

    _OPS = {
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if hasattr(ast, 'Num') and isinstance(node, ast.Num):  # Python 3.7 compat
            return float(node.n)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval_node(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        raise PackageLoadError(
            f"Unsupported expression in factor: {value!r}. "
            "Only numeric literals with * and / are allowed."
        )

    try:
        tree = ast.parse(value.strip(), mode='eval')
        return _eval_node(tree)
    except SyntaxError:
        raise PackageLoadError(f"Invalid factor expression: {value!r}")


def _get_dimension_map() -> dict[str, Dimension]:
    """Build a mapping from dimension names to Dimension objects."""
    return {d.name: d for d in all_dimensions() if d.name is not None}


class PackageLoadError(Exception):
    """Raised when a package file cannot be loaded or validated."""
    pass


@dataclass(frozen=True)
class UnitDef:
    """Serializable unit definition.

    Attributes
    ----------
    name : str
        Canonical name of the unit (e.g., "slug").
    dimension : str
        Dimension enum name (e.g., "mass", "length").
    aliases : tuple[str, ...]
        Optional shorthand symbols (e.g., ("slug",)).
    """
    name: str
    dimension: str
    aliases: tuple[str, ...] = ()

    def materialize(self) -> Unit:
        """Convert to a Unit object.

        Returns
        -------
        Unit
            A new Unit instance.

        Raises
        ------
        PackageLoadError
            If the dimension name is invalid.
        """
        dim_map = _get_dimension_map()
        dim = dim_map.get(self.dimension)
        if dim is None:
            raise PackageLoadError(
                f"Unknown dimension '{self.dimension}' for unit '{self.name}'"
            )

        return Unit(
            name=self.name,
            dimension=dim,
            aliases=self.aliases,
        )


@dataclass(frozen=True)
class EdgeDef:
    """Serializable conversion edge definition.

    Attributes
    ----------
    src : str
        Source unit name or composite expression.
    dst : str
        Destination unit name or composite expression.
    factor : float
        Multiplier (dst = factor * src + offset).
    offset : float
        Additive offset for affine conversions (default 0.0).
        When non-zero, an AffineMap is used instead of LinearMap.
    """
    src: str
    dst: str
    factor: float
    offset: float = 0.0

    def materialize(self, graph: 'ConversionGraph'):
        """Resolve units and add edge to graph.

        Parameters
        ----------
        graph : ConversionGraph
            The graph to add the edge to. Units are resolved
            using the graph's name registry.

        Raises
        ------
        PackageLoadError
            If source or destination unit cannot be resolved.
        """
        # Resolve units within graph context
        from ucon.resolver import get_unit_by_name
        from ucon.graph import using_graph
        with using_graph(graph):
            try:
                src_unit = get_unit_by_name(self.src)
            except UnknownUnitError:
                raise PackageLoadError(
                    f"Cannot resolve source unit '{self.src}' in edge"
                )

            try:
                dst_unit = get_unit_by_name(self.dst)
            except UnknownUnitError:
                raise PackageLoadError(
                    f"Cannot resolve destination unit '{self.dst}' in edge"
                )

        if self.offset != 0.0:
            graph.add_edge(src=src_unit, dst=dst_unit, map=AffineMap(self.factor, self.offset))
        else:
            graph.add_edge(src=src_unit, dst=dst_unit, map=LinearMap(self.factor))


@dataclass(frozen=True)
class UnitPackage:
    """Immutable bundle of domain-specific units and conversions.

    Attributes
    ----------
    name : str
        Package name (e.g., "aerospace").
    version : str
        Semantic version string (e.g., "1.0.0").
    description : str
        Human-readable description.
    units : tuple[UnitDef, ...]
        Unit definitions.
    edges : tuple[EdgeDef, ...]
        Conversion edge definitions.
    requires : tuple[str, ...]
        Names of required packages (for future dependency resolution).
    """
    name: str
    version: str = "1.0.0"
    description: str = ""
    units: tuple[UnitDef, ...] = ()
    edges: tuple[EdgeDef, ...] = ()
    requires: tuple[str, ...] = ()

    def __post_init__(self):
        """Validate package contents."""
        dim_map = _get_dimension_map()

        # Validate dimension names
        for unit_def in self.units:
            if unit_def.dimension not in dim_map:
                raise PackageLoadError(
                    f"Unknown dimension '{unit_def.dimension}' for unit '{unit_def.name}'"
                )


def load_package(path: str | Path) -> UnitPackage:
    """Load a UnitPackage from a TOML file.

    Parameters
    ----------
    path : str or Path
        Path to a .toml or .ucon.toml file.

    Returns
    -------
    UnitPackage
        Frozen package ready for use with ConversionGraph.with_package().

    Raises
    ------
    PackageLoadError
        If file cannot be read or contains invalid definitions.

    Example
    -------
    >>> pkg = load_package("aerospace.ucon.toml")
    >>> print(pkg.name, pkg.version)
    aerospace 1.0.0
    """
    path = Path(path)

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise PackageLoadError(f"Package file not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise PackageLoadError(f"Invalid TOML in {path}: {e}")

    # Parse units
    units = tuple(
        UnitDef(
            name=u["name"],
            dimension=u["dimension"],
            aliases=tuple(u.get("aliases", ())),
        )
        for u in data.get("units", [])
    )

    # Parse edges (factor supports arithmetic expressions like "1852 / 3600")
    edges = tuple(
        EdgeDef(
            src=e["src"],
            dst=e["dst"],
            factor=_parse_factor(e["factor"]),
            offset=_parse_factor(e.get("offset", 0.0)),
        )
        for e in data.get("edges", [])
    )

    return UnitPackage(
        name=data.get("name", path.stem),
        version=data.get("version", "1.0.0"),
        description=data.get("description", ""),
        units=units,
        edges=edges,
        requires=tuple(data.get("requires", [])),
    )


__all__ = [
    'EdgeDef',
    'PackageLoadError',
    'UnitDef',
    'UnitPackage',
    'load_package',
]

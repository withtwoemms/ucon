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
- :class:`ConstantDef` — Serializable constant definition.
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

from ucon.constants import Constant
from ucon.core import Unit, UnknownUnitError
from ucon.dimension import Dimension, all_dimensions
from ucon.maps import AffineMap, LinearMap, LogMap, Map, ReciprocalMap

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
    shorthand : str | None
        Explicit display symbol (e.g., "nmi"). When provided, this is
        prepended to aliases so it becomes ``Unit.shorthand``. When
        ``None``, the first alias (or name) is used as before.
    """
    name: str
    dimension: str
    aliases: tuple[str, ...] = ()
    shorthand: str | None = None

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

        aliases = self.aliases
        if self.shorthand is not None and self.shorthand not in aliases:
            aliases = (self.shorthand,) + aliases

        return Unit(
            name=self.name,
            dimension=dim,
            aliases=aliases,
        )


_MAP_TYPES: dict[str, type[Map]] = {
    'linear': LinearMap,
    'affine': AffineMap,
    'log': LogMap,
    'reciprocal': ReciprocalMap,
}


def _build_map(map_spec: dict) -> Map:
    """Build a Map from a TOML inline table specification.

    Parameters
    ----------
    map_spec : dict
        Must contain a ``type`` key selecting the map class.
        Remaining keys are passed as constructor arguments.

    Returns
    -------
    Map
        The constructed map instance.

    Raises
    ------
    PackageLoadError
        If the type is unknown or constructor arguments are invalid.
    """
    spec = dict(map_spec)  # Shallow copy to pop from
    map_type = spec.pop('type', None)
    if map_type is None:
        raise PackageLoadError("Edge 'map' requires a 'type' key")

    cls = _MAP_TYPES.get(map_type)
    if cls is None:
        raise PackageLoadError(
            f"Unknown map type '{map_type}'. "
            f"Valid types: {', '.join(sorted(_MAP_TYPES))}"
        )

    try:
        return cls(**spec)
    except TypeError as e:
        raise PackageLoadError(
            f"Invalid parameters for {map_type} map: {e}"
        )


@dataclass(frozen=True)
class EdgeDef:
    """Serializable conversion edge definition.

    Edges can be specified in two ways:

    **Shorthand** (linear/affine): uses ``factor`` and optional ``offset``.

    **Explicit map**: uses ``map_spec`` dict with a ``type`` key and
    constructor parameters. Supported types: ``linear``, ``affine``,
    ``log``, ``reciprocal``.

    When ``map_spec`` is provided, it takes precedence over
    ``factor``/``offset``.

    Attributes
    ----------
    src : str
        Source unit name or composite expression.
    dst : str
        Destination unit name or composite expression.
    factor : float
        Multiplier (dst = factor * src + offset). Ignored when
        ``map_spec`` is provided.
    offset : float
        Additive offset for affine conversions (default 0.0).
        Ignored when ``map_spec`` is provided.
    map_spec : dict | None
        Explicit map specification. When provided, must contain a
        ``type`` key (``"linear"``, ``"affine"``, ``"log"``,
        ``"reciprocal"``). Remaining keys are constructor arguments.
    """
    src: str
    dst: str
    factor: float = 1.0
    offset: float = 0.0
    map_spec: dict | None = None

    def _build_edge_map(self) -> Map:
        """Build the Map for this edge.

        Returns
        -------
        Map
            A LinearMap, AffineMap, LogMap, or ReciprocalMap.
        """
        if self.map_spec is not None:
            return _build_map(self.map_spec)

        if self.offset != 0.0:
            return AffineMap(self.factor, self.offset)
        return LinearMap(self.factor)

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

        graph.add_edge(src=src_unit, dst=dst_unit, map=self._build_edge_map())


@dataclass(frozen=True)
class ConstantDef:
    """Serializable constant definition.

    Attributes
    ----------
    symbol : str
        Standard symbol (e.g., "vs", "Eg").
    name : str
        Full descriptive name (e.g., "speed of sound in dry air at 20C").
    value : float
        Numeric value in the specified unit.
    unit : str
        Unit expression string (e.g., "m/s", "J", "kg*m/s^2").
        Resolved via ``get_unit_by_name()`` during materialization.
    uncertainty : float | None
        Standard uncertainty. None for exact values.
    source : str
        Data source reference.
    category : str
        Category: "exact", "derived", "measured", or "session".
    """
    symbol: str
    name: str
    value: float
    unit: str
    uncertainty: float | None = None
    source: str = "user-defined"
    category: str = "session"

    def materialize(self, graph: 'ConversionGraph') -> Constant:
        """Resolve unit string and create a Constant.

        Parameters
        ----------
        graph : ConversionGraph
            The graph to resolve unit names against.

        Returns
        -------
        Constant
            A new Constant instance.

        Raises
        ------
        PackageLoadError
            If the unit string cannot be resolved.
        """
        from ucon.resolver import get_unit_by_name
        from ucon.graph import using_graph
        with using_graph(graph):
            try:
                resolved_unit = get_unit_by_name(self.unit)
            except UnknownUnitError:
                raise PackageLoadError(
                    f"Cannot resolve unit '{self.unit}' for constant '{self.symbol}'"
                )

        return Constant(
            symbol=self.symbol,
            name=self.name,
            value=self.value,
            unit=resolved_unit,
            uncertainty=self.uncertainty,
            source=self.source,
            category=self.category,
        )


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
    constants : tuple[ConstantDef, ...]
        Constant definitions.
    requires : tuple[str, ...]
        Names of required packages (for future dependency resolution).
    """
    name: str
    version: str = "1.0.0"
    description: str = ""
    units: tuple[UnitDef, ...] = ()
    edges: tuple[EdgeDef, ...] = ()
    constants: tuple[ConstantDef, ...] = ()
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
            shorthand=u.get("shorthand"),
        )
        for u in data.get("units", [])
    )

    # Parse edges
    # Supports two forms:
    #   factor/offset shorthand: { src, dst, factor, offset? }
    #   explicit map: { src, dst, map = { type, ...params } }
    def _parse_edge(e: dict) -> EdgeDef:
        map_spec = e.get("map")
        if map_spec is not None:
            return EdgeDef(
                src=e["src"],
                dst=e["dst"],
                map_spec=dict(map_spec),
            )
        return EdgeDef(
            src=e["src"],
            dst=e["dst"],
            factor=_parse_factor(e["factor"]),
            offset=_parse_factor(e.get("offset", 0.0)),
        )

    edges = tuple(_parse_edge(e) for e in data.get("edges", []))

    # Parse constants
    constants = tuple(
        ConstantDef(
            symbol=c["symbol"],
            name=c["name"],
            value=float(c["value"]),
            unit=c["unit"],
            uncertainty=c.get("uncertainty"),
            source=c.get("source", "user-defined"),
            category=c.get("category", "session"),
        )
        for c in data.get("constants", [])
    )

    # Support both [package] table (preferred) and top-level keys (legacy)
    package = data.get("package", {})
    if not package and any(k in data for k in ("name", "version", "description")):
        import warnings
        warnings.warn(
            f"Package metadata as top-level keys is deprecated. "
            f"Wrap in a [package] table in {path.name}. "
            f"Legacy format will be removed in ucon 2.0.",
            DeprecationWarning,
            stacklevel=2,
        )

    return UnitPackage(
        name=package.get("name", data.get("name", path.stem)),
        version=package.get("version", data.get("version", "1.0.0")),
        description=package.get("description", data.get("description", "")),
        units=units,
        edges=edges,
        constants=constants,
        requires=tuple(package.get("requires", data.get("requires", []))),
    )


__all__ = [
    'ConstantDef',
    'EdgeDef',
    'PackageLoadError',
    'UnitDef',
    'UnitPackage',
    'load_package',
]

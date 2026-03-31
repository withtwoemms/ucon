# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.resolver
=============

Resolves unit strings into :class:`~ucon.core.Unit` and
:class:`~ucon.core.UnitProduct` objects.

Handles plain names (``"meter"``), aliases (``"m"``),
SI-prefix decomposition (``"km"``), exponents (``"m²"``),
and composite expressions (``"kg*m/s^2"``).

The global registries are populated at import time by
:mod:`ucon.units`, which calls :func:`register_unit` for
every canonical unit it defines.

Functions
---------
- :func:`get_unit_by_name` — Public resolver (string → Unit | UnitProduct).
- :func:`register_unit` — Register a unit (name + aliases) in the global lookup.
- :func:`register_priority_scaled_alias` — Register a scaled alias (e.g. "mcg").
"""
from __future__ import annotations

import re
from typing import Dict, Tuple, Union

from ucon.core import (
    Scale,
    Unit,
    UnitFactor,
    UnitProduct,
    UnknownUnitError,
    _get_parsing_graph,
)
from ucon.parsing import parse_unit_expression, ParseError


# ---------------------------------------------------------------------------
# Global registries (populated by ucon.units at import time)
# ---------------------------------------------------------------------------

_UNIT_REGISTRY: Dict[str, Unit] = {}
_UNIT_REGISTRY_CASE_SENSITIVE: Dict[str, Unit] = {}

# ---------------------------------------------------------------------------
# Priority Alias Invariant (for contributors)
# ---------------------------------------------------------------------------
#
# When a unit alias could be misinterpreted as a scale prefix + unit symbol,
# add it to _PRIORITY_ALIASES or _PRIORITY_SCALED_ALIASES to prevent ambiguity.
#
# Examples:
#   - "min" could parse as milli-inch (m + in), but should be minute
#   - "mcg" could fail (no "mc" prefix), but should be microgram
#   - "cc" could fail, but should be cubic centimeter (cm³)
#
# Rule: If a unit string starts with a valid scale prefix AND the remainder
# is a valid unit symbol, check whether the whole string should be treated
# as a single unit. If so, add it to:
#
#   _PRIORITY_ALIASES - for unscaled units (e.g., "min" -> minute)
#   _PRIORITY_SCALED_ALIASES - for scaled units (e.g., "mcg" -> microgram)
#
# The parser checks these sets BEFORE attempting prefix decomposition.
# ---------------------------------------------------------------------------

# Priority aliases that must match exactly before prefix decomposition.
# Prevents ambiguous parses like "min" -> milli-inch instead of minute.
_PRIORITY_ALIASES: set = {'min', 'ft', 'ft_lb', 'ft_lbf'}

# Priority scaled aliases that map to a specific (unit, scale) tuple.
# Used for medical conventions like "mcg" -> (gram, Scale.micro).
_PRIORITY_SCALED_ALIASES: Dict[str, Tuple[Unit, Scale]] = {}

# Scale prefix mapping (shorthand -> Scale)
# Derived from Scale enum's ScaleDescriptor.shorthand, plus input-only aliases
_SCALE_PREFIXES: Dict[str, Scale] = {
    s.shorthand: s for s in Scale if s.shorthand
}

# Additional input aliases not in canonical ScaleDescriptor.shorthand
_SCALE_PREFIXES.update({
    'u': Scale.micro,  # ASCII alternative for µ
    'μ': Scale.micro,  # Unicode MICRO SIGN (U+00B5)
    # Note: Scale.micro.shorthand is 'µ' (GREEK SMALL LETTER MU, U+03BC)
})

# Sorted by length descending for greedy prefix matching
_SCALE_PREFIXES_SORTED = sorted(_SCALE_PREFIXES.keys(), key=len, reverse=True)

# Unicode superscript translation table
_SUPERSCRIPT_TO_DIGIT = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻', '0123456789-')


# ---------------------------------------------------------------------------
# Registration API
# ---------------------------------------------------------------------------

def register_unit(unit: Unit) -> None:
    """Register a unit in the global lookup tables.

    Registers the unit's canonical name and all aliases in both the
    case-insensitive and case-sensitive registries.

    Parameters
    ----------
    unit : Unit
        The unit to register. Must have a non-empty ``name``.
    """
    if not unit.name:
        return
    _UNIT_REGISTRY[unit.name.lower()] = unit
    _UNIT_REGISTRY_CASE_SENSITIVE[unit.name] = unit
    for alias in unit.aliases:
        if alias:
            _UNIT_REGISTRY[alias.lower()] = unit
            _UNIT_REGISTRY_CASE_SENSITIVE[alias] = unit


def register_priority_scaled_alias(alias: str, unit: Unit, scale: Scale) -> None:
    """Register a priority scaled alias.

    Priority scaled aliases are checked before prefix decomposition,
    e.g. ``"mcg"`` → ``(gram, Scale.micro)`` rather than trying to
    parse as a prefix + unit.

    Parameters
    ----------
    alias : str
        The alias string (e.g. ``"mcg"``).
    unit : Unit
        The target unit (e.g. ``gram``).
    scale : Scale
        The scale to apply (e.g. ``Scale.micro``).
    """
    _PRIORITY_SCALED_ALIASES[alias] = (unit, scale)


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

def _parse_exponent(s: str) -> Tuple[str, float]:
    """
    Extract exponent from unit factor string.

    Handles both formats:
    - Unicode: 'm²' -> ('m', 2.0), 's⁻¹' -> ('s', -1.0)
    - ASCII:  'm^2' -> ('m', 2.0), 's^-1' -> ('s', -1.0)

    Returns:
        Tuple of (base_unit_str, exponent) where exponent defaults to 1.0.
    """
    # Try ASCII caret notation first: "m^2", "s^-1"
    if '^' in s:
        base, exp_str = s.rsplit('^', 1)
        try:
            return base.strip(), float(exp_str)
        except ValueError:
            raise UnknownUnitError(s)

    # Try Unicode superscripts: "m²", "s⁻¹"
    match = re.search(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+$', s)
    if match:
        base = s[:match.start()]
        exp_str = match.group().translate(_SUPERSCRIPT_TO_DIGIT)
        try:
            return base, float(exp_str)
        except ValueError:
            raise UnknownUnitError(s)

    # No exponent found
    return s, 1.0


def _lookup_factor(s: str) -> Tuple[Unit, Scale]:
    """
    Look up a single unit factor, handling scale prefixes.

    Checks graph-local registry first (if within a using_graph() context),
    then falls back to the global registry.

    Prioritizes prefix+unit interpretation over direct unit lookup,
    except for priority aliases (like 'min', 'mcg') which are checked first
    to avoid ambiguous parses or to handle domain-specific conventions.

    This means "kg" returns (gram, Scale.kilo) rather than (kilogram, Scale.one).

    Examples:
    - 'meter' -> (meter, Scale.one)
    - 'm' -> (meter, Scale.one)
    - 'km' -> (meter, Scale.kilo)
    - 'kg' -> (gram, Scale.kilo)
    - 'mL' -> (liter, Scale.milli)
    - 'min' -> (minute, Scale.one)  # priority alias, not milli-inch
    - 'mcg' -> (gram, Scale.micro)  # medical convention for microgram

    Returns:
        Tuple of (unit, scale).

    Raises:
        UnknownUnitError: If the unit cannot be resolved.
    """
    # Check graph-local registry first (if in using_graph() context)
    graph = _get_parsing_graph()
    if graph is not None:
        result = graph.resolve_unit(s)
        if result is not None:
            return result

    # Check priority scaled aliases first (e.g., "mcg" -> microgram)
    if s in _PRIORITY_SCALED_ALIASES:
        return _PRIORITY_SCALED_ALIASES[s]

    # Check priority aliases (prevents "min" -> milli-inch)
    if s in _PRIORITY_ALIASES:
        if s in _UNIT_REGISTRY_CASE_SENSITIVE:
            return _UNIT_REGISTRY_CASE_SENSITIVE[s], Scale.one
        s_lower = s.lower()
        if s_lower in _UNIT_REGISTRY:
            return _UNIT_REGISTRY[s_lower], Scale.one

    # Try scale prefix + unit (prioritize decomposition)
    # Only case-sensitive matching for remainder (e.g., "fT" = femto-tesla, "ft" = foot)
    for prefix in _SCALE_PREFIXES_SORTED:
        if s.startswith(prefix) and len(s) > len(prefix):
            remainder = s[len(prefix):]
            if remainder in _UNIT_REGISTRY_CASE_SENSITIVE:
                return _UNIT_REGISTRY_CASE_SENSITIVE[remainder], _SCALE_PREFIXES[prefix]

    # Fall back to exact case-sensitive match (for aliases like 'L', 'B', 'm')
    if s in _UNIT_REGISTRY_CASE_SENSITIVE:
        return _UNIT_REGISTRY_CASE_SENSITIVE[s], Scale.one

    # Fall back to case-insensitive match
    s_lower = s.lower()
    if s_lower in _UNIT_REGISTRY:
        return _UNIT_REGISTRY[s_lower], Scale.one

    raise UnknownUnitError(s)


def _parse_composite(s: str) -> UnitProduct:
    """
    Parse composite unit string into UnitProduct using recursive descent.

    Accepts both Unicode and ASCII notation:
    - Unicode: 'm/s²', 'kg·m/s²', 'N·m', 'W/(m²*K)'
    - ASCII:  'm/s^2', 'kg*m/s^2', 'N*m', 'W/(m^2*K)'

    Supports:
    - Parentheses: `W/(m²*K)`, `(kg*m)/(s^2)`
    - Chained division: `mg/kg/d`
    - Unicode superscripts: `⁰¹²³⁴⁵⁶⁷⁸⁹⁻`
    - ASCII exponents: `^2`, `^-1`

    Returns:
        UnitProduct representing the parsed composite unit.

    Raises:
        ParseError: If the expression is malformed (e.g., unbalanced parens).
        UnknownUnitError: If a unit name cannot be resolved.
    """
    return parse_unit_expression(s, _lookup_factor, UnitFactor, UnitProduct)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_unit_by_name(name: str) -> Union[Unit, UnitProduct]:
    """
    Look up a unit by name, alias, or shorthand.

    Handles:
    - Plain units: "meter", "m", "second", "s"
    - Scaled units: "km", "mL", "kg"
    - Composite units: "m/s", "kg*m/s^2", "N·m"
    - Exponents: "m²", "m^2", "s⁻¹", "s^-1"

    Args:
        name: Unit string to parse.

    Returns:
        Unit for simple unscaled units, UnitProduct for scaled or composite.

    Raises:
        UnknownUnitError: If the unit cannot be resolved.

    Examples:
        >>> get_unit_by_name("meter")
        <Unit m>
        >>> get_unit_by_name("km")
        <UnitProduct km>
        >>> get_unit_by_name("m/s^2")
        <UnitProduct m/s²>
    """
    if not name or not name.strip():
        raise UnknownUnitError(name if name else "")

    name = name.strip()

    # Check for composite (has operators or parentheses)
    # Note: · (U+00B7 middle dot) and ⋅ (U+22C5 dot operator) are both multiplication
    if '/' in name or '·' in name or '⋅' in name or '*' in name or '(' in name:
        return _parse_composite(name)

    # Check for exponent
    base_str, exp = _parse_exponent(name)
    if exp != 1.0:
        unit, scale = _lookup_factor(base_str)
        return UnitProduct({UnitFactor(unit, scale): exp})

    # Simple unit or scaled unit
    unit, scale = _lookup_factor(name)
    if scale == Scale.one:
        return unit
    else:
        return UnitProduct({UnitFactor(unit, scale): 1})


__all__ = [
    'get_unit_by_name',
    'register_unit',
    'register_priority_scaled_alias',
]

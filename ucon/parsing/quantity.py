# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.parsing.quantity
=====================

Quantity string parser — converts strings like ``"60 mph"`` or
``"1.234 ± 0.005 m"`` into :class:`~ucon.core.quantity.Number` objects.

Separated from :mod:`ucon.parsing.units` so that the ``parse()`` function
can import :func:`~ucon.resolver.parse_unit` at top level without
creating an import cycle (``resolver`` imports ``parse_unit_expression``
from ``ucon.parsing.units``).
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ucon.core import Number, UnknownUnitError  # noqa: F401 — UnknownUnitError re-export
from ucon.resolver import parse_unit

if TYPE_CHECKING:
    from ucon.system import UnitSystem


# Regex for quantity parsing
# Matches: optional sign, number (int/float/scientific), optional uncertainty, unit
_QUANTITY_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<value>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)  # numeric value
    \s*
    (?:
        (?:±|\+/-)\s*(?P<uncertainty>\d+\.?\d*(?:[eE][+-]?\d+)?)  # ± uncertainty
        |
        \((?P<paren_unc>\d+)\)  # parenthetical uncertainty
    )?
    \s*
    (?P<unit>.*)  # unit string (may be empty)
    $
    """,
    re.VERBOSE
)

# Pattern for uncertainty with unit: "1.234 m ± 0.005 m"
_UNCERTAINTY_WITH_UNIT_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<value>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)  # numeric value
    \s+
    (?P<unit1>[^\s±]+(?:\s*/\s*[^\s±]+)*)  # unit (with possible division)
    \s*
    (?:±|\+/-)\s*
    (?P<uncertainty>\d+\.?\d*(?:[eE][+-]?\d+)?)  # uncertainty value
    \s+
    (?P<unit2>.+)  # second unit (should match first)
    $
    """,
    re.VERBOSE
)


def parse(s: str, *, system: "UnitSystem | None" = None) -> 'Number':
    """Parse a quantity string into a Number.

    Supports various formats:
    - Basic quantities: "60 mph", "9.81 m/s^2", "1.5 kg"
    - Pure numbers: "100", "3.14159" (returns dimensionless Number)
    - Scientific notation: "1.5e3 m", "6.022e23"
    - Negative values: "-273.15 °C"
    - Uncertainty with ±: "1.234 ± 0.005 m"
    - Uncertainty with +/-: "1.234 +/- 0.005 m"
    - Parenthetical uncertainty: "1.234(5) m" (means 1.234 ± 0.005)
    - Uncertainty with unit: "1.234 m ± 0.005 m"

    The function respects context from using_graph() for unit resolution.

    Args:
        s: The quantity string to parse.
        system: Optional :class:`~ucon.system.UnitSystem` threaded through
            to :func:`~ucon.resolver.parse_unit`.

    Returns:
        A Number representing the parsed quantity.

    Raises:
        ValueError: If the string cannot be parsed.
        UnknownUnitError: If the unit cannot be resolved.

    Examples:
        >>> parse("60 mph")
        <60 mph>
        >>> parse("1.234 ± 0.005 m")
        <1.234 ± 0.005 m>
        >>> parse("9.81 m/s^2")
        <9.81 m/s²>
        >>> parse("100")
        <100>
    """
    if not s or not s.strip():
        raise ValueError("Cannot parse empty string")

    s = s.strip()

    # Try "value unit ± uncertainty unit" format first
    unc_with_unit = _UNCERTAINTY_WITH_UNIT_PATTERN.match(s)
    if unc_with_unit:
        value = float(unc_with_unit.group("value"))
        unit_str = unc_with_unit.group("unit1").strip()
        uncertainty = float(unc_with_unit.group("uncertainty"))

        unit = parse_unit(unit_str, system=system)
        return Number(quantity=value, unit=unit, uncertainty=uncertainty)

    # Standard quantity pattern
    match = _QUANTITY_PATTERN.match(s)
    if not match:
        raise ValueError(f"Cannot parse quantity: {s!r}")

    value_str = match.group("value")
    unit_str = match.group("unit").strip() if match.group("unit") else ""

    # Validate numeric value
    try:
        value = float(value_str)
    except ValueError:
        raise ValueError(f"Invalid numeric value: {value_str!r}")

    # Handle uncertainty
    uncertainty = None
    if match.group("uncertainty"):
        uncertainty = float(match.group("uncertainty"))
    elif match.group("paren_unc"):
        # Parenthetical: "1.234(5)" means 1.234 ± 0.005
        paren = match.group("paren_unc")
        # Determine scale from decimal places in value
        if "." in value_str:
            # Count decimal places (excluding trailing exponent)
            base_value = value_str.split('e')[0].split('E')[0]
            decimal_part = base_value.split(".")[1] if "." in base_value else ""
            decimal_places = len(decimal_part)
            uncertainty = int(paren) * (10 ** -decimal_places)
        else:
            uncertainty = float(paren)

    # Parse unit (or return dimensionless)
    if unit_str:
        unit = parse_unit(unit_str, system=system)
    else:
        unit = None  # Number will use dimensionless default

    return Number(quantity=value, unit=unit, uncertainty=uncertainty)

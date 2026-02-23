# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Formula registry for MCP-exposed domain calculations.

Provides @register_formula decorator for registering dimensionally-typed
functions that can be discovered and called via MCP tools.
"""

from dataclasses import dataclass
from typing import Callable

from ucon.mcp.schema import extract_dimension_constraints


@dataclass(frozen=True)
class FormulaInfo:
    """Metadata about a registered formula.

    Attributes
    ----------
    name : str
        Unique identifier for the formula.
    description : str
        Human-readable description of what the formula calculates.
    parameters : dict[str, str | None]
        Mapping of parameter name to dimension name (None if unconstrained).
    fn : Callable
        The actual function to call.
    """
    name: str
    description: str
    parameters: dict[str, str | None]
    fn: Callable


# Module-level registry
_FORMULA_REGISTRY: dict[str, FormulaInfo] = {}


def register_formula(name: str, *, description: str = "") -> Callable[[Callable], Callable]:
    """Decorator to register a formula for MCP discovery.

    The decorated function should use Number[Dimension.X] type annotations
    for parameters that have dimensional constraints. These constraints are
    extracted and exposed in the formula's schema.

    Parameters
    ----------
    name : str
        Unique identifier for the formula (used in list_formulas, call_formula).
    description : str, optional
        Human-readable description of what the formula calculates.

    Returns
    -------
    Callable
        Decorator that registers the function and returns it unchanged.

    Examples
    --------
    >>> from ucon import Number, Dimension, enforce_dimensions
    >>> from ucon.mcp.formulas import register_formula
    >>>
    >>> @register_formula("bmi", description="Body Mass Index")
    ... @enforce_dimensions
    ... def bmi(mass: Number[Dimension.mass], height: Number[Dimension.length]) -> Number:
    ...     return mass / (height * height)

    Notes
    -----
    - Use with @enforce_dimensions to get runtime validation
    - The @register_formula decorator should be outermost (applied last)
    - Formula names must be unique; re-registering raises ValueError
    """
    def decorator(fn: Callable) -> Callable:
        if name in _FORMULA_REGISTRY:
            raise ValueError(f"Formula '{name}' is already registered")

        parameters = extract_dimension_constraints(fn)

        info = FormulaInfo(
            name=name,
            description=description,
            parameters=parameters,
            fn=fn,
        )
        _FORMULA_REGISTRY[name] = info

        return fn

    return decorator


def list_formulas() -> list[FormulaInfo]:
    """Return all registered formulas.

    Returns
    -------
    list[FormulaInfo]
        List of formula metadata, sorted by name.
    """
    return sorted(_FORMULA_REGISTRY.values(), key=lambda f: f.name)


def get_formula(name: str) -> FormulaInfo | None:
    """Look up a formula by name.

    Parameters
    ----------
    name : str
        The formula identifier.

    Returns
    -------
    FormulaInfo | None
        The formula info, or None if not found.
    """
    return _FORMULA_REGISTRY.get(name)


def clear_formulas() -> None:
    """Clear all registered formulas. Intended for testing."""
    _FORMULA_REGISTRY.clear()


__all__ = [
    'FormulaInfo',
    'register_formula',
    'list_formulas',
    'get_formula',
    'clear_formulas',
]

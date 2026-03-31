# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.quantity
=============

Value-layer types for representing measured quantities and ratios.

This module provides the numeric wrappers that pair a magnitude with a unit
expression, supporting dimensional arithmetic and conversion.

Classes
-------
- :class:`Number` — Numeric quantity with unit, scale, and optional uncertainty.
- :class:`Ratio` — Ratio of two Numbers preserving unit semantics.
- :class:`DimensionConstraint` — Annotation marker for ``Number[Dimension.X]`` syntax.

Type Aliases
------------
- ``_Quantifiable`` — Union of Number and Ratio.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Union

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from ucon.core import Unit, UnitProduct, UnitFactor, Scale
from ucon.dimension import Dimension, NONE
from ucon.graph import get_default_graph


# --------------------------------------------------------------------------------------
# Dependency Injection Hooks (wired by ucon.__init__)
# --------------------------------------------------------------------------------------

_get_unit_by_name = None  # (name: str) -> Unit | UnitProduct


# Dimensionless unit for use as default in Number
_none = Unit()


_Quantifiable = Union['Number', 'Ratio']


class DimensionConstraint:
    """Annotation marker: constrains a Number to a specific Dimension.

    Used with typing.Annotated to enable Number[TIME] syntax.
    The decorator @enforce_dimensions introspects this marker at runtime.
    """

    __slots__ = ("dimension",)

    def __init__(self, dim: Dimension):
        self.dimension = dim

    def __repr__(self) -> str:
        return f"DimensionConstraint({self.dimension.name})"

    def __eq__(self, other) -> bool:
        return isinstance(other, DimensionConstraint) and self.dimension == other.dimension

    def __hash__(self) -> int:
        return hash(("DimensionConstraint", self.dimension))


@dataclass
class Number:
    """
    Represents a **numeric quantity** with an associated :class:`Unit` and :class:`Scale`.

    Combines magnitude, unit, and scale into a single, composable object that
    supports dimensional arithmetic and conversion:

        >>> from ucon.units import meter, second
        >>> length = meter(5)
        >>> time = second(2)
        >>> speed = length / time
        >>> speed
        <2.5 m/s>

    Optionally includes measurement uncertainty for error propagation:

        >>> length = meter(1.234, uncertainty=0.005)
        >>> length
        <1.234 ± 0.005 m>
    """
    quantity: Union[float, int] = 1.0
    unit: Union[Unit, UnitProduct] = None
    uncertainty: Union[float, None] = None

    def __post_init__(self):
        if self.unit is None:
            object.__setattr__(self, 'unit', _none)

    def __class_getitem__(cls, dim):
        """Enable Number[Dimension.X] syntax for type annotations.

        Returns Annotated[Number, DimensionConstraint(dim)] for runtime introspection
        by @enforce_dimensions decorator.
        """
        if isinstance(dim, Dimension):
            return Annotated[cls, DimensionConstraint(dim)]
        return cls

    @property
    def value(self) -> float:
        """Return the numeric magnitude as-expressed (no scale folding).

        Scale lives in the unit expression (e.g. kJ, mL) and is NOT
        folded into the returned value.  Use ``unit.fold_scale()`` on a
        UnitProduct when you need the base-unit-equivalent magnitude.
        """
        return round(self.quantity, 15)

    @property
    def _canonical_magnitude(self) -> float:
        """Quantity folded to base-unit scale (internal use for eq/div)."""
        if isinstance(self.unit, UnitProduct):
            return self.quantity * self.unit.fold_scale()
        return self.quantity

    def simplify(self) -> 'Number':
        """Return a new Number expressed in base scale (Scale.one).

        This normalizes the unit expression by removing all scale prefixes
        and adjusting the quantity accordingly. No conversion graph is needed
        since this is purely a scale transformation.

        Examples
        --------
        >>> from ucon import Scale, units
        >>> km = Scale.kilo * units.meter
        >>> km(5).simplify()
        <5000 m>
        >>> mg = Scale.milli * units.gram
        >>> mg(500).simplify()
        <0.5 g>
        """
        if not isinstance(self.unit, UnitProduct):
            # Plain Unit already has no scale
            return Number(quantity=self.quantity, unit=self.unit, uncertainty=self.uncertainty)

        # Compute the combined scale factor
        scale_factor = self.unit.fold_scale()

        # Create new unit with all factors at Scale.one
        base_factors: dict[UnitFactor, float] = {}
        for factor, exp in self.unit.factors.items():
            base_factor = UnitFactor(unit=factor.unit, scale=Scale.one)
            base_factors[base_factor] = exp

        base_unit = UnitProduct(base_factors)

        # Adjust quantity and uncertainty by the scale factor
        new_uncertainty = None
        if self.uncertainty is not None:
            new_uncertainty = self.uncertainty * abs(scale_factor)

        return Number(
            quantity=self.quantity * scale_factor,
            unit=base_unit,
            uncertainty=new_uncertainty,
        )

    def to(self, target, graph=None):
        """Convert this Number to a different unit expression.

        Parameters
        ----------
        target : Unit, UnitProduct, or str
            The target unit to convert to. Strings are resolved via
            :func:`~ucon.units.get_unit_by_name`, which supports bare names
            (``"foot"``), aliases (``"ft"``), scale prefixes (``"km"``),
            and composite expressions (``"m/s²"``).
        graph : ConversionGraph, optional
            The conversion graph to use. If not provided, uses the default graph.

        Returns
        -------
        Number
            A new Number with the converted quantity and target unit.

        Examples
        --------
        >>> from ucon.units import meter, foot
        >>> length = meter(100)
        >>> length.to(foot)
        <328.084 ft>
        >>> length.to("ft")
        <328.084 ft>
        >>> length.to("km")
        <0.1 km>
        """
        # Resolve string targets via name/alias/prefix/expression lookup
        if isinstance(target, str):
            target = _get_unit_by_name(target)

        # Wrap plain Units as UnitProducts for uniform handling
        src = self.unit if isinstance(self.unit, UnitProduct) else UnitProduct.from_unit(self.unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (same base unit, different scale)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = self.uncertainty * abs(factor)
            return Number(quantity=self.quantity * factor, unit=target, uncertainty=new_uncertainty)

        # Graph-based conversion (use default graph if none provided)
        if graph is None:
            graph = get_default_graph()

        # Pass raw Units to graph.convert() when possible, so the graph
        # can use _convert_units() which handles cross-basis via rebased units.
        # UnitProducts only go through _convert_products() which lacks cross-basis support.
        graph_src: Union[Unit, UnitProduct] = src
        graph_dst: Union[Unit, UnitProduct] = dst
        if len(src.factors) == 1:
            uf, exp = next(iter(src.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                graph_src = uf.unit
        if len(dst.factors) == 1:
            uf, exp = next(iter(dst.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                graph_dst = uf.unit

        conversion_map = graph.convert(src=graph_src, dst=graph_dst)
        # Use raw quantity - the conversion map handles scale via factorwise decomposition
        converted_quantity = conversion_map(self.quantity)

        # Account for residual scale factors from cancelled dimensions.
        # When units cancel (e.g., mcg/kg), the scale ratio goes into _residual_scale_factor.
        # The graph conversion only sees the remaining dimensions, so we must apply
        # the residual ratio here: src_residual / dst_residual.
        src_residual = getattr(src, '_residual_scale_factor', 1.0)
        dst_residual = getattr(dst, '_residual_scale_factor', 1.0)
        if src_residual != 1.0 or dst_residual != 1.0:
            converted_quantity *= (src_residual / dst_residual)

        # Propagate uncertainty through conversion using derivative
        new_uncertainty = None
        if self.uncertainty is not None:
            derivative = abs(conversion_map.derivative(self.quantity))
            # Also apply residual scale to uncertainty
            if src_residual != 1.0 or dst_residual != 1.0:
                derivative *= abs(src_residual / dst_residual)
            new_uncertainty = derivative * self.uncertainty

        return Number(quantity=converted_quantity, unit=target, uncertainty=new_uncertainty)

    def _is_scale_only_conversion(self, src: UnitProduct, dst: UnitProduct) -> bool:
        """Check if conversion is just a scale change (same base units)."""
        if len(src.factors) != len(dst.factors):
            return False

        src_by_dim = {}
        dst_by_dim = {}
        for f, exp in src.factors.items():
            src_by_dim[f.unit.dimension] = (f.unit, exp)
        for f, exp in dst.factors.items():
            dst_by_dim[f.unit.dimension] = (f.unit, exp)

        if src_by_dim.keys() != dst_by_dim.keys():
            return False

        for dim in src_by_dim:
            src_unit, src_exp = src_by_dim[dim]
            dst_unit, dst_exp = dst_by_dim[dim]
            if src_unit != dst_unit or abs(src_exp - dst_exp) > 1e-12:
                return False

        return True

    def as_ratio(self):
        return Ratio(self)

    def __mul__(self, other: _Quantifiable) -> 'Number':
        if isinstance(other, Ratio):
            other = other.evaluate()

        # Scalar multiplication
        if isinstance(other, (int, float)):
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = abs(other) * self.uncertainty
            return Number(
                quantity=self.quantity * other,
                unit=self.unit,
                uncertainty=new_uncertainty,
            )

        if not isinstance(other, Number):
            return NotImplemented

        # Uncertainty propagation for multiplication
        # δc = |c| * sqrt((δa/a)² + (δb/b)²)
        new_uncertainty = None
        result_quantity = self.quantity * other.quantity
        if self.uncertainty is not None or other.uncertainty is not None:
            rel_a = (self.uncertainty / abs(self.quantity)) if (self.uncertainty and self.quantity != 0) else 0
            rel_b = (other.uncertainty / abs(other.quantity)) if (other.uncertainty and other.quantity != 0) else 0
            rel_c = math.sqrt(rel_a**2 + rel_b**2)
            new_uncertainty = abs(result_quantity) * rel_c if rel_c > 0 else None

        return Number(
            quantity=result_quantity,
            unit=self.unit * other.unit,
            uncertainty=new_uncertainty,
        )

    def __add__(self, other: 'Number') -> 'Number':
        if not isinstance(other, Number):
            return NotImplemented

        # Dimensions must match for addition
        if self.unit.dimension != other.unit.dimension:
            raise TypeError(
                f"Cannot add Numbers with different dimensions: "
                f"{self.unit.dimension} vs {other.unit.dimension}"
            )

        # Uncertainty propagation for addition: δc = sqrt(δa² + δb²)
        new_uncertainty = None
        if self.uncertainty is not None or other.uncertainty is not None:
            ua = self.uncertainty if self.uncertainty is not None else 0
            ub = other.uncertainty if other.uncertainty is not None else 0
            new_uncertainty = math.sqrt(ua**2 + ub**2)

        return Number(
            quantity=self.quantity + other.quantity,
            unit=self.unit,
            uncertainty=new_uncertainty,
        )

    def __sub__(self, other: 'Number') -> 'Number':
        if not isinstance(other, Number):
            return NotImplemented

        # Dimensions must match for subtraction
        if self.unit.dimension != other.unit.dimension:
            raise TypeError(
                f"Cannot subtract Numbers with different dimensions: "
                f"{self.unit.dimension} vs {other.unit.dimension}"
            )

        # Uncertainty propagation for subtraction: δc = sqrt(δa² + δb²)
        new_uncertainty = None
        if self.uncertainty is not None or other.uncertainty is not None:
            ua = self.uncertainty if self.uncertainty is not None else 0
            ub = other.uncertainty if other.uncertainty is not None else 0
            new_uncertainty = math.sqrt(ua**2 + ub**2)

        return Number(
            quantity=self.quantity - other.quantity,
            unit=self.unit,
            uncertainty=new_uncertainty,
        )

    def __truediv__(self, other: _Quantifiable) -> "Number":
        # Allow dividing by a Ratio (interpret as its evaluated Number)
        if isinstance(other, Ratio):
            other = other.evaluate()

        # Scalar division
        if isinstance(other, (int, float)):
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = self.uncertainty / abs(other)
            return Number(
                quantity=self.quantity / other,
                unit=self.unit,
                uncertainty=new_uncertainty,
            )

        if not isinstance(other, Number):
            raise TypeError(f"Cannot divide Number by non-Number/Ratio type: {type(other)}")

        # Symbolic quotient in the unit algebra
        unit_quot = self.unit / other.unit

        # Uncertainty propagation for division
        # δc = |c| * sqrt((δa/a)² + (δb/b)²)
        def compute_uncertainty(result_quantity):
            if self.uncertainty is None and other.uncertainty is None:
                return None
            rel_a = (self.uncertainty / abs(self.quantity)) if (self.uncertainty and self.quantity != 0) else 0
            rel_b = (other.uncertainty / abs(other.quantity)) if (other.uncertainty and other.quantity != 0) else 0
            rel_c = math.sqrt(rel_a**2 + rel_b**2)
            return abs(result_quantity) * rel_c if rel_c > 0 else None

        # --- Case 1: Dimensionless result ----------------------------------
        # If the net dimension is none, we want a pure scalar:
        # fold *all* scale factors into the numeric magnitude.
        if not unit_quot.dimension:
            num = self._canonical_magnitude
            den = other._canonical_magnitude
            result = num / den
            return Number(quantity=result, unit=_none, uncertainty=compute_uncertainty(result))

        # --- Case 2: Dimensionful result -----------------------------------
        # For "real" physical results like g/mL, m/s², etc., preserve the
        # user's chosen unit scales symbolically. Only divide the raw quantities.
        new_quantity = self.quantity / other.quantity
        return Number(quantity=new_quantity, unit=unit_quot, uncertainty=compute_uncertainty(new_quantity))

    def __eq__(self, other: _Quantifiable) -> bool:
        if not isinstance(other, (Number, Ratio)):
            raise TypeError(
                f"Cannot compare Number to non-Number/Ratio type: {type(other)}"
            )

        # If comparing with a Ratio, evaluate it to a Number
        if isinstance(other, Ratio):
            other = other.evaluate()

        # Dimensions must match
        if self.unit.dimension != other.unit.dimension:
            return False

        # Compare magnitudes, scale-adjusted
        if abs(self._canonical_magnitude - other._canonical_magnitude) >= 1e-12:
            return False

        return True

    def __pow__(self, power: Union[int, float]) -> 'Number':
        """Raise Number to a power.

        Examples
        --------
        >>> from ucon import units
        >>> v = units.meter(3) / units.second(1)
        >>> v ** 2
        <9 m²/s²>
        """
        new_quantity = self.quantity ** power
        new_unit = self.unit ** power

        # Uncertainty propagation: δ(x^n) = |n| * x^(n-1) * δx = |n| * (x^n / x) * δx
        new_uncertainty = None
        if self.uncertainty is not None and self.quantity != 0:
            new_uncertainty = abs(power) * abs(new_quantity / self.quantity) * self.uncertainty

        return Number(
            quantity=new_quantity,
            unit=new_unit,
            uncertainty=new_uncertainty,
        )

    def __repr__(self):
        if self.uncertainty is not None:
            if not self.unit.dimension:
                return f"<{self.quantity} ± {self.uncertainty}>"
            return f"<{self.quantity} ± {self.uncertainty} {self.unit.shorthand}>"
        if not self.unit.dimension:
            return f"<{self.quantity}>"
        return f"<{self.quantity} {self.unit.shorthand}>"


class Ratio:
    """
    Represents a **ratio of two Numbers**, preserving their unit semantics.

    Useful for expressing physical relationships like efficiency, density,
    or dimensionless comparisons:

        >>> ratio = Ratio(length, time)
        >>> ratio.evaluate()
        <2.5 m/s>
    """
    def __init__(self, numerator: Number = None, denominator: Number = None):
        self.numerator = numerator if numerator is not None else Number()
        self.denominator = denominator if denominator is not None else Number()

    def reciprocal(self) -> 'Ratio':
        return Ratio(numerator=self.denominator, denominator=self.numerator)

    def evaluate(self) -> "Number":
        """Evaluate the ratio to a Number.

        Uses Exponent-derived arithmetic for scale handling:
        - If the result is dimensionless (units cancel), scales are folded
          into the magnitude using _canonical_magnitude.
        - If the result is dimensionful, raw quantities are divided and
          unit scales are preserved symbolically.

        This matches the behavior of Number.__truediv__ for consistency.
        """
        # Symbolic quotient in the unit algebra
        unit = self.numerator.unit / self.denominator.unit

        # Dimensionless result: fold all scale factors into magnitude
        if not unit.dimension:
            num = self.numerator._canonical_magnitude
            den = self.denominator._canonical_magnitude
            return Number(quantity=num / den, unit=_none)

        # Dimensionful result: preserve user's chosen scales symbolically
        numeric = self.numerator.quantity / self.denominator.quantity
        return Number(quantity=numeric, unit=unit)

    def __mul__(self, another_ratio: 'Ratio') -> 'Ratio':
        if self.numerator.unit == another_ratio.denominator.unit:
            factor = self.numerator / another_ratio.denominator
            numerator, denominator = factor * another_ratio.numerator, self.denominator
        elif self.denominator.unit == another_ratio.numerator.unit:
            factor = another_ratio.numerator / self.denominator
            numerator, denominator = factor * self.numerator, another_ratio.denominator
        else:
            factor = Number()
            another_number = another_ratio.evaluate()
            numerator, denominator = self.numerator * another_number, self.denominator
        return Ratio(numerator=numerator, denominator=denominator)

    def __truediv__(self, another_ratio: 'Ratio') -> 'Ratio':
        return Ratio(
            numerator=self.numerator * another_ratio.denominator,
            denominator=self.denominator * another_ratio.numerator,
        )

    def __eq__(self, another_ratio: 'Ratio') -> bool:
        if isinstance(another_ratio, Ratio):
            return self.evaluate() == another_ratio.evaluate()
        elif isinstance(another_ratio, Number):
            return self.evaluate() == another_ratio
        else:
            raise ValueError(f'"{another_ratio}" is not a Ratio or Number. Comparison not possible.')

    def __repr__(self):
        return f'{self.evaluate()}' if self.numerator == self.denominator else f'{self.numerator} / {self.denominator}'


__all__ = [
    'DimensionConstraint',
    'Number',
    'Ratio',
    '_Quantifiable',
    '_none',
]

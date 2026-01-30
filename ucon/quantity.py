# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.quantity
==========

Implements the **quantitative core** of the *ucon* system — the machinery that
defines how numeric values are coupled with units and scales to represent
physical quantities.

Classes
-------
- :class:`Quantity` — A Unit that constructs Numbers when called.
- :class:`Number` — Couples a numeric value with a unit and scale.
- :class:`Ratio` — Represents a ratio between two :class:`Number` objects.

Together, these classes allow full arithmetic, conversion, and introspection
of physical quantities with explicit dimensional semantics.
"""
from dataclasses import dataclass
from typing import Union

from ucon.core import Unit, UnitProduct, UnitFactor, Scale


# Dimensionless unit (no import from units to avoid circular dependency)
_none = Unit()


Quantifiable = Union['Number', 'Ratio']

@dataclass
class Number:
    """
    Represents a **numeric quantity** with an associated :class:`Unit` and :class:`Scale`.

    Combines magnitude, unit, and scale into a single, composable object that
    supports dimensional arithmetic and conversion:

        >>> from ucon import core, units
        >>> length = core.Number(unit=units.meter, quantity=5)
        >>> time = core.Number(unit=units.second, quantity=2)
        >>> speed = length / time
        >>> speed
        <2.5 (m/s)>
    """
    quantity: Union[float, int] = 1.0
    unit: Union[Unit, UnitProduct] = _none

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

    def simplify(self):
        """Return a new Number expressed in base scale (Scale.one)."""
        raise NotImplementedError("Unit simplification requires ConversionGraph; coming soon.")

    def to(self, target, graph=None):
        """Convert this Number to a different unit expression.

        Parameters
        ----------
        target : Unit or UnitProduct
            The target unit to convert to.
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
        """
        from ucon.graph import get_default_graph

        # Wrap plain Units as UnitProducts for uniform handling
        src = self.unit if isinstance(self.unit, UnitProduct) else UnitProduct.from_unit(self.unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (same base unit, different scale)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            return Number(quantity=self.quantity * factor, unit=target)

        # Graph-based conversion (use default graph if none provided)
        if graph is None:
            graph = get_default_graph()

        conversion_map = graph.convert(src=src, dst=dst)
        converted_quantity = conversion_map(self._canonical_magnitude)
        return Number(quantity=converted_quantity, unit=target)

    def _is_scale_only_conversion(self, src: UnitProduct, dst: UnitProduct) -> bool:
        """Check if conversion is just a scale change (same base units)."""
        # Same factors with same exponents, just different scales
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

    def __mul__(self, other: Quantifiable) -> 'Number':
        if isinstance(other, Ratio):
            other = other.evaluate()

        if not isinstance(other, Number):
            return NotImplemented

        return Number(
            quantity=self.quantity * other.quantity,
            unit=self.unit * other.unit,
        )

    def __truediv__(self, other: Quantifiable) -> "Number":
        # Allow dividing by a Ratio (interpret as its evaluated Number)
        if isinstance(other, Ratio):
            other = other.evaluate()

        if not isinstance(other, Number):
            raise TypeError("Cannot divide Number by non-Number/Ratio type: {type(other)}")

        # Symbolic quotient in the unit algebra
        unit_quot = self.unit / other.unit

        # --- Case 1: Dimensionless result ----------------------------------
        # If the net dimension is none, we want a pure scalar:
        # fold *all* scale factors into the numeric magnitude.
        if not unit_quot.dimension:
            num = self._canonical_magnitude    # quantity × scale
            den = other._canonical_magnitude
            return Number(quantity=num / den, unit=_none)

        # --- Case 2: Dimensionful result -----------------------------------
        # For "real" physical results like g/mL, m/s², etc., preserve the
        # user's chosen unit scales symbolically. Only divide the raw quantities.
        new_quantity = self.quantity / other.quantity
        return Number(quantity=new_quantity, unit=unit_quot)

    def __eq__(self, other: Quantifiable) -> bool:
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

    def __repr__(self):
        if not self.unit.dimension:
            return f"<{self.quantity}>"
        return f"<{self.quantity} {self.unit.shorthand}>"


# TODO -- consider using a dataclass
class Ratio:
    """
    Represents a **ratio of two Numbers**, preserving their unit semantics.

    Useful for expressing physical relationships like efficiency, density,
    or dimensionless comparisons:

        >>> ratio = Ratio(length, time)
        >>> ratio.evaluate()
        <2.5 (m/s)>
    """
    def __init__(self, numerator: Number = Number(), denominator: Number = Number()):
        self.numerator = numerator
        self.denominator = denominator

    def reciprocal(self) -> 'Ratio':
        return Ratio(numerator=self.denominator, denominator=self.numerator)

    def evaluate(self) -> "Number":
        # Pure arithmetic, no scale normalization.
        numeric = self.numerator.quantity / self.denominator.quantity

        # Pure unit division, with UnitFactor preservation.
        unit = self.numerator.unit / self.denominator.unit

        # DO NOT normalize, DO NOT fold scale.
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
        # TODO -- resolve int/float inconsistency
        return f'{self.evaluate()}' if self.numerator == self.denominator else f'{self.numerator} / {self.denominator}'


@dataclass(frozen=True)
class Quantity(Unit):
    """A Unit that constructs Numbers when called.

    Follows the physical definition: a quantity is a number with units.
    This class enables the ergonomic syntax::

        >>> from ucon.units import meter
        >>> length = meter(5)
        >>> length
        <5 m>

    Quantity inherits from Unit but overrides arithmetic operators to
    return UnitProduct (for composite units like ``mile / hour``).
    """

    def __call__(self, value: float) -> Number:
        """Construct a Number with this unit."""
        return Number(quantity=value, unit=UnitProduct.from_unit(self))

    def __mul__(self, other: "Quantity") -> UnitProduct:
        """Quantity * Quantity -> UnitProduct."""
        if isinstance(other, Quantity):
            return UnitProduct.from_unit(self) * UnitProduct.from_unit(other)
        if isinstance(other, Unit):
            return UnitProduct.from_unit(self) * UnitProduct.from_unit(other)
        if isinstance(other, UnitProduct):
            return UnitProduct.from_unit(self) * other
        return NotImplemented

    def __truediv__(self, other: "Quantity") -> UnitProduct:
        """Quantity / Quantity -> UnitProduct."""
        if isinstance(other, Quantity):
            return UnitProduct.from_unit(self) / UnitProduct.from_unit(other)
        if isinstance(other, Unit):
            return UnitProduct.from_unit(self) / UnitProduct.from_unit(other)
        if isinstance(other, UnitProduct):
            return UnitProduct.from_unit(self) / other
        return NotImplemented

    def __pow__(self, exp: float) -> UnitProduct:
        """Quantity ** exp -> UnitProduct."""
        return UnitProduct({UnitFactor(self, Scale.one): exp})

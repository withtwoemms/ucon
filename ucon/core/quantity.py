# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core.quantity
==================

Quantity types: :class:`Number`, :class:`Ratio`, and :class:`DimensionConstraint`.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from ucon.core.scale import Scale
from ucon.core.unit import Unit, UnitFactor
from ucon.core.product import UnitProduct
from ucon.dimension import Dimension, NONE

if TYPE_CHECKING:
    from ucon.graph import ConversionGraph
    from ucon.system import UnitSystem

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
        """Quantity in coherent base-unit scale.

        Pure function of (self.quantity, self.unit). Does NOT consult any graph.
        """
        if isinstance(self.unit, UnitProduct):
            result = self.quantity * getattr(self.unit, '_residual_scale_factor', 1.0)
            for uf, exp in self.unit.factors.items():
                result *= uf.scale.value.evaluated ** exp
                bf = uf.unit.base_form
                if bf is not None:
                    result *= bf.prefactor ** exp
            return result
        bf = self.unit.base_form
        if bf is not None:
            return self.quantity * bf.prefactor
        return self.quantity

    @property
    def canonical_magnitude(self) -> float:
        """Quantity expressed in coherent base-unit scale, as a plain float.

        This is the magnitude you would get from :meth:`to_base` and then
        reading ``.quantity``. It is a pure function of ``(self.quantity,
        self.unit)`` and does NOT consult any conversion graph.

        Use :attr:`canonical_magnitude` at interop boundaries where you need
        a raw float in SI-coherent units (e.g., for a dimensionless formula
        constant, a JSON payload, or a plotting library). For unit-safe
        composition, prefer :meth:`to_base`, which returns a new ``Number``.

        Examples
        --------
        >>> from ucon.units import kilometer, hour
        >>> kilometer(5).canonical_magnitude
        5000.0
        >>> (kilometer(90) / hour(1)).canonical_magnitude
        25.0
        """
        return self._canonical_magnitude

    @property
    def base_signature(self) -> tuple:
        """Hashable, sorted base-unit-name projection of this Number's unit.

        Delegates to ``self.unit.base_signature``. See
        :attr:`Unit.base_signature` for semantics and intended uses.

        The signature is invariant under :meth:`to_base` — that is,
        ``n.base_signature == n.to_base().base_signature`` for every
        ``Number n``. This makes it a useful dispatch / grouping key for
        formula inputs expressed in arbitrary scales.

        Examples
        --------
        >>> from ucon.units import kilometer, hour
        >>> kilometer(5).base_signature
        (('meter', 1.0),)
        >>> (kilometer(90) / hour(1)).base_signature
        (('meter', 1.0), ('second', -1.0))
        """
        return self.unit.base_signature

    @property
    def in_base_form(self) -> bool:
        """True if this Number is already expressed in coherent base units.

        A Number is *in base form* when :meth:`to_base` would produce an
        output equivalent to ``self`` (up to structural identity of the
        unit expression). Concretely, this holds when:

        * every factor's scale is :attr:`Scale.one`,
        * every factor's underlying :class:`Unit` is a *leaf* — either
          ``base_form is None`` or a self-referential coherent base
          (e.g., ``kilogram``, ``meter``), and
        * any residual scale factor from cancelled factors is ``1.0``.

        Use ``in_base_form`` as a fast pre-check to avoid a redundant
        :meth:`to_base` call in hot paths, or as an invariant assertion at
        formula boundaries.

        Examples
        --------
        >>> from ucon.units import kilometer, meter, hour, joule
        >>> meter(5).in_base_form
        True
        >>> kilometer(5).in_base_form
        False
        >>> kilometer(5).to_base().in_base_form
        True
        >>> joule(1).in_base_form  # joule has a non-trivial base_form
        False
        """
        def _is_leaf(u: 'Unit') -> bool:
            bf = u.base_form
            if bf is None:
                return True
            return (len(bf.factors) == 1
                    and bf.factors[0][0] is u
                    and abs(bf.factors[0][1] - 1.0) < 1e-12)

        if isinstance(self.unit, UnitProduct):
            if getattr(self.unit, '_residual_scale_factor', 1.0) != 1.0:
                return False
            for uf in self.unit.factors:
                if uf.scale is not Scale.one:
                    return False
                if not _is_leaf(uf.unit):
                    return False
            return True
        return _is_leaf(self.unit)

    def to_base(self) -> 'Number':
        """Return a new Number expressed in coherent base-unit scale.

        Walks ``self.unit`` and decomposes each factor through its
        :attr:`~Unit.base_form` (when available) to produce a quantity in the
        basis's canonical base units (e.g., SI: ``kg, m, s, A, K, cd, mol``).

        This is a pure algebraic operation; no :class:`~ucon.graph.ConversionGraph`
        is consulted. Units that lack a ``base_form`` (affine temperature
        units, logarithmic units, or units whose definition is graph-only)
        are preserved as-is at ``Scale.one``.

        Returns
        -------
        Number
            A new ``Number`` whose unit is either a plain base ``Unit`` (when
            the decomposition collapses to a single factor at exponent 1) or
            a :class:`UnitProduct` of base units. Uncertainty is scaled by the
            same multiplier as the quantity.

        Examples
        --------
        >>> from ucon.units import kilometer, hour, joule
        >>> kilometer(5).to_base()
        <5000 m>
        >>> (kilometer(90) / hour(1)).to_base()
        <25 m/s>
        >>> joule(1).to_base()
        <1 kg·m²/s²>

        Notes
        -----
        ``to_base()`` is the unit-safe counterpart to
        :attr:`canonical_magnitude`. The identity
        ``n.to_base().quantity == n.canonical_magnitude`` holds for every
        ``Number n``.
        """
        # Total multiplier from self.unit to base-unit scale.
        # Compute on a unit Number so quantity=0 is handled correctly.
        multiplier = Number(1.0, self.unit)._canonical_magnitude
        canonical_q = self.quantity * multiplier

        new_uncertainty = None
        if self.uncertainty is not None:
            new_uncertainty = self.uncertainty * abs(multiplier)

        def _decompose(unit) -> dict:
            """Return a dict[UnitFactor, float] of base-unit factors for `unit`.

            If `unit` has no useful base_form (None or self-referential),
            it is preserved as-is at Scale.one.
            """
            bf = unit.base_form
            if bf is None:
                return {UnitFactor(unit, Scale.one): 1.0}
            # Self-referential coherent base (e.g., kilogram -> kilogram^1)
            if (len(bf.factors) == 1
                    and bf.factors[0][0] is unit
                    and abs(bf.factors[0][1] - 1.0) < 1e-12):
                return {UnitFactor(unit, Scale.one): 1.0}
            out: dict = {}
            for base_unit, base_exp in bf.factors:
                key = UnitFactor(base_unit, Scale.one)
                out[key] = out.get(key, 0.0) + base_exp
            return out

        # Accumulate base-unit factors with combined exponents
        base_dict: dict = {}
        if isinstance(self.unit, UnitProduct):
            for uf, exp in self.unit.factors.items():
                for key, base_exp in _decompose(uf.unit).items():
                    base_dict[key] = base_dict.get(key, 0.0) + base_exp * exp
        else:
            for key, base_exp in _decompose(self.unit).items():
                base_dict[key] = base_dict.get(key, 0.0) + base_exp

        # Drop zero exponents
        base_dict = {k: e for k, e in base_dict.items() if abs(e) > 1e-12}

        # Degenerate case: everything cancelled. Preserve structural unit.
        if not base_dict:
            return Number(
                quantity=canonical_q,
                unit=self.unit,
                uncertainty=new_uncertainty,
            )

        # Single factor at exp 1.0: return as plain Unit for ergonomic output
        if len(base_dict) == 1:
            key, exp = next(iter(base_dict.items()))
            if abs(exp - 1.0) < 1e-12:
                return Number(
                    quantity=canonical_q,
                    unit=key.unit,
                    uncertainty=new_uncertainty,
                )

        return Number(
            quantity=canonical_q,
            unit=UnitProduct(base_dict),
            uncertainty=new_uncertainty,
        )

    def same_dimension_as(self, other) -> bool:
        """Return True if ``self`` and ``other`` share a dimension.

        Accepts another :class:`Number`, :class:`Unit`, or
        :class:`UnitProduct`. Compares on :attr:`Dimension` equality — the
        fundamental invariant of unit compatibility — which is basis-aware
        and scale-agnostic.

        This is a lightweight compatibility check for the common case
        "can I add / compare / feed these into the same formula slot?"
        without the overhead of constructing a conversion or walking the
        graph.

        Parameters
        ----------
        other : Number, Unit, or UnitProduct
            The quantity or unit expression to compare dimensions with.

        Returns
        -------
        bool
            True if the dimensions match, False otherwise.

        Raises
        ------
        TypeError
            If ``other`` is not a Number, Unit, or UnitProduct.

        Examples
        --------
        >>> from ucon.units import kilometer, mile, hour, second, joule
        >>> kilometer(5).same_dimension_as(mile(3))
        True
        >>> kilometer(5).same_dimension_as(hour(2))
        False
        >>> (kilometer(90) / hour(1)).same_dimension_as(
        ...     kilometer(1) / second(1)
        ... )
        True
        """
        if isinstance(other, Number):
            return self.unit.dimension == other.unit.dimension
        if isinstance(other, (Unit, UnitProduct)):
            return self.unit.dimension == other.dimension
        raise TypeError(
            f"same_dimension_as expects Number, Unit, or UnitProduct; "
            f"got {type(other).__name__}"
        )

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

    def to(
        self,
        target,
        graph: "ConversionGraph | None" = None,
        propagate_factor_uncertainty: bool = False,
        *,
        system: "UnitSystem | None" = None,
    ):
        """Convert this Number to a different unit expression.

        Parameters
        ----------
        target : Unit, UnitProduct, or str
            The target unit to convert to. Strings are resolved via
            :func:`~ucon.resolver.parse_unit`, which supports bare names
            (``"foot"``), aliases (``"ft"``), scale prefixes (``"km"``),
            and composite expressions (``"m/s²"``).
        graph : ConversionGraph, optional
            The conversion graph to use. If not provided, uses the default graph.
        propagate_factor_uncertainty : bool, optional
            When ``True``, include the relative uncertainty of the conversion
            factor (from measured physical constants) in the result uncertainty
            via GUM quadrature.  Default ``False`` preserves backward
            compatibility — only measurement uncertainty is propagated.
        system : UnitSystem, optional
            When provided, routes through ``system.conversion_graph`` for graph
            lookups and ``system.units`` for string-target parsing. Takes
            precedence over ``graph=`` when both are given.

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
        # Route through UnitSystem: active system is the authority.
        if system is None:
            from ucon.system import active  # transitional deferred import (Phase 2 eliminates)
            system = active()

        # Explicit graph= takes precedence; otherwise use get_default_graph()
        # which respects the 3-tier priority: context-local → active system → module default.
        # Using system.conversion_graph directly would bypass context-scoped graphs
        # (from using_context / using_conversion_graph).
        if graph is None:
            from ucon.graph import get_default_graph  # transitional deferred import (Phase 2 eliminates)
            graph = get_default_graph()

        # Resolve string targets via the system's resolver
        if isinstance(target, str):
            target = system.resolve_unit(target)

        # --- Fast path: plain Unit → plain Unit (no UnitProduct wrapping) ---
        src_unit = self.unit
        dst_unit = target

        src_is_plain = isinstance(src_unit, Unit) and not isinstance(src_unit, UnitProduct)
        dst_is_plain = isinstance(dst_unit, Unit) and not isinstance(dst_unit, UnitProduct)

        if not src_is_plain and isinstance(src_unit, UnitProduct) and len(src_unit.factors) == 1:
            uf, exp = next(iter(src_unit.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                src_is_plain = True
                src_unit = uf.unit

        if not dst_is_plain and isinstance(dst_unit, UnitProduct) and len(dst_unit.factors) == 1:
            uf, exp = next(iter(dst_unit.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                dst_is_plain = True
                dst_unit = uf.unit

        if src_is_plain and dst_is_plain and src_unit != dst_unit:
            conversion_map = graph.convert(src=src_unit, dst=dst_unit)
            converted = conversion_map(self.quantity)
            new_unc = None
            if self.uncertainty is not None or (
                propagate_factor_uncertainty and conversion_map.rel_uncertainty > 0
            ):
                dy_meas = abs(conversion_map.derivative(self.quantity)) * self.uncertainty \
                          if self.uncertainty is not None else 0.0
                dy_factor = abs(converted) * conversion_map.rel_uncertainty \
                            if propagate_factor_uncertainty else 0.0
                new_unc = math.sqrt(dy_meas**2 + dy_factor**2)
                if new_unc == 0.0:
                    new_unc = None
            return Number(quantity=converted, unit=target, uncertainty=new_unc)

        # --- General path: wrap into UnitProducts ---
        src = self.unit if isinstance(self.unit, UnitProduct) else UnitProduct.from_unit(self.unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (same base unit, different scale)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = self.uncertainty * abs(factor)
            return Number(quantity=self.quantity * factor, unit=target, uncertainty=new_uncertainty)

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
        if self.uncertainty is not None or (
            propagate_factor_uncertainty and conversion_map.rel_uncertainty > 0
        ):
            derivative = abs(conversion_map.derivative(self.quantity))
            # Also apply residual scale to uncertainty
            if src_residual != 1.0 or dst_residual != 1.0:
                derivative *= abs(src_residual / dst_residual)
            dy_meas = derivative * self.uncertainty if self.uncertainty is not None else 0.0
            dy_factor = abs(converted_quantity) * conversion_map.rel_uncertainty \
                        if propagate_factor_uncertainty else 0.0
            new_uncertainty = math.sqrt(dy_meas**2 + dy_factor**2)
            if new_uncertainty == 0.0:
                new_uncertainty = None

        return Number(quantity=converted_quantity, unit=target, uncertainty=new_uncertainty)

    def _is_scale_only_conversion(self, src: UnitProduct, dst: UnitProduct) -> bool:
        """Check if conversion is just a scale change (same base units)."""
        if len(src.factors) != len(dst.factors):
            return False

        # Single-factor fast path: avoid building two dicts
        if len(src.factors) == 1:
            sf, se = next(iter(src.factors.items()))
            df, de = next(iter(dst.factors.items()))
            return sf.unit == df.unit and abs(se - de) < 1e-12

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

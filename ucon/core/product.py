# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core.product
=================

:class:`UnitProduct` — product/quotient of Units with simplification
and readable rendering.
"""
from __future__ import annotations

from functools import reduce
from typing import TYPE_CHECKING, Union

from ucon.core.scale import Scale
from ucon.core.unit import BaseForm, Unit, UnitFactor
from ucon.dimension import Dimension, NONE

if TYPE_CHECKING:
    from ucon.core.quantity import Number

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


class UnitProduct:
    """
    Represents a product or quotient of Units.

    Key properties:
    - factors is a dict[UnitFactor, float] mapping (unit, scale) pairs to exponents.
    - Nested UnitProduct instances are flattened.
    - Identical UnitFactors (same underlying unit and same scale) merge exponents.
    - Units with net exponent ~0 are dropped.
    - Dimensionless units (NONE) are dropped.
    - Scaled variants of the same base unit (e.g. L and mL) are grouped by
      (name, dimension, aliases) and their exponents combined; if the net exponent
      is ~0, the whole group is cancelled.
    """

    _SUPERSCRIPTS = str.maketrans("0123456789-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻·")

    def __init__(self, factors: dict[Unit, float]):
        """
        Build a UnitProduct with UnitFactor keys, preserving user-provided scales.

        Key principles:
        - Never canonicalize scale (no implicit preference for Scale.one).
        - Only collapse scaled variants of the same base unit when total exponent == 0.
        - If only one scale variant exists in a group, preserve it exactly.
        - If multiple variants exist and the group exponent != 0, preserve the FIRST
        encountered UnitFactor (keeps user-intent scale).
        """

        self.name = ""
        self.aliases = ()

        # --- Fast path: single factor, no nesting ---
        if len(factors) == 1:
            key, exp = next(iter(factors.items()))
            if not isinstance(key, UnitProduct):
                if isinstance(key, Unit) and not isinstance(key, UnitFactor):
                    key = UnitFactor(key, Scale.one)
                if isinstance(key, UnitFactor) and key.dimension != NONE and abs(exp) > 1e-12:
                    self.factors = {key: exp}
                    self._residual_scale_factor = 1.0
                    self.dimension = key.dimension ** exp
                    return

        # --- Fast path: two factors, no nesting, no cancellation ---
        if len(factors) == 2:
            items = list(factors.items())
            k0, e0 = items[0]
            k1, e1 = items[1]
            if not isinstance(k0, UnitProduct) and not isinstance(k1, UnitProduct):
                if isinstance(k0, Unit) and not isinstance(k0, UnitFactor):
                    k0 = UnitFactor(k0, Scale.one)
                if isinstance(k1, Unit) and not isinstance(k1, UnitFactor):
                    k1 = UnitFactor(k1, Scale.one)
                if (isinstance(k0, UnitFactor) and isinstance(k1, UnitFactor)
                        and k0.dimension != NONE and k1.dimension != NONE
                        and abs(e0) > 1e-12 and abs(e1) > 1e-12
                        and k0 != k1):
                    self.factors = {k0: e0, k1: e1}
                    self._residual_scale_factor = 1.0
                    self.dimension = (k0.dimension ** e0) * (k1.dimension ** e1)
                    return

        merged: dict[UnitFactor, float] = {}

        # -----------------------------------------------------
        # Helper: normalize Units or UnitFactors to UnitFactor
        # -----------------------------------------------------
        def to_factored(unit_or_fu):
            if isinstance(unit_or_fu, UnitFactor):
                return unit_or_fu
            # Plain Unit has no scale - wrap with Scale.one
            return UnitFactor(unit_or_fu, Scale.one)

        # -----------------------------------------------------
        # Helper: merge UnitFactors by full (unit, scale) identity
        # -----------------------------------------------------
        def merge_fu(fu: UnitFactor, exponent: float):
            for existing in merged:
                if existing == fu:     # UnitFactor.__eq__ handles scale & unit compare
                    merged[existing] += exponent
                    return
            merged[fu] = merged.get(fu, 0.0) + exponent

        # Track residual scale from nested UnitProducts that get flattened.
        # This captures scale from previously-cancelled units.
        inherited_residual: float = 1.0

        # -----------------------------------------------------
        # Step 1 — Flatten sources into UnitFactors
        # -----------------------------------------------------
        for key, exp in factors.items():
            if isinstance(key, UnitProduct):
                # Flatten nested UnitProducts
                for inner_fu, inner_exp in key.factors.items():
                    merge_fu(inner_fu, inner_exp * exp)
                # Capture residual scale from the nested product
                # (e.g., from mg/kg cancellation)
                inner_residual = getattr(key, '_residual_scale_factor', 1.0)
                if inner_residual != 1.0:
                    inherited_residual *= inner_residual ** exp
            else:
                merge_fu(to_factored(key), exp)

        # -----------------------------------------------------
        # Step 2 — Remove exponent-zero & dimensionless UnitFactors
        # -----------------------------------------------------
        simplified: dict[UnitFactor, float] = {}
        for fu, exp in merged.items():
            if abs(exp) < 1e-12:
                continue
            if fu.dimension == NONE:
                continue
            simplified[fu] = exp

        # -----------------------------------------------------
        # Step 3 — Group by full unit identity (including scale)
        # -----------------------------------------------------
        # NOTE: We include scale in the group key so that differently-scaled
        # variants of the same base unit (e.g., mg and kg) remain separate.
        # This preserves user intent in expressions like mg/kg, allowing
        # the mg to survive when later multiplied by kg (e.g., mg/kg * kg = mg).
        groups: dict[tuple, dict[UnitFactor, float]] = {}

        for fu, exp in simplified.items():
            alias_key = tuple(sorted(a for a in fu.aliases if a))
            group_key = (fu.name, fu.dimension, alias_key, fu.scale)
            groups.setdefault(group_key, {})
            groups[group_key][fu] = groups[group_key].get(fu, 0.0) + exp

        # -----------------------------------------------------
        # Step 4 — Resolve groups while preserving user scale
        # -----------------------------------------------------
        final: dict[UnitFactor, float] = {}

        # Track residual scale NUMERICALLY from cancelled units.
        # This accumulates scale factors when units cancel dimensionally
        # but have different scales (e.g., gram / decagram = factor of 0.1).
        # We use a numeric value rather than Scale to preserve precision
        # for arbitrary combinations (especially binary scales like kibi).
        residual_scale_factor: float = 1.0

        for group_key, bucket in groups.items():
            total_exp = sum(bucket.values())

            # 4A — Full cancellation (dimensionally)
            # BUT: we must preserve the NET SCALE from the cancelled units!
            if abs(total_exp) < 1e-12:
                # Compute the scale contribution from this cancelled group
                # Each factor contributes: factor.scale.value.evaluated ** exponent
                for fu, exp in bucket.items():
                    residual_scale_factor *= fu.scale.value.evaluated ** exp
                continue

            # 4B — Only one scale variant → preserve exactly
            if len(bucket) == 1:
                fu, exp = next(iter(bucket.items()))
                final[fu] = exp
                continue

            # 4C — Multiple scale variants, exponent != 0:
            #      preserve FIRST encountered UnitFactor.
            #      This ensures user scale is preserved.
            #      BUT: also accumulate scale from the OTHER variants
            first_fu = next(iter(bucket.keys()))
            final[first_fu] = total_exp

            # The first_fu will be kept with total_exp, so its scale^total_exp
            # will be folded normally. We need to account for the OTHER factors'
            # scale contributions that are being "absorbed" into this representative.
            for fu, exp in bucket.items():
                if fu is not first_fu:
                    # This factor is being absorbed; its scale contribution
                    # relative to first_fu needs to be captured
                    residual_scale_factor *= fu.scale.value.evaluated ** exp

        self.factors = final

        # Store the residual scale factor from cancellations (numeric)
        # Include inherited residual from nested UnitProducts
        self._residual_scale_factor = residual_scale_factor * inherited_residual

        # -----------------------------------------------------
        # Step 5 — Derive dimension via exponent algebra
        # -----------------------------------------------------
        self.dimension = reduce(
            lambda acc, item: acc * (item[0].dimension ** item[1]),
            self.factors.items(),
            NONE,
        )

    # ------------- Rendering -------------------------------------------------

    @classmethod
    def _append(cls, unit: Unit, power: float, num: list[str], den: list[str]) -> None:
        """
        Append a unit^power into numerator or denominator list. Works with
        both Unit and UnitFactor, since UnitFactor exposes dimension,
        shorthand, name, and aliases.
        """
        if unit.dimension == NONE:
            return
        part = getattr(unit, "shorthand", "") or getattr(unit, "name", "") or ""
        if not part:
            return

        def fmt_exp(p: float) -> str:
            """Format exponent, using int when possible to avoid '2.0' → '²·⁰'."""
            return str(int(p) if p == int(p) else p).translate(cls._SUPERSCRIPTS)

        if power > 0:
            if power == 1:
                num.append(part)
            else:
                num.append(part + fmt_exp(power))
        elif power < 0:
            if power == -1:
                den.append(part)
            else:
                den.append(part + fmt_exp(-power))

    @property
    def shorthand(self) -> str:
        """
        Human-readable composite unit string, e.g. 'kg·m/s²'.
        """
        if not self.factors:
            return ""

        num: list[str] = []
        den: list[str] = []

        for u, power in self.factors.items():
            self._append(u, power, num, den)

        numerator = "·".join(num) or "1"
        denominator = "·".join(den)
        if not denominator:
            return numerator
        if len(den) > 1:
            return f"{numerator}/({denominator})"
        return f"{numerator}/{denominator}"

    def fold_scale(self) -> float:
        """
        Compute the overall numeric scale factor of this UnitProduct by folding
        together the scales of each UnitFactor raised to its exponent,
        plus any residual scale factor from cancelled units.

        Returns
        -------
        float
            The combined numeric scale factor.
        """
        # Cache the result since UnitProduct is effectively immutable
        cached = getattr(self, '_fold_scale_cache', None)
        if cached is not None:
            return cached

        result = getattr(self, '_residual_scale_factor', 1.0)
        for factor, power in self.factors.items():
            result *= factor.scale.value.evaluated ** power

        self._fold_scale_cache = result
        return result

    def to_base_form(self) -> tuple:
        """Expand all factors to SI base units algebraically.

        Returns
        -------
        (base_factors, prefactor)
            base_factors: dict mapping base Unit → net exponent
            prefactor: cumulative scalar (product of all scale, decomposition prefactors)
        """
        cached = getattr(self, '_to_base_form_cache', None)
        if cached is not None:
            return cached

        base_factors: dict = {}
        prefactor = getattr(self, '_residual_scale_factor', 1.0)

        for uf, exp in self.factors.items():
            prefactor *= uf.scale.value.evaluated ** exp

            bf = uf.unit.base_form
            if bf is None:
                # No base_form — treat unit as its own base
                base_factors[uf.unit] = base_factors.get(uf.unit, 0.0) + exp
            else:
                prefactor *= bf.prefactor ** exp
                for base_unit, base_exp in bf.factors:
                    base_factors[base_unit] = base_factors.get(base_unit, 0.0) + base_exp * exp

        # Drop zero-exponent entries
        result = ({u: e for u, e in base_factors.items() if abs(e) > 1e-12}, prefactor)
        self._to_base_form_cache = result
        return result

    @property
    def base_signature(self) -> tuple:
        """Hashable, sorted projection of this product's base-unit decomposition.

        Returns a tuple of ``(base_unit_name, exponent)`` pairs, sorted by
        name. Composes each factor's ``Unit.base_signature`` contribution
        with the product's exponents, collapsing duplicates and dropping
        zero-exponent terms. The prefactor accumulated during base-form
        expansion is intentionally dropped.

        Leverages the same walk as :meth:`to_base_form` but discards the
        cumulative scalar, returning only the basis-identity fingerprint.

        Examples
        --------
        >>> from ucon.units import meter, second
        >>> (meter / second).base_signature
        (('meter', 1.0), ('second', -1.0))
        >>> (meter * meter / (second * second)).base_signature
        (('meter', 2.0), ('second', -2.0))
        """
        accumulated: dict = {}
        for uf, exp in self.factors.items():
            bf = uf.unit.base_form
            if bf is None:
                accumulated[uf.unit.name] = accumulated.get(uf.unit.name, 0.0) + exp
            else:
                for base_u, base_exp in bf.factors:
                    accumulated[base_u.name] = accumulated.get(base_u.name, 0.0) + base_exp * exp
        return tuple(sorted(
            (name, exp) for name, exp in accumulated.items() if abs(exp) > 1e-12
        ))

    # ------------- Helpers ---------------------------------------------------

    _from_unit_cache: dict[int, 'UnitProduct'] = {}

    @classmethod
    def from_unit(cls, unit: Unit) -> 'UnitProduct':
        """Wrap a plain Unit as a UnitProduct with Scale.one (cached)."""
        uid = id(unit)
        cached = cls._from_unit_cache.get(uid)
        if cached is not None:
            return cached
        result = cls({UnitFactor(unit, Scale.one): 1})
        cls._from_unit_cache[uid] = result
        return result

    def as_unit(self) -> Union[Unit, None]:
        """Extract the underlying Unit if this is a trivial single-factor product.

        Returns the Unit when this UnitProduct wraps exactly one factor with
        exponent 1 and Scale.one, otherwise None.
        """
        if len(self.factors) != 1:
            return None
        factor, exp = next(iter(self.factors.items()))
        if exp != 1 or factor.scale != Scale.one:
            return None
        return factor.unit

    def factors_by_dimension(self) -> dict[Dimension, tuple[UnitFactor, float]]:
        """Group factors by dimension.

        Returns a dict mapping each Dimension to (UnitFactor, exponent).
        Raises ValueError if multiple factors share the same Dimension.
        """
        result: dict[Dimension, tuple[UnitFactor, float]] = {}
        for factor, exp in self.factors.items():
            dim = factor.unit.dimension
            if dim in result:
                raise ValueError(f"Multiple factors for dimension {dim}")
            result[dim] = (factor, exp)
        return result

    def _norm(self, aliases: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize alias bag: drop empty/whitespace-only aliases."""
        return tuple(a for a in aliases if a.strip())

    def __pow__(self, power):
        """UnitProduct ** n => new UnitProduct with scaled exponents."""
        return UnitProduct({u: exp * power for u, exp in self.factors.items()})

    # ------------- Algebra ---------------------------------------------------

    def __mul__(self, other):
        if isinstance(other, Unit):
            combined = self.factors.copy()
            combined[other] = combined.get(other, 0.0) + 1.0
            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        if isinstance(other, UnitProduct):
            combined = self.factors.copy()
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) + exp
            result = UnitProduct(combined)
            # Propagate residual scale factors from both operands
            result._residual_scale_factor *= self._residual_scale_factor
            result._residual_scale_factor *= other._residual_scale_factor
            return result

        if isinstance(other, Scale):
            # respect the convention: Scale * Unit, not Unit * Scale
            return NotImplemented

        return NotImplemented

    def __rmul__(self, other):
        # Scale * UnitProduct → apply scale to a canonical sink unit
        if isinstance(other, Scale):
            if not self.factors:
                return self

            # heuristic: choose unit with positive exponent first, else first unit
            items = list(self.factors.items())
            positives = [(u, e) for (u, e) in items if e > 0]
            sink, _ = (positives or items)[0]

            # Normalize sink into a UnitFactor
            if isinstance(sink, UnitFactor):
                sink_fu = sink
            else:
                # Plain Unit has no scale
                sink_fu = UnitFactor(unit=sink, scale=Scale.one)

            # Combine scales (expression-level)
            if sink_fu.scale is not Scale.one:
                new_scale = other * sink_fu.scale
            else:
                new_scale = other

            scaled_sink = UnitFactor(
                unit=sink_fu.unit,
                scale=new_scale,
            )

            combined: dict[UnitFactor, float] = {}
            for u, exp in self.factors.items():
                # Normalize each key into UnitFactor as we go
                if isinstance(u, UnitFactor):
                    fu = u
                else:
                    # Plain Unit has no scale
                    fu = UnitFactor(unit=u, scale=Scale.one)

                if fu is sink_fu:
                    combined[scaled_sink] = combined.get(scaled_sink, 0.0) + exp
                else:
                    combined[fu] = combined.get(fu, 0.0) + exp

            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        if isinstance(other, Unit):
            combined: dict[Unit, float] = {other: 1.0}
            for u, e in self.factors.items():
                combined[u] = combined.get(u, 0.0) + e
            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            combined = self.factors.copy()
            combined[other] = combined.get(other, 0.0) - 1.0
            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        if isinstance(other, UnitProduct):
            combined = self.factors.copy()
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) - exp
            result = UnitProduct(combined)
            # Propagate residual: self's residual divided by other's residual
            result._residual_scale_factor *= self._residual_scale_factor
            result._residual_scale_factor /= other._residual_scale_factor
            return result

        return NotImplemented

    # ------------- Identity & hashing ---------------------------------------

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.shorthand}>"

    def __eq__(self, other):
        if isinstance(other, Unit):
            # Only equal to a plain Unit if we have exactly that unit^1
            # Here, the tuple comparison will invoke UnitFactor.__eq__(Unit)
            # on the key when factors are keyed by UnitFactor.
            return len(self.factors) == 1 and list(self.factors.items()) == [(other, 1.0)]
        return isinstance(other, UnitProduct) and self.factors == other.factors

    def __hash__(self):
        # Sort by name; UnitFactor exposes .name, so this is stable.
        return hash(tuple(sorted(self.factors.items(), key=lambda x: x[0].name)))

    def __call__(self, quantity, uncertainty=None):
        """Create a Number or NumberArray with this unit product.

        Parameters
        ----------
        quantity : int, float, list, tuple, or numpy.ndarray
            The numeric value(s). If array-like, returns NumberArray.
        uncertainty : float, array-like, or None
            The measurement uncertainty.

        Returns
        -------
        Number or NumberArray
            Number for scalar inputs, NumberArray for array inputs.

        Example
        -------
        >>> (meter / second)(10)
        <10 m/s>
        >>> (meter / second)(10, uncertainty=0.5)
        <10 ± 0.5 m/s>
        >>> (meter / second)([10, 20, 30])  # requires numpy
        <NumberArray [10. 20. 30.] m/s>
        """
        from ucon.core.quantity import Number

        # Check for array-like inputs
        if _HAS_NUMPY and (
            isinstance(quantity, np.ndarray)
            or (isinstance(quantity, (list, tuple)) and len(quantity) > 0)
        ):
            from ucon.integrations.numpy import NumberArray
            return NumberArray(quantities=quantity, unit=self, uncertainty=uncertainty)

        return Number(quantity=quantity, unit=self, uncertainty=uncertainty)

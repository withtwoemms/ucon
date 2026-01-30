# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core
==========

Implements the **ontological core** of the *ucon* system — the machinery that
defines the algebra of physical dimensions, magnitude prefixes, and units.

Classes
-------
- :class:`Dimension` — Enumerates physical dimensions with algebraic closure over *, /, and **
- :class:`Scale` — Enumerates SI and binary magnitude prefixes with algebraic closure over *, /
  and with nearest-prefix lookup.
- :class:`Unit` — Measurable quantity descriptor with algebraic closure over *, /.
- :class:`UnitProduct` — Product/quotient of Units with simplification and readable rendering.
"""
from __future__ import annotations

import math
from enum import Enum
from functools import lru_cache, reduce, total_ordering
from dataclasses import dataclass, field
from typing import Dict, Tuple, Union

from ucon.algebra import Exponent, Vector


# --------------------------------------------------------------------------------------
# Dimension
# --------------------------------------------------------------------------------------

class Dimension(Enum):
    """
    Represents a **physical dimension** defined by a :class:`Vector`.
    Algebra over multiplication/division & exponentiation, with dynamic resolution.
    """
    none = Vector()

    # -- BASIS ---------------------------------------
    time                = Vector(1, 0, 0, 0, 0, 0, 0, 0)
    length              = Vector(0, 1, 0, 0, 0, 0, 0, 0)
    mass                = Vector(0, 0, 1, 0, 0, 0, 0, 0)
    current             = Vector(0, 0, 0, 1, 0, 0, 0, 0)
    temperature         = Vector(0, 0, 0, 0, 1, 0, 0, 0)
    luminous_intensity  = Vector(0, 0, 0, 0, 0, 1, 0, 0)
    amount_of_substance = Vector(0, 0, 0, 0, 0, 0, 1, 0)
    information         = Vector(0, 0, 0, 0, 0, 0, 0, 1)
    # ------------------------------------------------

    acceleration = Vector(-2, 1, 0, 0, 0, 0, 0, 0)
    angular_momentum = Vector(-1, 2, 1, 0, 0, 0, 0, 0)
    area = Vector(0, 2, 0, 0, 0, 0, 0, 0)
    capacitance = Vector(4, -2, -1, 2, 0, 0, 0, 0)
    charge = Vector(1, 0, 0, 1, 0, 0, 0, 0)
    conductance = Vector(3, -2, -1, 2, 0, 0, 0, 0)
    conductivity = Vector(3, -3, -1, 2, 0, 0, 0, 0)
    density = Vector(0, -3, 1, 0, 0, 0, 0, 0)
    electric_field_strength = Vector(-3, 1, 1, -1, 0, 0, 0, 0)
    energy = Vector(-2, 2, 1, 0, 0, 0, 0, 0)
    entropy = Vector(-2, 2, 1, 0, -1, 0, 0, 0)
    force = Vector(-2, 1, 1, 0, 0, 0, 0, 0)
    frequency = Vector(-1, 0, 0, 0, 0, 0, 0, 0)
    gravitation = Vector(-2, 3, -1, 0, 0, 0, 0, 0)
    illuminance = Vector(0, -2, 0, 0, 0, 1, 0, 0)
    inductance = Vector(-2, 2, 1, -2, 0, 0, 0, 0)
    magnetic_flux = Vector(-2, 2, 1, -1, 0, 0, 0, 0)
    magnetic_flux_density = Vector(-2, 0, 1, -1, 0, 0, 0, 0)
    magnetic_permeability = Vector(-2, 1, 1, -2, 0, 0, 0, 0)
    molar_mass = Vector(0, 0, 1, 0, 0, 0, -1, 0)
    molar_volume = Vector(0, 3, 0, 0, 0, 0, -1, 0)
    momentum = Vector(-1, 1, 1, 0, 0, 0, 0, 0)
    permittivity = Vector(4, -3, -1, 2, 0, 0, 0, 0)
    power = Vector(-3, 2, 1, 0, 0, 0, 0, 0)
    pressure = Vector(-2, -1, 1, 0, 0, 0, 0, 0)
    resistance = Vector(-3, 2, 1, -2, 0, 0, 0, 0)
    resistivity = Vector(-3, 3, 1, -2, 0, 0, 0, 0)
    specific_heat_capacity = Vector(-2, 2, 0, 0, -1, 0, 0, 0)
    thermal_conductivity = Vector(-3, 1, 1, 0, -1, 0, 0, 0)
    velocity = Vector(-1, 1, 0, 0, 0, 0, 0, 0)
    voltage = Vector(-3, 2, 1, -1, 0, 0, 0, 0)
    volume = Vector(0, 3, 0, 0, 0, 0, 0, 0)

    @classmethod
    def _resolve(cls, vector: 'Vector') -> 'Dimension':
        for dim in cls:
            if dim.value == vector:
                return dim
        dyn = object.__new__(cls)
        dyn._name_ = f"derived({vector})"
        dyn._value_ = vector
        return dyn

    def __truediv__(self, dimension: 'Dimension') -> 'Dimension':
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot divide Dimension by non-Dimension type: {type(dimension)}")
        return self._resolve(self.value - dimension.value)

    def __mul__(self, dimension: 'Dimension') -> 'Dimension':
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot multiply Dimension by non-Dimension type: {type(dimension)}")
        return self._resolve(self.value + dimension.value)

    def __pow__(self, power: Union[int, float]) -> 'Dimension':
        if power == 1:
            return self
        if power == 0:
            return Dimension.none
        new_vector = self.value * power
        return self._resolve(new_vector)

    def __eq__(self, dimension) -> bool:
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot compare Dimension with non-Dimension type: {type(dimension)}")
        return self.value == dimension.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __bool__(self):
        return False if self is Dimension.none else True


# --------------------------------------------------------------------------------------
# Scale (with descriptor)
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ScaleDescriptor:
    exponent: Exponent
    shorthand: str
    alias: str

    @property
    def evaluated(self) -> float:
        return self.exponent.evaluated

    @property
    def base(self) -> int:
        return self.exponent.base

    @property
    def power(self) -> Union[int, float]:
        return self.exponent.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        return (self.base, self.power)

    def __repr__(self):
        tag = self.alias or self.shorthand or "1"
        return f"<ScaleDescriptor {tag}: {self.base}^{self.power}>"


@total_ordering
class Scale(Enum):
    # Binary
    gibi  = ScaleDescriptor(Exponent(2, 30), "Gi", "gibi")
    mebi  = ScaleDescriptor(Exponent(2, 20), "Mi", "mebi")
    kibi  = ScaleDescriptor(Exponent(2, 10), "Ki", "kibi")

    # Decimal
    peta  = ScaleDescriptor(Exponent(10, 15), "P", "peta")
    tera  = ScaleDescriptor(Exponent(10, 12), "T", "tera")
    giga  = ScaleDescriptor(Exponent(10, 9),  "G", "giga")
    mega  = ScaleDescriptor(Exponent(10, 6),  "M", "mega")
    kilo  = ScaleDescriptor(Exponent(10, 3),  "k", "kilo")
    hecto = ScaleDescriptor(Exponent(10, 2),  "h", "hecto")
    deca  = ScaleDescriptor(Exponent(10, 1),  "da", "deca")
    one   = ScaleDescriptor(Exponent(10, 0),  "",  "")
    deci  = ScaleDescriptor(Exponent(10,-1),  "d", "deci")
    centi = ScaleDescriptor(Exponent(10,-2),  "c", "centi")
    milli = ScaleDescriptor(Exponent(10,-3),  "m", "milli")
    micro = ScaleDescriptor(Exponent(10,-6),  "µ", "micro")
    nano  = ScaleDescriptor(Exponent(10,-9),  "n", "nano")
    pico  = ScaleDescriptor(Exponent(10,-12), "p", "pico")
    femto = ScaleDescriptor(Exponent(10,-15), "f", "femto")

    @property
    def descriptor(self) -> ScaleDescriptor:
        return self.value

    @property
    def shorthand(self) -> str:
        return self.value.shorthand

    @property
    def alias(self) -> str:
        return self.value.alias

    @staticmethod
    @lru_cache(maxsize=1)
    def all() -> Dict[Tuple[int, int], str]:
        return {(s.value.base, s.value.power): s.name for s in Scale}

    @classmethod
    @lru_cache(maxsize=1)
    def _decimal_scales(cls):
        return [s for s in cls if s.value.base == 10]

    @classmethod
    @lru_cache(maxsize=1)
    def _binary_scales(cls):
        return [s for s in cls if s.value.base == 2]

    @staticmethod
    @lru_cache(maxsize=1)
    def by_value() -> Dict[float, str]:
        """
        Return a map from evaluated numeric value → Scale name.
        Cached after first access.
        """
        return {round(s.value.exponent.evaluated, 15): s.name for s in Scale}

    @classmethod
    def nearest(cls, value: float, include_binary: bool = False, undershoot_bias: float = 0.75) -> "Scale":
        if value == 0:
            return Scale.one
        abs_val = abs(value)
        candidates = list(cls) if include_binary else cls._decimal_scales()

        def distance(scale: "Scale") -> float:
            ratio = abs_val / scale.value.evaluated
            diff = math.log10(ratio)
            if ratio < 1:
                diff /= undershoot_bias
            return abs(diff)

        return min(candidates, key=distance)

    def __eq__(self, other: 'Scale'):
        return self.value.exponent == other.value.exponent

    def __gt__(self, other: 'Scale'):
        return self.value.exponent > other.value.exponent

    def __hash__(self):
        e = self.value.exponent
        return hash((e.base, round(e.power, 12)))

    def __mul__(self, other):
        # --- Case 1: applying Scale to simple Unit --------------------
        if isinstance(other, Unit):
            return UnitProduct({UnitFactor(unit=other, scale=self): 1})

        # --- Case 2: other cases are NOT handled here -----------------
        # UnitProduct scaling is handled solely by UnitProduct.__rmul__
        if isinstance(other, UnitProduct):
            return NotImplemented

        # --- Case 3: Scale * Scale algebra ----------------------------
        if isinstance(other, Scale):
            if self is Scale.one:
                return other
            if other is Scale.one:
                return self

            result = self.value.exponent * other.value.exponent
            include_binary = 2 in {self.value.base, other.value.base}

            if isinstance(result, Exponent):
                match = Scale.all().get(result.parts())
                if match:
                    return Scale[match]

            return Scale.nearest(float(result), include_binary=include_binary)

        return NotImplemented

    def __truediv__(self, other):
        if not isinstance(other, Scale):
            return NotImplemented
        if self == other:
            return Scale.one
        result = self.value.exponent / other.value.exponent
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        include_binary = 2 in {self.value.base, other.value.base}
        return Scale.nearest(float(result), include_binary=include_binary)

    def __pow__(self, power):
        result = self.value.exponent ** power
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        include_binary = self.value.base == 2
        return Scale.nearest(float(result), include_binary=include_binary)


@dataclass(frozen=True)
class Unit:
    """
    Represents a **unit of measure** associated with a :class:`Dimension`.

    A Unit is an atomic symbol with no scale information. Scale is handled
    separately by UnitFactor, which pairs a Unit with a Scale.

    Parameters
    ----------
    name : str
        Canonical name of the unit (e.g., "meter").
    dimension : Dimension
        The physical dimension this unit represents.
    aliases : tuple[str, ...]
        Optional shorthand symbols (e.g., ("m", "M")).
    """
    name: str = ""
    dimension: Dimension = field(default=Dimension.none)
    aliases: tuple[str, ...] = ()

    # ----------------- symbolic helpers -----------------

    @staticmethod
    def _norm(aliases: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize alias bag: drop empty/whitespace-only aliases."""
        return tuple(a for a in aliases if a.strip())

    @property
    def shorthand(self) -> str:
        """
        Symbol used in expressions (e.g., 'm', 's').
        For dimensionless units, returns ''.

        Note: Scale prefixes are handled by UnitFactor.shorthand, not here.
        """
        if self.dimension == Dimension.none:
            return ""
        base = (self.aliases[0] if self.aliases else self.name) or ""
        return base.strip()

    # ----------------- algebra -----------------

    def __mul__(self, other):
        """
        Unit * Unit -> UnitProduct
        Unit * UnitProduct -> UnitProduct
        """
        if isinstance(other, UnitProduct):
            # let UnitProduct handle merging
            return other.__rmul__(self)

        if isinstance(other, Unit):
            return UnitProduct({self: 1, other: 1})

        return NotImplemented

    def __truediv__(self, other):
        """
        Unit / Unit or Unit / UnitProduct => UnitProduct
        """
        if isinstance(other, UnitProduct):
            combined = {self: 1.0}
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) - exp
            return UnitProduct(combined)

        if not isinstance(other, Unit):
            return NotImplemented

        # same physical unit → cancel to dimensionless
        if (
            self.dimension == other.dimension
            and self.name == other.name
            and self._norm(self.aliases) == self._norm(other.aliases)
        ):
            return Unit()  # dimensionless (matches units.none)

        # dividing by dimensionless → no change
        if other.dimension == Dimension.none:
            return self

        # general case: form composite (self^1 * other^-1)
        return UnitProduct({self: 1, other: -1})

    def __pow__(self, power):
        """
        Unit ** n => UnitProduct with that exponent.
        """
        return UnitProduct({self: power})

    # ----------------- equality & hashing -----------------

    def __eq__(self, other):
        if isinstance(other, UnitProduct):
            return other.__eq__(self)
        if not isinstance(other, Unit):
            return NotImplemented
        return (
            self.dimension == other.dimension
            and self.name == other.name
            and self._norm(self.aliases) == self._norm(other.aliases)
        )

    def __hash__(self):
        return hash(
            (
                self.name,
                self._norm(self.aliases),
                self.dimension,
            )
        )

    # ----------------- representation -----------------

    def __repr__(self):
        """
        <Unit m>, <Unit kg>, <Unit>, <Unit | velocity>, etc.
        """
        if self.shorthand:
            return f"<Unit {self.shorthand}>"
        if self.dimension == Dimension.none:
            return "<Unit>"
        return f"<Unit | {self.dimension.name}>"

    # ----------------- callable (creates Number) -----------------

    def __call__(self, quantity: Union[int, float]) -> "Number":
        """Create a Number with this unit.

        Example
        -------
        >>> meter(5)
        <5 m>
        """
        return Number(quantity=quantity, unit=UnitProduct.from_unit(self))


@dataclass(frozen=True)
class UnitFactor:
    """
    A structural pair (unit, scale) used as the *key* inside UnitProduct.

    - `unit` is a plain Unit (no extra meaning beyond dimension + aliases + name).
    - `scale` is the *expression-level* Scale attached by the user (e.g. milli in mL).

    Two UnitFactors are equal iff both `unit` and `scale` are equal, so components
    with the same base unit and same scale truly merge.

    NOTE: We also implement equality / hashing in a way that allows lookups
    by the underlying Unit to keep working:

        m in product.factors
        product.factors[m]

    still work even though the actual keys are UnitFactor instances.
    """

    unit: "Unit"
    scale: "Scale"

    # ------------- Projections (Unit-like surface) -------------------------

    @property
    def dimension(self):
        return self.unit.dimension

    @property
    def aliases(self):
        return getattr(self.unit, "aliases", ())

    @property
    def name(self):
        return getattr(self.unit, "name", "")

    @property
    def shorthand(self) -> str:
        """
        Render something like 'mg' for UnitFactor(gram, milli),
        or 'L' for UnitFactor(liter, one).
        """
        base = ""
        if self.aliases:
            base = self.aliases[0]
        elif self.name:
            base = self.name

        prefix = "" if self.scale is Scale.one else self.scale.shorthand
        return f"{prefix}{base}".strip()

    # ------------- Identity & hashing -------------------------------------

    def __repr__(self) -> str:
        return f"UnitFactor(unit={self.unit!r}, scale={self.scale!r})"

    def __hash__(self) -> int:
        # Important: share hash space with the underlying Unit so that
        # lookups by Unit (e.g., factors[unit]) work against UnitFactor keys.
        return hash(self.unit)

    def __eq__(self, other):
        # UnitFactor vs UnitFactor → structural equality
        if isinstance(other, UnitFactor):
            return (self.unit == other.unit) and (self.scale == other.scale)

        # UnitFactor vs Unit → equal iff underlying unit matches AND
        # this UnitFactor has Scale.one (since Unit has no scale).
        # This lets `unit in factors` work when `factors` is keyed by UnitFactor.
        if isinstance(other, Unit):
            return self.unit == other and self.scale is Scale.one

        return NotImplemented


class UnitProduct:
    """
    Represents a product or quotient of Units.

    Key properties:
    - factors is a dict[UnitFactor, float] mapping (unit, scale) pairs to exponents.
    - Nested UnitProduct instances are flattened.
    - Identical UnitFactors (same underlying unit and same scale) merge exponents.
    - Units with net exponent ~0 are dropped.
    - Dimensionless units (Dimension.none) are dropped.
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

        # -----------------------------------------------------
        # Step 1 — Flatten sources into UnitFactors
        # -----------------------------------------------------
        for key, exp in factors.items():
            if isinstance(key, UnitProduct):
                # Flatten nested UnitProducts
                for inner_fu, inner_exp in key.factors.items():
                    merge_fu(inner_fu, inner_exp * exp)
            else:
                merge_fu(to_factored(key), exp)

        # -----------------------------------------------------
        # Step 2 — Remove exponent-zero & dimensionless UnitFactors
        # -----------------------------------------------------
        simplified: dict[UnitFactor, float] = {}
        for fu, exp in merged.items():
            if abs(exp) < 1e-12:
                continue
            if fu.dimension == Dimension.none:
                continue
            simplified[fu] = exp

        # -----------------------------------------------------
        # Step 3 — Group by base-unit identity (ignoring scale)
        # -----------------------------------------------------
        groups: dict[tuple, dict[UnitFactor, float]] = {}

        for fu, exp in simplified.items():
            alias_key = tuple(sorted(a for a in fu.aliases if a))
            group_key = (fu.name, fu.dimension, alias_key)
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
        self._residual_scale_factor = residual_scale_factor

        # -----------------------------------------------------
        # Step 5 — Derive dimension via exponent algebra
        # -----------------------------------------------------
        self.dimension = reduce(
            lambda acc, item: acc * (item[0].dimension ** item[1]),
            self.factors.items(),
            Dimension.none,
        )

    # ------------- Rendering -------------------------------------------------

    @classmethod
    def _append(cls, unit: Unit, power: float, num: list[str], den: list[str]) -> None:
        """
        Append a unit^power into numerator or denominator list. Works with
        both Unit and UnitFactor, since UnitFactor exposes dimension,
        shorthand, name, and aliases.
        """
        if unit.dimension == Dimension.none:
            return
        part = getattr(unit, "shorthand", "") or getattr(unit, "name", "") or ""
        if not part:
            return
        if power > 0:
            if power == 1:
                num.append(part)
            else:
                num.append(part + str(power).translate(cls._SUPERSCRIPTS))
        elif power < 0:
            if power == -1:
                den.append(part)
            else:
                den.append(part + str(-power).translate(cls._SUPERSCRIPTS))

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
        result = getattr(self, '_residual_scale_factor', 1.0)
        for factor, power in self.factors.items():
            result *= factor.scale.value.evaluated ** power
        return result

    # ------------- Helpers ---------------------------------------------------

    @classmethod
    def from_unit(cls, unit: Unit) -> 'UnitProduct':
        """Wrap a plain Unit as a UnitProduct with Scale.one."""
        return cls({UnitFactor(unit, Scale.one): 1})

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
            return UnitProduct(combined)

        if isinstance(other, UnitProduct):
            combined = self.factors.copy()
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) + exp
            return UnitProduct(combined)

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

            return UnitProduct(combined)

        if isinstance(other, Unit):
            combined: dict[Unit, float] = {other: 1.0}
            for u, e in self.factors.items():
                combined[u] = combined.get(u, 0.0) + e
            return UnitProduct(combined)

        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            combined = self.factors.copy()
            combined[other] = combined.get(other, 0.0) - 1.0
            return UnitProduct(combined)

        if isinstance(other, UnitProduct):
            combined = self.factors.copy()
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) - exp
            return UnitProduct(combined)

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

    def __call__(self, quantity: Union[int, float]) -> "Number":
        """Create a Number with this unit product.

        Example
        -------
        >>> (meter / second)(10)
        <10 m/s>
        """
        return Number(quantity=quantity, unit=self)


# --------------------------------------------------------------------------------------
# Number & Ratio (Value Layer)
# --------------------------------------------------------------------------------------

# Dimensionless unit for use as default in Number
_none = Unit()


Quantifiable = Union['Number', 'Ratio']


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
    """
    quantity: Union[float, int] = 1.0
    unit: Union[Unit, UnitProduct] = None

    def __post_init__(self):
        if self.unit is None:
            object.__setattr__(self, 'unit', _none)

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
            return Number(quantity=self.quantity, unit=self.unit)

        # Compute the combined scale factor
        scale_factor = self.unit.fold_scale()

        # Create new unit with all factors at Scale.one
        base_factors: dict[UnitFactor, float] = {}
        for factor, exp in self.unit.factors.items():
            base_factor = UnitFactor(unit=factor.unit, scale=Scale.one)
            base_factors[base_factor] = exp

        base_unit = UnitProduct(base_factors)

        # Adjust quantity by the scale factor
        return Number(quantity=self.quantity * scale_factor, unit=base_unit)

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
        # Use raw quantity - the conversion map handles scale via factorwise decomposition
        converted_quantity = conversion_map(self.quantity)
        return Number(quantity=converted_quantity, unit=target)

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
            raise TypeError(f"Cannot divide Number by non-Number/Ratio type: {type(other)}")

        # Symbolic quotient in the unit algebra
        unit_quot = self.unit / other.unit

        # --- Case 1: Dimensionless result ----------------------------------
        # If the net dimension is none, we want a pure scalar:
        # fold *all* scale factors into the numeric magnitude.
        if not unit_quot.dimension:
            num = self._canonical_magnitude
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
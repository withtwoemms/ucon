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
- :class:`CompositeUnit` — Product/quotient of Units with simplification and readable rendering.
"""
from __future__ import annotations

import math
from enum import Enum
from functools import lru_cache, reduce, total_ordering
from dataclasses import dataclass
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
    time                = Vector(1, 0, 0, 0, 0, 0, 0)
    length              = Vector(0, 1, 0, 0, 0, 0, 0)
    mass                = Vector(0, 0, 1, 0, 0, 0, 0)
    current             = Vector(0, 0, 0, 1, 0, 0, 0)
    temperature         = Vector(0, 0, 0, 0, 1, 0, 0)
    luminous_intensity  = Vector(0, 0, 0, 0, 0, 1, 0)
    amount_of_substance = Vector(0, 0, 0, 0, 0, 0, 1)
    # ------------------------------------------------

    acceleration = Vector(-2, 1, 0, 0, 0, 0, 0)
    angular_momentum = Vector(-1, 2, 1, 0, 0, 0, 0)
    area = Vector(0, 2, 0, 0, 0, 0, 0)
    capacitance = Vector(4, -2, -1, 2, 0, 0, 0)
    charge = Vector(1, 0, 0, 1, 0, 0, 0)
    conductance = Vector(3, -2, -1, 2, 0, 0, 0)
    conductivity = Vector(3, -3, -1, 2, 0, 0, 0)
    density = Vector(0, -3, 1, 0, 0, 0, 0)
    electric_field_strength = Vector(-3, 1, 1, -1, 0, 0, 0)
    energy = Vector(-2, 2, 1, 0, 0, 0, 0)
    entropy = Vector(-2, 2, 1, 0, -1, 0, 0)
    force = Vector(-2, 1, 1, 0, 0, 0, 0)
    frequency = Vector(-1, 0, 0, 0, 0, 0, 0)
    gravitation = Vector(-2, 3, -1, 0, 0, 0, 0)
    illuminance = Vector(0, -2, 0, 0, 0, 1, 0)
    inductance = Vector(-2, 2, 1, -2, 0, 0, 0)
    magnetic_flux = Vector(-2, 2, 1, -1, 0, 0, 0)
    magnetic_flux_density = Vector(-2, 0, 1, -1, 0, 0, 0)
    magnetic_permeability = Vector(-2, 1, 1, -2, 0, 0, 0)
    molar_mass = Vector(0, 0, 1, 0, 0, 0, -1)
    molar_volume = Vector(0, 3, 0, 0, 0, 0, -1)
    momentum = Vector(-1, 1, 1, 0, 0, 0, 0)
    permittivity = Vector(4, -3, -1, 2, 0, 0, 0)
    power = Vector(-3, 2, 1, 0, 0, 0, 0)
    pressure = Vector(-2, -1, 1, 0, 0, 0, 0)
    resistance = Vector(-3, 2, 1, -2, 0, 0, 0)
    resistivity = Vector(-3, 3, 1, -2, 0, 0, 0)
    specific_heat_capacity = Vector(-2, 2, 0, 0, -1, 0, 0)
    thermal_conductivity = Vector(-3, 1, 1, 0, -1, 0, 0)
    velocity = Vector(-1, 1, 0, 0, 0, 0, 0)
    voltage = Vector(-3, 2, 1, -1, 0, 0, 0)
    volume = Vector(0, 3, 0, 0, 0, 0, 0)

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
        if isinstance(other, Unit) and not isinstance(other, CompositeUnit):
            if getattr(other, "scale", Scale.one) is not Scale.one:
                raise ValueError(f"Cannot apply {self} to already scaled unit {other}")
            return Unit(
                *other.aliases,
                name=other.name,
                dimension=other.dimension,
                scale=self,
            )

        # --- Case 2: other cases are NOT handled here -----------------
        # CompositeUnit scaling is handled solely by CompositeUnit.__rmul__
        if isinstance(other, CompositeUnit):
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


class Unit:
    """
    Represents a **unit of measure** associated with a :class:`Dimension`.

    Parameters
    ----------
    *aliases : str
        Optional shorthand symbols (e.g., "m", "sec").
    name : str
        Canonical name of the unit (e.g., "meter").
    dimension : Dimension
        The physical dimension this unit represents.
    scale : Scale
        Magnitude prefix (kilo, milli, etc.).
    """
    def __init__(
        self,
        *aliases: str,
        name: str = "",
        dimension: Dimension = Dimension.none,
        scale: Scale = Scale.one,
    ):
        self.aliases = aliases
        self.name = name
        self.dimension = dimension
        self.scale = scale

    # ----------------- symbolic helpers -----------------

    def _norm(self, aliases: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize alias bag: drop empty/whitespace-only aliases."""
        return tuple(a for a in aliases if a.strip())

    @property
    def shorthand(self) -> str:
        """
        Symbol used in expressions (e.g., 'kg', 'm', 's').
        For dimensionless units, returns ''.
        """
        if self.dimension == Dimension.none:
            return ""
        prefix = getattr(self.scale, "shorthand", "") or ""
        base = (self.aliases[0] if self.aliases else self.name) or ""
        return f"{prefix}{base}".strip()

    # ----------------- algebra -----------------

    def __mul__(self, other):
        """
        Unit * Unit -> CompositeUnit
        Unit * CompositeUnit -> CompositeUnit
        """
        from ucon.core import CompositeUnit  # local import to avoid circulars

        if isinstance(other, CompositeUnit):
            # let CompositeUnit handle merging
            return other.__rmul__(self)

        if isinstance(other, Unit):
            return CompositeUnit({self: 1, other: 1})

        return NotImplemented

    def __rmul__(self, other):
        """
        Scale * Unit -> scaled Unit

        NOTE:
        - Only allow applying a Scale to an unscaled Unit.
        - CompositeUnit scale handling is done in CompositeUnit.__rmul__.
        """
        if isinstance(other, Scale):
            if self.scale is not Scale.one:
                raise ValueError(f"Cannot apply {other} to already scaled unit {self}")
            return Unit(
                *self.aliases,
                name=self.name,
                dimension=self.dimension,
                scale=other,
            )
        return NotImplemented

    def __truediv__(self, other):
        """
        Unit / Unit:
          - If same unit => dimensionless Unit()
          - If denominator is dimensionless => self
          - Else => CompositeUnit
        """
        from ucon.core import CompositeUnit  # local import

        if not isinstance(other, Unit):
            return NotImplemented

        # same physical unit → cancel to dimensionless
        if (
            self.dimension == other.dimension
            and self.scale == other.scale
            and self.name == other.name
            and self._norm(self.aliases) == self._norm(other.aliases)
        ):
            return Unit()  # dimensionless (matches units.none)

        # dividing by dimensionless → no change
        if other.dimension == Dimension.none:
            return self

        # general case: form composite (self^1 * other^-1)
        return CompositeUnit({self: 1, other: -1})

    def __pow__(self, power):
        """
        Unit ** n => CompositeUnit with that exponent.
        """
        from ucon.core import CompositeUnit  # local import

        return CompositeUnit({self: power})

    # ----------------- equality & hashing -----------------

    def __eq__(self, other):
        if not isinstance(other, Unit):
            return NotImplemented
        return (
            self.dimension == other.dimension
            and self.scale == other.scale
            and self.name == other.name
            and self._norm(self.aliases) == self._norm(other.aliases)
        )

    def __hash__(self):
        return hash(
            (
                self.name,
                self._norm(self.aliases),
                self.dimension,
                self.scale,
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


from dataclasses import dataclass

@dataclass(frozen=True)
class FactoredUnit:
    """
    A structural pair (unit, scale) used as the *key* inside CompositeUnit.

    - `unit` is a plain Unit (no extra meaning beyond dimension + aliases + name).
    - `scale` is the *expression-level* Scale attached by the user (e.g. milli in mL).

    Two FactoredUnits are equal iff both `unit` and `scale` are equal, so components
    with the same base unit and same scale truly merge.

    NOTE: We also implement equality / hashing in a way that allows lookups
    by the underlying Unit to keep working:

        m in composite.components
        composite.components[m]

    still work even though the actual keys are FactoredUnit instances.
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
        Render something like 'mg' for FactoredUnit(gram, milli),
        or 'L' for FactoredUnit(liter, one).
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
        return f"FactoredUnit(unit={self.unit!r}, scale={self.scale!r})"

    def __hash__(self) -> int:
        # Important: share hash space with the underlying Unit so that
        # lookups by Unit (e.g., components[unit]) work against FactoredUnit keys.
        return hash(self.unit)

    def __eq__(self, other):
        # FactoredUnit vs FactoredUnit → structural equality
        if isinstance(other, FactoredUnit):
            return (self.unit == other.unit) and (self.scale == other.scale)

        # FactoredUnit vs Unit → equal iff underlying unit matches and the
        # Unit's own scale matches our scale. This lets `unit in components`
        # work when `components` is keyed by FactoredUnit.
        if isinstance(other, Unit):
            return (
                self.unit == other
                and getattr(other, "scale", Scale.one) == self.scale
            )

        return NotImplemented


class CompositeUnit(Unit):
    """
    Represents a product or quotient of Units.

    Key properties:
    - components is a dict[FactoredUnit, float] mapping (unit, scale) pairs to exponents.
    - Nested CompositeUnit instances are flattened.
    - Identical factored units (same underlying unit and same scale) merge exponents.
    - Units with net exponent ~0 are dropped.
    - Dimensionless units (Dimension.none) are dropped.
    - Scaled variants of the same base unit (e.g. L and mL) are grouped by
      (name, dimension, aliases) and their exponents combined; if the net exponent
      is ~0, the whole group is cancelled.
    """

    _SUPERSCRIPTS = str.maketrans("0123456789-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻·")

    def __init__(self, components: dict[Unit, float]):
        """
        Build a CompositeUnit with FactoredUnit keys, preserving user-provided scales.

        Key principles:
        - Never canonicalize scale (no implicit preference for Scale.one).
        - Only collapse scaled variants of the same base unit when total exponent == 0.
        - If only one scale variant exists in a group, preserve it exactly.
        - If multiple variants exist and the group exponent != 0, preserve the FIRST
        encountered FactoredUnit (keeps user-intent scale).
        """

        # CompositeUnit always starts dimensionless & unscaled
        super().__init__(name="", dimension=Dimension.none, scale=Scale.one)
        self.aliases = ()

        merged: dict[FactoredUnit, float] = {}

        # -----------------------------------------------------
        # Helper: normalize Units or FactoredUnits to FactoredUnit
        # -----------------------------------------------------
        def to_factored(unit_or_fu):
            if isinstance(unit_or_fu, FactoredUnit):
                return unit_or_fu
            scale = getattr(unit_or_fu, "scale", Scale.one)
            return FactoredUnit(unit_or_fu, scale)

        # -----------------------------------------------------
        # Helper: merge FactoredUnits by full (unit, scale) identity
        # -----------------------------------------------------
        def merge_fu(fu: FactoredUnit, exponent: float):
            for existing in merged:
                if existing == fu:     # FactoredUnit.__eq__ handles scale & unit compare
                    merged[existing] += exponent
                    return
            merged[fu] = merged.get(fu, 0.0) + exponent

        # -----------------------------------------------------
        # Step 1 — Flatten sources into FactoredUnits
        # -----------------------------------------------------
        for key, exp in components.items():
            if isinstance(key, CompositeUnit):
                # Flatten nested composites
                for inner_fu, inner_exp in key.components.items():
                    merge_fu(inner_fu, inner_exp * exp)
            else:
                merge_fu(to_factored(key), exp)

        # -----------------------------------------------------
        # Step 2 — Remove exponent-zero & dimensionless FactoredUnits
        # -----------------------------------------------------
        simplified: dict[FactoredUnit, float] = {}
        for fu, exp in merged.items():
            if abs(exp) < 1e-12:
                continue
            if fu.dimension == Dimension.none:
                continue
            simplified[fu] = exp

        # -----------------------------------------------------
        # Step 3 — Group by base-unit identity (ignoring scale)
        # -----------------------------------------------------
        groups: dict[tuple, dict[FactoredUnit, float]] = {}

        for fu, exp in simplified.items():
            alias_key = tuple(sorted(a for a in fu.aliases if a))
            group_key = (fu.name, fu.dimension, alias_key)
            groups.setdefault(group_key, {})
            groups[group_key][fu] = groups[group_key].get(fu, 0.0) + exp

        # -----------------------------------------------------
        # Step 4 — Resolve groups while preserving user scale
        # -----------------------------------------------------
        final: dict[FactoredUnit, float] = {}

        for group_key, bucket in groups.items():
            total_exp = sum(bucket.values())

            # 4A — Full cancellation
            if abs(total_exp) < 1e-12:
                continue

            # 4B — Only one scale variant → preserve exactly
            if len(bucket) == 1:
                fu, exp = next(iter(bucket.items()))
                final[fu] = exp
                continue

            # 4C — Multiple scale variants, exponent != 0:
            #      preserve FIRST encountered FactoredUnit.
            #      This ensures user scale is preserved.
            first_fu = next(iter(bucket.keys()))
            final[first_fu] = total_exp

        self.components = final

        # CompositeUnit itself has no global scale
        self.scale = Scale.one

        # -----------------------------------------------------
        # Step 5 — Derive dimension via exponent algebra
        # -----------------------------------------------------
        self.dimension = reduce(
            lambda acc, item: acc * (item[0].dimension ** item[1]),
            self.components.items(),
            Dimension.none,
        )

    # ------------- Rendering -------------------------------------------------

    @classmethod
    def _append(cls, unit: Unit, power: float, num: list[str], den: list[str]) -> None:
        """
        Append a unit^power into numerator or denominator list. Works with
        both Unit and FactoredUnit, since FactoredUnit exposes dimension,
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
        if not self.components:
            return ""

        num: list[str] = []
        den: list[str] = []

        for u, power in self.components.items():
            self._append(u, power, num, den)

        numerator = "·".join(num) or "1"
        denominator = "·".join(den)
        if not denominator:
            return numerator
        return f"{numerator}/{denominator}"

    # ------------- Algebra ---------------------------------------------------

    def __mul__(self, other):
        if isinstance(other, Unit):
            combined = self.components.copy()
            combined[other] = combined.get(other, 0.0) + 1.0
            return CompositeUnit(combined)

        if isinstance(other, CompositeUnit):
            combined = self.components.copy()
            for u, exp in other.components.items():
                combined[u] = combined.get(u, 0.0) + exp
            return CompositeUnit(combined)

        if isinstance(other, Scale):
            # respect the convention: Scale * Unit, not Unit * Scale
            return NotImplemented

        return NotImplemented

    def __rmul__(self, other):
        # Scale * CompositeUnit → apply scale to a canonical sink unit
        if isinstance(other, Scale):
            if not self.components:
                return self

            # heuristic: choose unit with positive exponent first, else first unit
            items = list(self.components.items())
            positives = [(u, e) for (u, e) in items if e > 0]
            sink, _ = (positives or items)[0]

            # Normalize sink into a FactoredUnit
            if isinstance(sink, FactoredUnit):
                sink_fu = sink
            else:
                sink_fu = FactoredUnit(
                    unit=sink,
                    scale=getattr(sink, "scale", Scale.one),
                )

            # Combine scales (expression-level)
            if sink_fu.scale is not Scale.one:
                new_scale = other * sink_fu.scale
            else:
                new_scale = other

            scaled_sink = FactoredUnit(
                unit=sink_fu.unit,
                scale=new_scale,
            )

            combined: dict[FactoredUnit, float] = {}
            for u, exp in self.components.items():
                # Normalize each key into FactoredUnit as we go
                if isinstance(u, FactoredUnit):
                    fu = u
                else:
                    fu = FactoredUnit(
                        unit=u,
                        scale=getattr(u, "scale", Scale.one),
                    )

                if fu is sink_fu:
                    combined[scaled_sink] = combined.get(scaled_sink, 0.0) + exp
                else:
                    combined[fu] = combined.get(fu, 0.0) + exp

            return CompositeUnit(combined)

        if isinstance(other, Unit):
            combined: dict[Unit, float] = {other: 1.0}
            for u, e in self.components.items():
                combined[u] = combined.get(u, 0.0) + e
            return CompositeUnit(combined)

        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            combined = self.components.copy()
            combined[other] = combined.get(other, 0.0) - 1.0
            return CompositeUnit(combined)

        if isinstance(other, CompositeUnit):
            combined = self.components.copy()
            for u, exp in other.components.items():
                combined[u] = combined.get(u, 0.0) - exp
            return CompositeUnit(combined)

        return NotImplemented

    # ------------- Identity & hashing ---------------------------------------

    def __repr__(self):
        return f"<CompositeUnit {self.shorthand}>"

    def __eq__(self, other):
        if isinstance(other, Unit) and not isinstance(other, CompositeUnit):
            # Only equal to a plain Unit if we have exactly that unit^1
            # Here, the tuple comparison will invoke FactoredUnit.__eq__(Unit)
            # on the key when components are keyed by FactoredUnit.
            return len(self.components) == 1 and list(self.components.items()) == [(other, 1.0)]
        return isinstance(other, CompositeUnit) and self.components == other.components

    def __hash__(self):
        # Sort by name; FactoredUnit exposes .name, so this is stable.
        return hash(tuple(sorted(self.components.items(), key=lambda x: x[0].name)))

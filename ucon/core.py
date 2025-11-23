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
            raise TypeError(f"Cannot compare Unit with non-Unit type: {type(other)}")
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


class CompositeUnit(Unit):
    """
    Represents a product or quotient of Units.

    Key properties:
    - components is a dict[Unit, float] mapping units (with full scale) to exponents.
    - Nested CompositeUnit instances are flattened.
    - Identical units (same dimension, name, aliases, *and scale*) merge exponents.
    - Units with net exponent ~0 are dropped.
    - Dimensionless units (Dimension.none) are dropped.
    - Scaled variants of the same base unit (e.g. L and mL) are
      grouped by (name, dimension, aliases) and their exponents combined;
      if the net exponent is ~0, the whole group is cancelled.
    """

    _SUPERSCRIPTS = str.maketrans("0123456789-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻·")

    def __init__(self, components: dict[Unit, float]):
        # Base Unit construction; CompositeUnit itself always starts
        # as dimensionless with scale=one, then we derive from components.
        super().__init__(name="", dimension=Dimension.none, scale=Scale.one)
        self.aliases = ()

        merged: dict[Unit, float] = {}

        def merge_unit(unit: Unit, exponent: float) -> None:
            # Only merge truly identical units, including scale
            existing = next(
                (
                    k
                    for k in merged
                    if (
                        k.dimension == unit.dimension
                        and getattr(k, "scale", Scale.one) == getattr(unit, "scale", Scale.one)
                        and getattr(k, "aliases", ()) == getattr(unit, "aliases", ())
                        and getattr(k, "name", "") == getattr(unit, "name", "")
                    )
                ),
                None,
            )
            if existing is not None:
                merged[existing] += exponent
            else:
                merged[unit] = exponent

        # 1. Flatten nested CompositeUnits and sum exponents
        for unit, exponent in components.items():
            if isinstance(unit, CompositeUnit):
                for inner_unit, inner_exponent in unit.components.items():
                    merge_unit(inner_unit, inner_exponent * exponent)
            else:
                merge_unit(unit, exponent)

        # 2. Drop near-zero exponents and dimensionless units
        simplified: dict[Unit, float] = {}
        for unit, exponent in merged.items():
            if abs(exponent) < 1e-12:
                continue
            if unit.dimension == Dimension.none:
                # dimensionless factors do not affect composite structure
                continue
            simplified[unit] = exponent

        # 3. Group scaled variants of the same base unit and cancel when net exponent ~0
        #    Key is (name, dimension, aliases-without-empty), ignoring scale.
        groups: dict[tuple, dict[Unit, float]] = {}
        for unit, exponent in simplified.items():
            alias_key = tuple(sorted(a for a in unit.aliases if a))
            key = (unit.name, unit.dimension, alias_key)
            bucket = groups.setdefault(key, {})
            bucket[unit] = bucket.get(unit, 0.0) + exponent

        final: dict[Unit, float] = {}
        for key, bucket in groups.items():
            total_exp = sum(bucket.values())
            if abs(total_exp) < 1e-12:
                # Net exponent cancels for all scaled variants of this base unit.
                # Example: L^-1 and mL^1 → 0 → drop the entire group.
                continue

            # Pick a representative unit for this group:
            #  - Prefer unscaled (Scale.one) if present
            #  - Otherwise take a stable choice (by name)
            rep: Unit | None = None
            for u in bucket:
                if getattr(u, "scale", Scale.one) is Scale.one:
                    rep = u
                    break
            if rep is None:
                rep = sorted(bucket.keys(), key=lambda u: u.name)[0]

            final[rep] = total_exp

        self.components = final
        self.scale = Scale.one  # CompositeUnit itself has no global scale

        # 4. Compute resulting dimension via exponent algebra
        self.dimension = reduce(
            lambda acc, kv: acc * (kv[0].dimension ** kv[1]),
            self.components.items(),
            Dimension.none,
        )

    # ------------- Rendering -------------------------------------------------

    @classmethod
    def _append(cls, unit: Unit, power: float, num: list[str], den: list[str]) -> None:
        if unit.dimension == Dimension.none:
            return
        part = unit.shorthand or unit.name or ""
        if not part:
            return
        if power > 0:
            if power == 1:
                num.append(part)
            else:
                num.append(f"{part}{str(power).translate(cls._SUPERSCRIPTS)}")
        elif power < 0:
            abs_p = abs(power)
            if abs_p == 1:
                den.append(part)
            else:
                den.append(f"{part}{str(abs_p).translate(cls._SUPERSCRIPTS)}")

    @property
    def shorthand(self) -> str:
        """Return symbolic shorthand like 'kg·m/s²'."""
        if not self.components:
            return ""
        num: list[str] = []
        den: list[str] = []
        for unit, power in self.components.items():
            self._append(unit, power, num, den)

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
            sink_unit, _ = (positives or items)[0]

            # Apply scale directly to that unit (no exponent-based scaling)
            if getattr(sink_unit, "scale", Scale.one) is not Scale.one:
                scaled_sink = Unit(
                    *sink_unit.aliases,
                    name=sink_unit.name,
                    dimension=sink_unit.dimension,
                    scale=other * sink_unit.scale,
                )
            else:
                scaled_sink = Unit(
                    *sink_unit.aliases,
                    name=sink_unit.name,
                    dimension=sink_unit.dimension,
                    scale=other,
                )

            combined: dict[Unit, float] = {}
            for u, exp in self.components.items():
                if u is sink_unit:
                    combined[scaled_sink] = combined.get(scaled_sink, 0.0) + exp
                else:
                    combined[u] = combined.get(u, 0.0) + exp

            return CompositeUnit(combined)

        if isinstance(other, Unit):
            combined = {other: 1.0}
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
            return len(self.components) == 1 and list(self.components.items()) == [(other, 1.0)]
        return isinstance(other, CompositeUnit) and self.components == other.components

    def __hash__(self):
        return hash(tuple(sorted(self.components.items(), key=lambda x: x[0].name)))

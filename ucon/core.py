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
        if isinstance(other, CompositeUnit):
            return other.__rmul__(self)

        if isinstance(other, Unit):
            if getattr(other, "scale", Scale.one) is not Scale.one:
                raise ValueError(f"Cannot apply {self.name or self.alias} to already scaled unit {other}")
            return Unit(*other.aliases, name=other.name, dimension=other.dimension, scale=self)

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


class Unit:
    def __init__(self, *aliases: str, name: str = '', dimension: Dimension = Dimension.none, scale: Scale = Scale.one):
        self.aliases = aliases
        self.name = name
        self.dimension = dimension
        self.scale = scale

    @property
    def shorthand(self) -> str:
        if self.dimension == Dimension.none:
            return ""
        prefix = getattr(self.scale, "shorthand", "") or ""
        base = (self.aliases[0] if self.aliases else self.name) or ""
        return f"{prefix}{base}".strip()

    def __mul__(self, other):
        if isinstance(other, Unit):
            return CompositeUnit({self: 1, other: 1})
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, Scale):
            return other * self
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            if other.dimension == Dimension.none:
                return self
            if self == other:
                return Unit("", name="", dimension=Dimension.none)
            return CompositeUnit({self: 1, other: -1})
        return NotImplemented

    def __pow__(self, power):
        return CompositeUnit({self: power})

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
        return hash((self.name, self._norm(self.aliases), self.dimension, self.scale))

    def __repr__(self):
        if self.shorthand:  # clear unit name → don't show dimension
            return f"<Unit {self.shorthand}>"
        if self.dimension == Dimension.none:
            return "<Unit>"
        return f"<Unit | {self.dimension.name}>"

    def _norm(self, aliases: tuple[str]):
        return tuple(a for a in aliases if a.strip())


class CompositeUnit(Unit):
    _SUPERSCRIPTS = str.maketrans("0123456789-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻·")

    def __init__(self, components: dict[Unit, int]):
        super().__init__(name="", dimension=Dimension.none, scale=Scale.one)
        self.aliases = ()

        # 1) Merge like components (preserving current unit objects)
        merged: dict[Unit, float] = {}

        def merge_unit(unit: Unit, exponent: float) -> None:
            existing = next(
                (
                    k
                    for k in merged
                    if k.dimension == unit.dimension
                    and getattr(k, "scale", Scale.one) == getattr(unit, "scale", Scale.one)
                    and getattr(k, "aliases", ()) == getattr(unit, "aliases", ())
                    and getattr(k, "name", "") == getattr(unit, "name", "")
                ),
                None,
            )
            if existing is not None:
                merged[existing] += exponent
            else:
                merged[unit] = exponent

        for unit, exponent in components.items():
            if isinstance(unit, CompositeUnit):
                for inner_unit, inner_exponent in unit.components.items():
                    merge_unit(inner_unit, inner_exponent * exponent)
            else:
                merge_unit(unit, exponent)

        # 2) Drop tiny exponents and dimensionless factors
        merged = {
            u: e for u, e in merged.items()
            if abs(e) >= 1e-12 and u.dimension != Dimension.none
        }

        # 3) Unify all component scales into a single total Scale,
        #    while stripping scales from individual units.
        total_scale = Scale.one
        normalized: dict[Unit, float] = {}

        for u, e in merged.items():
            # add unit w/ Scale.one to normalized bag
            base_u = Unit(*u.aliases, name=u.name, dimension=u.dimension, scale=Scale.one)
            normalized[base_u] = normalized.get(base_u, 0) + e

            # accumulate this unit's scale e times into total_scale
            if u.scale is not Scale.one:
                # exponents are expected integers in unit algebra
                n = int(e) if float(e).is_integer() else None
                if n is not None:
                    if n > 0:
                        for _ in range(n):
                            total_scale = total_scale * u.scale
                    elif n < 0:
                        for _ in range(-n):
                            total_scale = total_scale / u.scale
                else:
                    # non-integer exponents: best effort — apply once (common in roots)
                    total_scale = total_scale * u.scale

        # 4) Assign normalized components
        self.components = normalized or {}
        self.scale = Scale.one

        # 5) Apply the unified scale to a single sink component (if any)
        if self.components and total_scale is not Scale.one:
            sink = self._pick_scale_sink()
            new_components: dict[Unit, float] = {}
            for u, e in self.components.items():
                if u is sink:
                    scaled_sink = total_scale * u  # safe: u has Scale.one
                    new_components[scaled_sink] = new_components.get(scaled_sink, 0) + e
                else:
                    new_components[u] = new_components.get(u, 0) + e
            self.components = new_components

        # 6) Compute resulting dimension
        self.dimension = reduce(
            lambda acc, kv: acc * (kv[0].dimension ** kv[1]),
            self.components.items(),
            Dimension.none,
        )

        # 7) Anneal: if single unit to the power of 1, collapse to that Unit
        if len(self.components) == 1:
            (only_u, only_p), = self.components.items()
            if abs(only_p - 1) < 1e-12:
                self.__class__ = only_u.__class__
                self.__dict__.clear()
                self.__dict__.update(only_u.__dict__)
                return

    @classmethod
    def _append(cls, unit: Unit, power: int | float, num: list, den: list):
        if unit.dimension == Dimension.none:
            return
        part = unit.shorthand or unit.name or ""
        if power > 0:
            num.append(f"{part}{str(power).translate(cls._SUPERSCRIPTS)}" if power != 1 else part)
        elif power < 0:
            abs_p = abs(power)
            den.append(f"{part}{str(abs_p).translate(cls._SUPERSCRIPTS)}" if abs_p != 1 else part)

    @property
    def shorthand(self):
        if not self.components:
            return ""
        num, den = [], []
        for unit, power in self.components.items():
            self._append(unit, power, num, den)
        numerator = "·".join(num) or "1"
        denominator = "·".join(den)
        if not denominator:
            return numerator
        return f"{numerator}/{denominator}"

    def _pick_scale_sink(self) -> Unit | None:
        if not self.components:
            return None
        items = list(self.components.items())
        pos = [(u, e) for (u, e) in items if e > 0]
        pool = pos if pos else items
        pool.sort(key=lambda ue: (-abs(ue[1]), getattr(ue[0], "name", "")))
        return pool[0][0]

    def __mul__(self, other):
        if isinstance(other, Unit):
            combined = self.components.copy()
            combined[other] = combined.get(other, 0) + 1
            return CompositeUnit(combined)
        if isinstance(other, CompositeUnit):
            combined = self.components.copy()
            for u, exp in other.components.items():
                combined[u] = combined.get(u, 0) + exp
            return CompositeUnit(combined)
        if isinstance(other, Scale):
            return other * self
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, Unit):
            combined = {other: 1}
            for u, e in self.components.items():
                combined[u] = combined.get(u, 0) + e
            return CompositeUnit(combined)
        if isinstance(other, Scale):
            sink = self._pick_scale_sink()
            if sink is None:
                return self
            combined = {}
            for u, e in self.components.items():
                if u is sink:
                    base_unscaled = Unit(*u.aliases, name=u.name, dimension=u.dimension, scale=Scale.one)
                    scaled_sink = other * base_unscaled
                    combined[scaled_sink] = combined.get(scaled_sink, 0) + e
                else:
                    combined[u] = combined.get(u, 0) + e
            return CompositeUnit(combined)
        if isinstance(other, CompositeUnit):
            return other * self
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            if other.dimension == Dimension.none:
                return self
            combined = self.components.copy()
            combined[other] = combined.get(other, 0) - 1
            return CompositeUnit(combined)
        if isinstance(other, CompositeUnit):
            if all(u.dimension == Dimension.none for u in other.components):
                return self
            combined = self.components.copy()
            for u, exp in other.components.items():
                combined[u] = combined.get(u, 0) - exp
            return CompositeUnit(combined)
        return NotImplemented

    def __repr__(self):
        return f"<CompositeUnit {self.shorthand}>"

    def __eq__(self, other):
        if isinstance(other, Unit):
            return len(self.components) == 1 and next(iter(self.components.items())) == (other, 1)
        return isinstance(other, CompositeUnit) and self.components == other.components

    def __hash__(self):
        return hash(tuple(sorted(self.components.items(), key=lambda x: x[0].name)))

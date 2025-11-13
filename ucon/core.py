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

Together these classes enable dimensional arithmetic, prefix composition, and unit
construction with explicit, canonical semantics.
"""
from dataclasses import dataclass
import math
from enum import Enum
from functools import lru_cache, reduce
from typing import Dict, Tuple, Union

from ucon.algebra import Exponent, Vector


class Dimension(Enum):
    """
    Represents a **physical dimension** defined by a :class:`Vector`.

    Each dimension corresponds to a distinct combination of base exponents.
    Dimensions are algebraically composable via multiplication and division:

        >>> Dimension.length / Dimension.time
        <Dimension.velocity: Vector(T=-1, L=1, M=0, I=0, Θ=0, J=0, N=0)>

    This algebra forms the foundation for unit compatibility and conversion.
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
        """
        Try to map a Vector to a known Dimension; if not found,
        return a dynamic Dimension-like object.
        """
        for dim in cls:
            if dim.value == vector:
                return dim

        # -- fallback: dynamic Dimension-like instance --
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
        """
        Raise a Dimension to a power.

        Example:
            >>> Dimension.length ** 2   # area
            >>> Dimension.time ** -1    # frequency
        """
        if power == 1:
            return self
        if power == 0:
            return Dimension.none

        new_vector = self.value * power   # element-wise scalar multiply
        return self._resolve(new_vector)

    def __eq__(self, dimension) -> bool:
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot compare Dimension with non-Dimension type: {type(dimension)}")
        return self.value == dimension.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class ScaleDescriptor:
    exponent: Exponent
    shorthand: str
    alias: str

    @property
    def evaluated(self):
        return self.exponent.evaluated

    @property
    def base(self):
        return self.exponent.base

    @property
    def power(self):
        return self.exponent.power

    def __repr__(self):
        return f"<ScaleDescriptor {self.alias or self.shorthand or '1'}: {self.base}^{self.power}>"


class Scale(Enum):
    """
    Enumerates common **magnitude prefixes** for units and quantities.

    Examples include:
    - Binary prefixes (kibi, mebi)
    - Decimal prefixes (milli, kilo, mega)

    Each entry stores its numeric scaling factor (e.g., `kilo = 10³`).
    """
    gibi  = ScaleDescriptor(Exponent(2, 30), 'Gi', 'gibi')
    mebi  = ScaleDescriptor(Exponent(2, 20), 'Mi', 'mebi')
    kibi  = ScaleDescriptor(Exponent(2, 10), 'Ki', 'kibi')

    peta = ScaleDescriptor(Exponent(10, 15), 'P', 'peta')
    tera  = ScaleDescriptor(Exponent(10, 12), 'T', 'tera')
    giga  = ScaleDescriptor(Exponent(10, 9), 'G', 'giga')
    mega  = ScaleDescriptor(Exponent(10, 6), 'M', 'mega')
    kilo  = ScaleDescriptor(Exponent(10, 3), 'k', 'kilo')
    hecto = ScaleDescriptor(Exponent(10, 2), 'h', 'hecto')
    deca  = ScaleDescriptor(Exponent(10, 1), 'da', 'deca')
    one   = ScaleDescriptor(Exponent(10, 0), '', '')
    deci  = ScaleDescriptor(Exponent(10,-1), 'd', 'deci')
    centi = ScaleDescriptor(Exponent(10,-2), 'c', 'centi')
    milli = ScaleDescriptor(Exponent(10,-3), 'm', 'milli')
    micro = ScaleDescriptor(Exponent(10,-6), 'µ', 'micro')
    nano  = ScaleDescriptor(Exponent(10,-9), 'n', 'nano')
    pico  = ScaleDescriptor(Exponent(10,-12), 'p', 'pico')
    femto = ScaleDescriptor(Exponent(10,-15), 'f', 'femto')

    @staticmethod
    @lru_cache(maxsize=1)
    def all() -> Dict[Tuple[int, int], str]:
        """Return a map from (base, power) → Scale name."""
        return {(s.value.exponent.base, s.value.exponent.power): s.name for s in Scale}

    @staticmethod
    @lru_cache(maxsize=1)
    def by_value() -> Dict[float, str]:
        """
        Return a map from evaluated numeric value → Scale name.
        Cached after first access.
        """
        return {round(s.value.exponent.evaluated, 15): s.name for s in Scale}

    @classmethod
    @lru_cache(maxsize=1)
    def _decimal_scales(cls):
        """Return decimal (base-10) scales only."""
        return list(s for s in cls if s.value.exponent.base == 10)

    @classmethod
    @lru_cache(maxsize=1)
    def _binary_scales(cls):
        """Return binary (base-2) scales only."""
        return list(s for s in cls if s.value.exponent.base == 2)

    @classmethod
    def nearest(cls, value: float, include_binary: bool = False, undershoot_bias: float = 0.75) -> "Scale":
        """
        Return the Scale that best normalizes `value` toward 1 in log-space.
        Optionally restricts to base-10 prefixes unless `include_binary=True`.
        """
        if value == 0:
            return Scale.one

        abs_val = abs(value)
        candidates = cls._decimal_scales() if not include_binary else list(cls)

        def distance(scale: "Scale") -> float:
            ratio = abs_val / scale.value.exponent.evaluated
            diff = math.log10(ratio)
            # Bias overshoots slightly more than undershoots
            if ratio < 1:
                diff /= undershoot_bias
            return abs(diff)

        return min(candidates, key=distance)

    def __mul__(self, other: Union['Scale', 'Unit']):
        """
        Multiply two Scales together.

        Always returns a `Scale`, representing the resulting order of magnitude.
        If no exact prefix match exists, returns the nearest known Scale.
        """
        # 1️⃣ Handle CompositeUnit first (it subclasses Unit)
        if isinstance(other, CompositeUnit):
            return other.__rmul__(self)

        # 2️⃣ Apply this scale to a plain Unit
        if isinstance(other, Unit):
            # Forbid double-prefixing
            if getattr(other, "scale", Scale.one) is not Scale.one:
                raise ValueError(
                    f"Cannot apply {self.name or self.alias} "
                    f"to already scaled unit {other}"
                )
            return Unit(
                *other.aliases,
                name=other.name,
                dimension=other.dimension,
                scale=self,
            )

        # 3️⃣ Multiply two Scales — quantize to nearest
        if isinstance(other, Scale):
            if self is Scale.one:
                return other
            if other is Scale.one:
                return self

            result = self.value.exponent * other.value.exponent  # delegates to Exponent.__mul__
            include_binary = 2 in {self.value.exponent.base, other.value.exponent.base}

            if isinstance(result, Exponent):
                match = Scale.all().get(result.parts())
                if match:
                    return Scale[match]

            # Quantize to the nearest known scale
            return Scale.nearest(float(result), include_binary=include_binary)

        # 4️⃣ Anything else → not supported
        return NotImplemented
    def __mul__(self, other: Union['Scale', 'Unit']):
        # Handle CompositeUnit FIRST (because it's a subclass of Unit)
        if isinstance(other, CompositeUnit):
            return other.__rmul__(self)

        # Then handle plain Unit
        if isinstance(other, Unit):
            if getattr(other, "scale", Scale.one) is not Scale.one:
                raise ValueError(f"Cannot apply {self.name or self.alias} to already scaled unit {other}")
            return Unit(*other.aliases,
                        name=other.name,
                        dimension=other.dimension,
                        scale=self)

        # Handle Scale × Scale
        if isinstance(other, Scale):
            result = self.value.exponent * other.value.exponent
            include_binary = 2 in {self.value.exponent.base, other.value.exponent.base}
            if isinstance(result, Exponent):
                match = Scale.all().get(result.parts())
                if match:
                    return Scale[match]
            return Scale.nearest(float(result), include_binary=include_binary)

        return NotImplemented

    # def __mul__(self, other: Union['Scale', 'Unit']):
    #     """
    #     Multiply two Scales together.

    #     Always returns a `Scale`, representing the resulting order of magnitude.
    #     If no exact prefix match exists, returns the nearest known Scale.
    #     """
    #     if isinstance(other, Unit):
    #         # Apply scale to a Unit
    #         return Unit(*other.aliases, name=other.name,
    #                     dimension=other.dimension, scale=self)

    #     if not isinstance(other, (Scale, Unit,)):
    #         return NotImplemented

    #     if self is Scale.one:
    #         return other
    #     if other is Scale.one:
    #         return self

    #     result = self.value.exponent * other.value.exponent  # delegates to Exponent.__mul__
    #     include_binary = 2 in {self.value.exponent.base, other.value.exponent.base}

    #     if isinstance(result, Exponent):
    #         match = Scale.all().get(result.parts())
    #         if match:
    #             return Scale[match]

    #     return Scale.nearest(float(result), include_binary=include_binary)

    def __truediv__(self, other: 'Scale'):
        """
        Divide one Scale by another.

        Always returns a `Scale`, representing the resulting order of magnitude.
        If no exact prefix match exists, returns the nearest known Scale.
        """
        if not isinstance(other, Scale):
            return NotImplemented

        if self == other:
            return Scale.one
        if other is Scale.one:
            return self

        should_consider_binary = (self.value.exponent.base == 2) or (other.value.exponent.base == 2)

        if self is Scale.one:
            result = Exponent(other.value.exponent.base, -other.value.exponent.power)
            name = Scale.all().get((result.base, result.power))
            if name:
                return Scale[name]
            return Scale.nearest(float(result), include_binary=should_consider_binary)

        result: Union[Exponent, float] = self.value.exponent / other.value.exponent
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        else:
            return Scale.nearest(float(result), include_binary=should_consider_binary)

    def __lt__(self, other: 'Scale'):
        return self.value.exponent < other.value.exponent

    def __gt__(self, other: 'Scale'):
        return self.value.exponent > other.value.exponent

    def __eq__(self, other: 'Scale'):
        return self.value.exponent == other.value.exponent

    def __hash__(self):
        return hash((self.value.base, round(self.value.power, 12)))


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

    Notes
    -----
    Units participate in algebraic operations that produce new compound units:

        >>> density = units.gram / units.liter
        >>> density.dimension
        <Dimension.density: Vector(T=0, L=-3, M=1, I=0, Θ=0, J=0, N=0)>

    The combination rules follow the same algebra as :class:`Dimension`.
    """
    def __init__(self, *aliases: str, name: str = "", dimension: Dimension = Dimension.none, scale: Scale = Scale.one):
        self.aliases = aliases
        self.name = name
        self.dimension = dimension
        self.scale = scale

    @property
    def shorthand(self) -> str:
        # Special-case: hide dimensionless in display contexts
        if self.dimension == Dimension.none:
            return ""
        prefix = self.scale.value.shorthand or ""
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
            if self == other:
                return Unit("", name="", dimension=Dimension.none)
            return CompositeUnit({self: 1, other: -1})
        return NotImplemented

    def __pow__(self, power):
        return CompositeUnit({self: power})

    def __eq__(self, other):
        return (
            isinstance(other, Unit)
            and self.dimension == other.dimension
            and self.scale == other.scale
            and self.name == other.name
        )

    def __hash__(self):
        return hash((self.name, self.dimension, self.scale))

    def __repr__(self):
        return f"<Unit {self.shorthand}>"


class CompositeUnit(Unit):
    """
    Represents a product or quotient of base Units.

    Example:
        >>> velocity = CompositeUnit({units.meter: 1, units.second: -1})
        >>> str(velocity)
        'm/s'

    Automatically simplifies:
        (g / mL) * (mL)  →  g
        (m / s) * (s)    →  m
    """
    _SUPERSCRIPTS = str.maketrans("0123456789-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻·")

    def __init__(self, components: dict[Unit, int]):
        super().__init__(name="", dimension=Dimension.none, scale=Scale.one)
        self.aliases = ()
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

        simplified = {}
        for unit, exponent in merged.items():
            if abs(exponent) < 1e-12 or exponent == 0:
                continue
            if unit.dimension == Dimension.none:
                continue  # dimensionless factors do not affect composite structure
            simplified[unit] = exponent

        self.components = simplified
        self.scale = Scale.one

        # Compute resulting dimension
        self.dimension = reduce(
            lambda acc, kv: acc * (kv[0].dimension ** kv[1]),
            self.components.items(),
            Dimension.none,
        )

        self._quantize()

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

    # def _quantize(self):
    #     """
    #     Normalize internal scales so all components are unscaled,
    #     and one unified Scale is promoted to `self.scale`.
    #     """
    #     # 1. Accumulate numeric scaling factor from all component scales
    #     total_factor = 1.0
    #     unscaled_components = {}

    #     for unit, power in self.components.items():
    #         scale = getattr(unit, "scale", Scale.one)
    #         total_factor *= scale.value.exponent.evaluated ** power

    #         # Replace component with an unscaled version
    #         unscaled_unit = Unit(
    #             *getattr(unit, "aliases", ()),
    #             name=unit.name,
    #             dimension=unit.dimension,
    #             scale=Scale.one,
    #         )
    #         unscaled_components[unscaled_unit] = power

    #     # 2. Quantize total_factor into a nearest known Scale
    #     unified_scale = Scale.nearest(total_factor, include_binary=True)

    #     # 3. Update internal state
    #     self.components = unscaled_components
    #     self.scale = unified_scale

    def _quantize(self):
        """
        Normalize component scales by:
        - accumulating all per-component scale factors into a single factor,
        - choosing a nearest known Scale for that factor,
        - absorbing that Scale into one chosen component (so it renders visibly),
        - leaving CompositeUnit.scale = Scale.one.
        """
        if not self.components:
            self.scale = Scale.one
            return

        # 1) accumulate numeric factor contributed by component scales
        total = 1.0
        unscaled = {}
        for unit, power in self.components.items():
            unit_scale = getattr(unit, "scale", Scale.one)
            total *= (unit_scale.value.evaluated ** power)
            # replace each component with an unscaled copy
            unscaled_unit = Unit(
                *getattr(unit, "aliases", ()),
                name=getattr(unit, "name", ""),
                dimension=getattr(unit, "dimension", Dimension.none),
                scale=Scale.one,
            )
            unscaled[unscaled_unit] = unscaled.get(unscaled_unit, 0) + power

        # 2) choose nearest known scale for the accumulated factor
        #    short-circuit when the factor is ~1
        if abs(total - 1.0) < 1e-12:
            self.components = unscaled
            self.scale = Scale.one
            return

        unified = Scale.nearest(total, include_binary=True)

        # 3) pick a "sink" component to absorb the unified scale
        self.components = unscaled  # set first so _pick_scale_sink sees unscaled units
        sink = self._pick_scale_sink()
        if sink is None:
            # nothing to do; keep global identity scale
            self.scale = Scale.one
            return

        # 4) rebuild components with the sink scaled
        exp = self.components.pop(sink)
        scaled_sink = unified * sink  # uses Scale.__mul__(Unit) – safe (sink is unscaled)
        self.components[scaled_sink] = self.components.get(scaled_sink, 0) + exp

        # 5) composite’s own scale remains identity; all scale is visible in components
        self.scale = Scale.one

    def _pick_scale_sink(self) -> Unit:
        """
        Deterministically choose the component that should absorb a unified scale.
        Heuristic:
        1) Prefer components with positive exponent
        2) Among them, choose the one with largest exponent magnitude
        3) Tie-break by unit name (stable)
        4) If no positive exponents, apply same rules to all components
        """
        if not self.components:
            return None

        items = list(self.components.items())
        pos = [(u, e) for (u, e) in items if e > 0]
        pool = pos if pos else items

        # sort by (-abs(exponent), name) so biggest magnitude first, stable by name
        pool_sorted = sorted(pool, key=lambda ue: (-abs(ue[1]), getattr(ue[0], "name", "")))
        return pool_sorted[0][0]

    def _quantize(self):
        """
        Normalize component scales by:
        - accumulating all per-component scale factors into a single factor,
        - choosing a nearest known Scale for that factor,
        - absorbing that Scale into one chosen component (so it renders visibly),
        - leaving CompositeUnit.scale = Scale.one.
        """
        if not self.components:
            self.scale = Scale.one
            return

        # 1) accumulate numeric factor contributed by component scales
        total = 1.0
        unscaled = {}
        for unit, power in self.components.items():
            unit_scale = getattr(unit, "scale", Scale.one)
            total *= (unit_scale.value.evaluated ** power)
            # replace each component with an unscaled copy
            unscaled_unit = Unit(
                *getattr(unit, "aliases", ()),
                name=getattr(unit, "name", ""),
                dimension=getattr(unit, "dimension", Dimension.none),
                scale=Scale.one,
            )
            unscaled[unscaled_unit] = unscaled.get(unscaled_unit, 0) + power

        # 2) choose nearest known scale for the accumulated factor
        #    short-circuit when the factor is ~1
        if abs(total - 1.0) < 1e-12:
            self.components = unscaled
            self.scale = Scale.one
            return

        unified = Scale.nearest(total, include_binary=True)

        # 3) pick a "sink" component to absorb the unified scale
        self.components = unscaled  # set first so _pick_scale_sink sees unscaled units
        sink = self._pick_scale_sink()
        if sink is None:
            # nothing to do; keep global identity scale
            self.scale = Scale.one
            return

        # 4) rebuild components with the sink scaled
        exp = self.components.pop(sink)
        scaled_sink = unified * sink  # uses Scale.__mul__(Unit) – safe (sink is unscaled)
        self.components[scaled_sink] = self.components.get(scaled_sink, 0) + exp

        # 5) composite’s own scale remains identity; all scale is visible in components
        self.scale = Scale.one

    @property
    def shorthand(self):
        """Return symbolic shorthand (e.g., 'kg·m/s²') with automatic cleanup."""
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

    def canonicalize(self) -> 'CompositeUnit':
        """Return a new CompositeUnit normalized to nearest unified scale."""
        clone = CompositeUnit(self.components)
        clone._quantize()
        return clone

    def __mul__(self, other: Union['Scale', 'Unit']):
        # ----- CompositeUnit first (since it's a subclass of Unit) -----
        if isinstance(other, CompositeUnit):
            # Defer to composite’s rmul so it can distribute the scale appropriately
            return other.__rmul__(self)

        # ----- Apply scale to a plain Unit -----
        if isinstance(other, Unit):
            # Forbid double-prefixing
            if getattr(other, "scale", Scale.one) is not Scale.one:
                raise ValueError(f"Cannot apply {self.name or self.alias} to already scaled unit {other}")
            return Unit(*other.aliases,
                        name=other.name,
                        dimension=other.dimension,
                        scale=self)

        # ----- Scale × Scale semantics (unchanged from your logic) -----
        if isinstance(other, Scale):
            result = self.value.exponent * other.value.exponent
            include_binary = 2 in {self.value.exponent.base, other.value.exponent.base}
            if isinstance(result, Exponent):
                match = Scale.all().get(result.parts())
                if match:
                    return Scale[match]
            return Scale.nearest(float(result), include_binary=include_binary)

        return NotImplemented

    # def __mul__(self, other):
    #     if isinstance(other, Unit):
    #         combined = self.components.copy()
    #         combined[other] = combined.get(other, 0) + 1
    #         return CompositeUnit(combined)
    #     if isinstance(other, CompositeUnit):
    #         combined = self.components.copy()
    #         for u, exp in other.components.items():
    #             combined[u] = combined.get(u, 0) + exp
    #         return CompositeUnit(combined)
    #     return NotImplemented

    def __rmul__(self, other):
        """Allow Scale * CompositeUnit to push the prefix into one base component.

        Heuristic:
        1) Prefer a component with positive exponent and scale == one.
        2) Otherwise, pick any unscaled component.
        3) If all components are already scaled, raise (prevents 'kkg' etc.).
        """
        if not isinstance(other, Scale):
            return NotImplemented

        # Choose a target unit to absorb the scale
        target = None
        for u, p in self.components.items():
            if p > 0 and getattr(u, "scale", Scale.one) is Scale.one:
                target = u
                break

        if target is None:
            for u, p in self.components.items():
                if getattr(u, "scale", Scale.one) is Scale.one:
                    target = u
                    break

        if target is None:
            raise ValueError(f"Cannot apply {other} to composite: all components are already scaled")

        # Build new component map with the scale absorbed by the chosen unit
        new_components = dict(self.components)
        exp = new_components.pop(target)
        scaled_target = other * target  # will go through Scale.__mul__(Unit) path
        new_components[scaled_target] = new_components.get(scaled_target, 0) + exp

        return CompositeUnit(new_components)

    # def __rmul__(self, other):
    #     """Allow Scale * CompositeUnit to apply prefix to entire composite."""
    #     if not isinstance(other, Scale):
    #         return NotImplemented

    #     if getattr(self, "scale", Scale.one) is not Scale.one:
    #         raise ValueError(f"Cannot apply {other.name} to already scaled unit {self}")

    #     # Construct a shallow clone of this CompositeUnit, preserving components.
    #     scaled = CompositeUnit(self.components)
    #     scaled.scale = other
    #     return scaled

    # def __rmul__(self, other):
    #     """Allow Scale * CompositeUnit to scale all component units."""
    #     if isinstance(other, Scale):
    #         if getattr(self, "scale", Scale.one) is not Scale.one:
    #             raise ValueError(f"Cannot apply {other} to already scaled unit {self}")

    #         # Apply the scale to the entire composite, not just attach it blindly
    #         scaled_components = {}
    #         for unit, exp in self.components.items():
    #             # apply scale only once to each base unit
    #             if unit.scale is not Scale.one:
    #                 raise ValueError(f"Cannot rescale already-scaled component {unit}")
    #             scaled_components[other * unit] = exp

    #         scaled = CompositeUnit(scaled_components)
    #         scaled.scale = other       # track the global scale for metadata parity
    #         return scaled

    #     return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            combined = self.components.copy()
            combined[other] = combined.get(other, 0) - 1
            return CompositeUnit(combined)
        if isinstance(other, CompositeUnit):
            combined = self.components.copy()
            for u, exp in other.components.items():
                combined[u] = combined.get(u, 0) - exp
            return CompositeUnit(combined)
        return NotImplemented

    # def __repr__(self):
    #     return f"<CompositeUnit {self.shorthand}>"

    # def __repr__(self):
    #     prefix = getattr(self.scale, "shorthand", "")
    #     inner = self.shorthand
    #     dim_name = getattr(self.dimension, "_name_", "derived")
    #     if prefix and prefix != "":
    #         return f"<{dim_name} | {prefix}{inner}>"
    #     return f"<{dim_name} | {inner}>"

    def __repr__(self):
        prefix = getattr(self.scale, "shorthand", "")
        inner = self.shorthand
        dim_name = getattr(self.dimension, "_name_", "derived")
        if prefix:
            return f"<{dim_name} | {prefix}{inner}>"
        return f"<{dim_name} | {inner}>"

    def __eq__(self, other):
        return isinstance(other, CompositeUnit) and self.components == other.components

    def __hash__(self):
        return hash(tuple(sorted(self.components.items(), key=lambda x: x[0].name)))


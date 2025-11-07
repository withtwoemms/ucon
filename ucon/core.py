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
import math
from enum import Enum
from functools import lru_cache
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
        return Dimension(self.value - dimension.value)

    def __mul__(self, dimension: 'Dimension') -> 'Dimension':
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot multiply Dimension by non-Dimension type: {type(dimension)}")
        return Dimension(self.value + dimension.value)

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


class Scale(Enum):
    """
    Enumerates common **magnitude prefixes** for units and quantities.

    Examples include:
    - Binary prefixes (kibi, mebi)
    - Decimal prefixes (milli, kilo, mega)

    Each entry stores its numeric scaling factor (e.g., `kilo = 10³`).
    """
    mebi  = (Exponent(2, 20), "Mi", "mebi")
    kibi  = (Exponent(2, 10), "Ki", "kibi")

    peta  = (Exponent(10, 15), "P", "peta")
    tera  = (Exponent(10, 12), "T", "tera")
    giga  = (Exponent(10, 9), "G", "giga")
    mega  = (Exponent(10, 6), "M", "mega")
    kilo  = (Exponent(10, 3), "k", "kilo")
    hecto = (Exponent(10, 2), "h", "hecto")
    deca  = (Exponent(10, 1), "da", "deca")
    one   = (Exponent(10, 0), "", "")
    deci  = (Exponent(10,-1), "d", "deci")
    centi = (Exponent(10,-2), "c", "centi")
    milli = (Exponent(10,-3), "m", "milli")
    micro = (Exponent(10,-6), "μ", "micro")
    nano  = (Exponent(10,-9), "n", "nano")
    pico  = (Exponent(10,-12), "p", "pico")
    femto = (Exponent(10,-15), "f", "femto")

    def __init__(self, exponent: Exponent, shorthand: str, alias: str):
        self._value_ = exponent
        self.shorthand = shorthand
        self.alias = alias

    def __mul__(self, other):
        if isinstance(other, Scale):
            result = self.value * other.value
            for scale in Scale:
                if scale.value == result:
                    return scale
            return Scale.one
        if isinstance(other, Unit):
            # Apply scale to a Unit
            name = f"{self.shorthand}{other.name}"
            return Unit(*other.aliases, name=name,
                        dimension=other.dimension, scale=self)
        return NotImplemented

    def __truediv__(self, other):
        if not isinstance(other, Scale):
            return NotImplemented
        if self == other:
            return Scale.one
        result = self.value / other.value
        for scale in Scale:
            if scale.value == result:
                return scale
        return Scale.one

    def __hash__(self):
        exponent = self.value
        return hash((exponent.base, round(exponent.power, 12)))


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
    def __init__(self, *aliases: str, name: str = '', dimension: Dimension = Dimension.none, scale: Scale = Scale.one):
        self.aliases = aliases
        self.name = name
        self.shorthand = aliases[0] if aliases else self.name
        self.dimension = dimension
        self.scale = scale

    def __repr__(self):
        addendum = f' | {self.name}' if self.name else ''
        return f'<{self.dimension.name}{addendum}>'

    # TODO -- limit `operator` param choices
    def generate_name(self, unit: 'Unit', operator: str):
        if (self.dimension is Dimension.none) and not (unit.dimension is Dimension.none):
            return unit.name
        if not (self.dimension is Dimension.none) and (unit.dimension is Dimension.none):
            return self.name

        if not self.shorthand and not unit.shorthand:
            name = ''
        elif self.shorthand and not unit.shorthand:
            name = f'({self.shorthand}{operator}?)'
        elif not self.shorthand and unit.shorthand:
            name = f'(?{operator}{unit.shorthand})'
        else:
            name = f'({self.shorthand}{operator}{unit.shorthand})'
        return name

    def __truediv__(self, unit: 'Unit') -> 'Unit':
        # TODO -- define __eq__ for simplification, here
        if (self.name == unit.name) and (self.dimension == unit.dimension):
            return Unit()

        if (unit.dimension is Dimension.none):
            return self

        return Unit(name=self.generate_name(unit, '/'), dimension=self.dimension / unit.dimension)

    def __mul__(self, unit: 'Unit') -> 'Unit':
        return Unit(name=self.generate_name(unit, '*'), dimension=self.dimension * unit.dimension)

    def __rmul__(self, other):
        if isinstance(other, Scale):
            return other * self
        return NotImplemented

    def __eq__(self, unit: 'Unit') -> bool:
        if not isinstance(unit, Unit):
            raise TypeError(f'Cannot compare Unit to non-Unit type: {type(unit)}')
        return (self.name == unit.name) and (self.dimension == unit.dimension)

    def __hash__(self) -> int:
        return hash(tuple([self.name, self.dimension,]))

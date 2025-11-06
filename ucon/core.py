"""
ucon.core
==========

Implements the **quantitative core** of the *ucon* system — the machinery that
manages numeric quantities, scaling prefixes, and dimensional relationships.

Classes
-------
- :class:`Scale` — Enumerates SI and binary magnitude prefixes (kilo, milli, etc.).
- :class:`Number` — Couples a numeric value with a unit and scale.
- :class:`Ratio` — Represents a ratio between two :class:`Number` objects.

Together, these classes allow full arithmetic, conversion, and introspection
of physical quantities with explicit dimensional semantics.
"""
import math
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Dict, Tuple, Union

from ucon import units
from ucon.algebra import Exponent


class Scale(Enum):
    """
    Enumerates common **magnitude prefixes** for units and quantities.

    Examples include:
    - Binary prefixes (kibi, mebi)
    - Decimal prefixes (milli, kilo, mega)

    Each entry stores its numeric scaling factor (e.g., `kilo = 10³`).
    """
    gibi  = Exponent(2, 30)
    mebi  = Exponent(2, 20)
    kibi  = Exponent(2, 10)
    giga  = Exponent(10, 9)
    mega  = Exponent(10, 6)
    kilo  = Exponent(10, 3)
    hecto = Exponent(10, 2)
    deca  = Exponent(10, 1)
    one   = Exponent(10, 0)
    deci  = Exponent(10,-1)
    centi = Exponent(10,-2)
    milli = Exponent(10,-3)
    micro = Exponent(10,-6)
    nano = Exponent(10,-9)
    _kibi = Exponent(2,-10)   # "kibi" inverse
    _mebi = Exponent(2,-20)   # "mebi" inverse
    _gibi = Exponent(2,-30)   # "gibi" inverse

    @staticmethod
    @lru_cache(maxsize=1)
    def all() -> Dict[Tuple[int, int], str]:
        """Return a map from (base, power) → Scale name."""
        return {(s.value.base, s.value.power): s.name for s in Scale}

    @staticmethod
    @lru_cache(maxsize=1)
    def by_value() -> Dict[float, str]:
        """
        Return a map from evaluated numeric value → Scale name.
        Cached after first access.
        """
        return {round(s.value.evaluated, 15): s.name for s in Scale}

    @classmethod
    @lru_cache(maxsize=1)
    def _decimal_scales(cls):
        """Return decimal (base-10) scales only."""
        return list(s for s in cls if s.value.base == 10)

    @classmethod
    @lru_cache(maxsize=1)
    def _binary_scales(cls):
        """Return binary (base-2) scales only."""
        return list(s for s in cls if s.value.base == 2)

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
            ratio = abs_val / scale.value.evaluated
            diff = math.log10(ratio)
            # Bias overshoots slightly more than undershoots
            if ratio < 1:
                diff /= undershoot_bias
            return abs(diff)

        return min(candidates, key=distance)

    def __mul__(self, other: 'Scale'):
        """
        Multiply two Scales together.

        Always returns a `Scale`, representing the resulting order of magnitude.
        If no exact prefix match exists, returns the nearest known Scale.
        """
        if not isinstance(other, Scale):
            return NotImplemented

        if self is Scale.one:
            return other
        if other is Scale.one:
            return self

        result = self.value * other.value  # delegates to Exponent.__mul__
        include_binary = 2 in {self.value.base, other.value.base}

        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]

        return Scale.nearest(float(result), include_binary=include_binary)

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

        should_consider_binary = (self.value.base == 2) or (other.value.base == 2)

        if self is Scale.one:
            result = Exponent(other.value.base, -other.value.power)
            name = Scale.all().get((result.base, result.power))
            if name:
                return Scale[name]
            return Scale.nearest(float(result), include_binary=should_consider_binary)

        result: Union[Exponent, float] = self.value / other.value
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        else:
            return Scale.nearest(float(result), include_binary=should_consider_binary)

    def __lt__(self, other: 'Scale'):
        return self.value < other.value

    def __gt__(self, other: 'Scale'):
        return self.value > other.value

    def __eq__(self, other: 'Scale'):
        return self.value == other.value


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
    def __init__(self, *aliases: str, name: str = '', dimension: Dimension = Dimension.none):
        self.dimension = dimension
        self.name = name
        self.aliases = aliases
        self.shorthand = aliases[0] if aliases else self.name

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

    def __eq__(self, unit: 'Unit') -> bool:
        if not isinstance(unit, Unit):
            raise TypeError(f'Cannot compare Unit to non-Unit type: {type(unit)}')
        return (self.name == unit.name) and (self.dimension == unit.dimension)

    def __hash__(self) -> int:
        return hash(tuple([self.name, self.dimension,]))


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
    unit: Unit = units.none
    scale: Scale = field(default_factory=lambda: Scale.one)

    @property
    def value(self) -> float:
        """Return numeric magnitude as quantity × scale factor."""
        return round(self.quantity * self.scale.value.evaluated, 15)

    def simplify(self):
        return Number(unit=self.unit, quantity=self.value)

    def to(self, new_scale: Scale):
        new_quantity = self.quantity / new_scale.value.evaluated
        return Number(unit=self.unit, scale=new_scale, quantity=new_quantity)

    def as_ratio(self):
        return Ratio(self)

    def __mul__(self, other: Quantifiable) -> 'Number':
        if not isinstance(other, (Number, Ratio)):
            return NotImplemented

        if isinstance(other, Ratio):
            other = other.evaluate()

        return Number(
            quantity=self.quantity * other.quantity,
            unit=self.unit * other.unit,
            scale=self.scale * other.scale,
        )

    def __truediv__(self, other: Quantifiable) -> 'Number':
        if not isinstance(other, (Number, Ratio)):
            return NotImplemented

        if isinstance(other, Ratio):
            other = other.evaluate()

        return Number(
            quantity=self.quantity / other.quantity,
            unit=self.unit / other.unit,
            scale=self.scale / other.scale,
        )

    def __eq__(self, other: Quantifiable) -> bool:
        if not isinstance(other, (Number, Ratio)):
            raise TypeError(f'Cannot compare Number to non-Number/Ratio type: {type(other)}')

        elif isinstance(other, Ratio):
            other = other.evaluate()

        # Compare on evaluated numeric magnitude and exact unit
        return (
            self.unit == other.unit and
            abs(self.value - other.value) < 1e-12
        )

    def __repr__(self):
        return f'<{self.quantity} {"" if self.scale.name == "one" else self.scale.name}{self.unit.name}>'


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

    def evaluate(self) -> Number:
        return self.numerator / self.denominator

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

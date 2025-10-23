"""
ucon.core
==========

Implements the **quantitative core** of the *ucon* system — the machinery that
manages numeric quantities, scaling prefixes, and dimensional relationships.

Classes
-------
- :class:`Exponent` — Represents an exponential base/power pair (e.g., 10³).
- :class:`Scale` — Enumerates SI and binary magnitude prefixes (kilo, milli, etc.).
- :class:`Number` — Couples a numeric value with a unit and scale.
- :class:`Ratio` — Represents a ratio between two :class:`Number` objects.

Together, these classes allow full arithmetic, conversion, and introspection
of physical quantities with explicit dimensional semantics.
"""
from enum import Enum
from functools import lru_cache, reduce, total_ordering
from math import log2
from math import log10
from typing import Dict, Tuple, Union

from ucon import units
from ucon.unit import Unit


# TODO -- consider using a dataclass
@total_ordering
class Exponent:
    """
    Represents a **base–exponent pair** (e.g., 10³ or 2¹⁰).

    Provides comparison and division semantics used internally to represent
    magnitude prefixes (e.g., kilo, mega, micro).
    """
    bases = {2: log2, 10: log10}

    __slots__ = ("base", "power")

    def __init__(self, base: int, power: Union[int, float]):
        if base not in self.bases.keys():
            raise ValueError(f'Only the following bases are supported: {reduce(lambda a,b: f"{a}, {b}", self.bases.keys())}')
        self.base = base
        self.power = power

    @property
    def evaluated(self) -> float:
        """Return the numeric value of base ** power."""
        return self.base ** self.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        """Return (base, power) tuple, used for Scale lookups."""
        return self.base, self.power

    def __eq__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            raise TypeError(f'Cannot compare Exponent to non-Exponent type: {type(other)}')
        return self.evaluated == other.evaluated

    def __lt__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        return self.evaluated < other.evaluated

    def __hash__(self):
        # Hash by rounded numeric equivalence to maintain cross-base consistency
        return hash(round(self.evaluated, 15))

    # ---------- Arithmetic Semantics ----------

    def __truediv__(self, other: 'Exponent'):
        """
        Divide two Exponents.
        - If bases match, returns a relative Exponent.
        - If bases differ, returns a numeric ratio (float).
        """
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power - other.power)
        return self.evaluated / other.evaluated

    def __mul__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power + other.power)
        return float(self.evaluated * other.evaluated)

    # ---------- Conversion Utilities ----------

    def to_base(self, new_base: int) -> "Exponent":
        """
        Convert this Exponent to another base representation.

        Example:
            Exponent(2, 10).to_base(10)
            # → Exponent(base=10, power=3.010299956639812)
        """
        if new_base not in self.bases:
            supported = ", ".join(map(str, self.bases))
            raise ValueError(f"Unsupported base {new_base!r}. Supported bases: {supported}")
        new_power = self.bases[new_base](self.evaluated)
        return Exponent(new_base, new_power)

    # ---------- Numeric Interop ----------

    def __float__(self) -> float:
        return float(self.evaluated)

    def __int__(self) -> int:
        return int(self.evaluated)

    # ---------- Representation ----------

    def __repr__(self) -> str:
        return f"Exponent(base={self.base}, power={self.power})"

    def __str__(self) -> str:
        return f"{self.base}^{self.power}"


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
            diff = log10(ratio)
            # Bias overshoots slightly more than undershoots
            if ratio < 1:
                diff /= undershoot_bias
            return abs(diff)

        return min(candidates, key=distance)

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


# TODO -- consider using a dataclass
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
    def __init__(self, unit: Unit = units.none, scale: Scale = Scale.one, quantity = 1):
        self.unit = unit
        self.scale = scale
        self.quantity = quantity
        self.value = round(self.quantity * self.scale.value.evaluated, 15)

    def simplify(self):
        return Number(unit=self.unit, quantity=self.value)

    def to(self, new_scale: Scale):
        new_quantity = self.quantity / new_scale.value.evaluated
        return Number(unit=self.unit, scale=new_scale, quantity=new_quantity)

    def as_ratio(self):
        return Ratio(self)

    def __mul__(self, another_number: 'Number') -> 'Number':
        return Number(
            unit=self.unit * another_number.unit,
            scale=self.scale,
            quantity=self.quantity * another_number.quantity,
        )

    def __truediv__(self, another_number: 'Number') -> 'Number':
        unit = self.unit / another_number.unit
        scale = self.scale / another_number.scale
        quantity = self.quantity / another_number.quantity
        return Number(unit, scale, quantity)

    def __eq__(self, another_number):
        if isinstance(another_number, Number):
            return (self.unit == another_number.unit) and \
                   (self.quantity == another_number.quantity) and \
                   (self.value == another_number.value)
        elif isinstance(another_number, Ratio):
            return self == another_number.evaluate()
        else:
            raise ValueError(f'"{another_number}" is not a Number or Ratio. Comparison not possible.')

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

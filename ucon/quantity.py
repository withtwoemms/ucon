"""
ucon.quantity
==========
Classes
-------
- :class:`Number` — Couples a numeric value with a unit and scale.
- :class:`Ratio` — Represents a ratio between two :class:`Number` objects.
"""
from dataclasses import dataclass, field
from typing import Union

from ucon import units
from ucon.core import Scale, Unit


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

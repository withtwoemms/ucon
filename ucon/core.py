from __future__ import annotations  # NOTE: prevents the use of < python3.7

from enum import Enum
from functools import reduce
from math import log2
from math import log10

from ucon.unit import Unit
from ucon.unit import Units


# TODO -- consider using a dataclass
class Exponent:
    bases ={2: log2, 10: log10}

    def __init__(self, base: int, power: int):
        if base not in self.bases.keys():
            raise ValueError(f'Only the following bases are supported: {reduce(lambda a,b: f"{a}, {b}", self.bases.keys())}')
        self.base = base
        self.power = power
        self.evaluated = base ** power

    def parts(self):
        return self.base, self.power

    def __truediv__(self, another_exponent):
        return self.evaluated / another_exponent.evaluated

    def __lt__(self, another_exponent):
        return self.evaluated < another_exponent.evaluated

    def __gt__(self, another_exponent):
        return self.evaluated > another_exponent.evaluated

    def __eq__(self, another_exponent):
        return self.evaluated == another_exponent.evaluated

    def __repr__(self):
        return f'<{self.base}^{self.power}>'


class Scale(Enum):
    mebi  = Exponent(2, 20)
    kibi  = Exponent(2, 10)
    mega  = Exponent(10, 6)
    kilo  = Exponent(10, 3)
    hecto = Exponent(10, 2)
    deca  = Exponent(10, 1)
    one   = Exponent(10, 0)
    deci  = Exponent(10,-1)
    centi = Exponent(10,-2)
    milli = Exponent(10,-3)
    micro = Exponent(10,-6)
    _kibi = Exponent(2,-10)
    _mebi = Exponent(2,-20)

    @staticmethod
    def all():
        return dict(map(lambda x: ((x.value.base, x.value.power), x.name), Scale))

    @staticmethod
    def by_value():
        return dict(map(lambda x: (x.value.evaluated, x.name), Scale))

    def __truediv__(self, another_scale):
        power_diff = self.value.power - another_scale.value.power
        if self.value == another_scale.value:
            return Scale.one
        if self.value.base == another_scale.value.base:
            return Scale[Scale.all()[Exponent(self.value.base, power_diff).parts()]]

        base_quotient = self.value.base / another_scale.value.base
        exp_quotient = round((base_quotient ** another_scale.value.power) * (self.value.base ** power_diff), 15)

        if Scale.one in [self, another_scale]:
            power = Exponent.bases[2](exp_quotient)
            return Scale[Scale.all()[Exponent(2, power).parts()]]
        else:
            scale_exp_values = [Scale[Scale.all()[pair]].value.evaluated for pair in Scale.all().keys()]
            closest_val = min(scale_exp_values, key=lambda val: abs(val - exp_quotient))
            return Scale[Scale.by_value()[closest_val]]

    def __lt__(self, another_scale):
        return self.value < another_scale.value

    def __gt__(self, another_scale):
        return self.value > another_scale.value

    def __eq__(self, another_scale):
        return self.value == another_scale.value


# TODO -- consider using a dataclass
class Number:
    def __init__(self, unit: Unit = Units.none.value, scale: Scale = Scale.one, quantity = 1):
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

    def __mul__(self, another_number):
        return Number(
            unit=self.unit * another_number.unit,
            scale=self.scale,
            quantity=self.quantity * another_number.quantity,
        )

    def __truediv__(self, another_number: Number) -> Number:
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
    def __init__(self, numerator: Number = Number(), denominator: Number = Number()):
        self.numerator = numerator
        self.denominator = denominator

    def reciprocal(self) -> Ratio:
        return Ratio(numerator=self.denominator, denominator=self.numerator)

    def evaluate(self) -> Number:
        return self.numerator / self.denominator

    def __mul__(self, another_ratio):
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

    def __truediv__(self, another_ratio):
        return Ratio(
            numerator=self.numerator * another_ratio.denominator,
            denominator=self.denominator * another_ratio.numerator,
        )

    def __eq__(self, another_ratio):
        if isinstance(another_ratio, Ratio):
            return self.evaluate() == another_ratio.evaluate()
        elif isinstance(another_ratio, Number):
            return self.evaluate() == another_ratio
        else:
            raise ValueError(f'"{another_ratio}" is not a Ratio or Number. Comparison not possible.')

    def __repr__(self):
        # TODO -- resolve int/float inconsistency
        return f'{self.evaluate()}' if self.numerator == self.denominator else f'{self.numerator} / {self.denominator}'

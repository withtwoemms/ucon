from __future__ import annotations  # NOTE: prevents the use of < python3.7

from enum import Enum
from functools import reduce
from math import log2
from math import log10


class Unit:
    def __init__(self, name, *aliases):
        self.name = name
        self.aliases = aliases

    def __repr__(self):
        return f'<{self.name}>'


class Units(Enum):
    none = Unit('')
    volt = Unit('volt', 'v', 'V')  # NOTE: a "volt" is a derived unit; treat accordingly in future
    liter = Unit('liter', 'l', 'L')         # volume
    gram = Unit('gram', 'g', 'G')           # mass
    second = Unit('second', 's', 'secs')    # time
    kelvin = Unit('kelvin', 'K')            # temperature
    mole = Unit('mole', 'mol')              # amount
    coulomb = Unit('coulomb', 'C')          # charge

    def __truediv__(self, another_unit) -> Unit:
        if self.name == another_unit.name:
            return Units.none
        elif self == Units.none:
            return another_unit
        elif another_unit == Units.none:
            return self
        else:
            raise ValueError(f'Unsupported unit division: {self.name} / {another_unit.name}. Consider using Ratio.')

    @staticmethod
    def all():
        return dict(list(map(lambda x: (x.value, x.value.aliases), Units)))


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
    def __init__(self, unit: Unit = Units.none, scale: Scale = Scale.one, quantity = 1):
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
        new_quantity = self.quantity * another_number.quantity
        return Number(unit=self.unit, scale=self.scale, quantity=new_quantity)

    def __truediv__(self, another_number) -> Number:
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
        return f'<{self.quantity} {"" if self.scale.name == "one" else self.scale.name}{self.unit.value.name}>'


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
        new_numerator = self.numerator / another_ratio.denominator
        new_denominator = self.denominator / another_ratio.numerator
        return Ratio(numerator=new_numerator, denominator=new_denominator)

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


from __future__ import annotations

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
    volt = Unit('volt', 'v', 'V')
    liter = Unit('liter', 'l', 'L')
    gram = Unit('gram', 'g', 'G')
    second = Unit('second', 's', 'secs')

    def __truediv__(self, another_unit) -> Unit:
        if self.name == another_unit.name:
            return Units.none
        elif self == Units.none:
            return another_unit
        elif another_unit == Units.none:
            return self
        else:
            # TODO -- support division of different units. Will likely need a concept like "RatioUnits"
            raise RuntimeError(f'Unsupported unit division: {self.name} / {another_unit.name}')

    @staticmethod
    def all():
        return dict(list(map(lambda x: (x.value, x.value.aliases), Units)))


# TODO -- write tests
class Exponent:
    bases ={2: log2, 10: log10}

    def __init__(self, base: int, power: int):
        if base not in self.bases.keys():
            raise RuntimeError(f'Only the following bases are supported: {reduce(lambda a,b: f"{a}, {b}", self.bases.keys())}')
        self.base = base
        self.power = power
        self.evaluated = base ** power

    def parts(self):
        return self.base, self.power

    def __truediv__(self, another_exponent):
        self.evaluated / another_exponent.evaluated

    def __lt__(self, another_exponent):
        return self.evaluated > another_exponent.evaluated

    def __gt__(self, another_exponent):
        return self.evaluated < another_exponent.evaluated

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
        return self.value > another_scale.value

    def __gt__(self, another_scale):
        return self.value < another_scale.value

    def __eq__(self, another_scale):
        return self.value == another_scale.value


class ScaledUnit:
    def __init__(self, unit: Unit = Units.none, scale: Scale = Scale.one):
        self.unit = unit
        self.scale = scale

    # NOTE: specifying a return class of the containing class made possible by __future__.annotations
    def __truediv__(self, another_scaled_unit) -> ScaledUnit:
        unit = self.unit / another_scaled_unit.unit
        scale = self.scale / another_scaled_unit.scale
        return ScaledUnit(unit, scale)

    def __eq__(self, another_scaled_unit):
        return (self.unit == another_scaled_unit.unit) and (self.scale == another_scaled_unit.scale)

    def __repr__(self):
        return f'<|{self.scale.value.evaluated} {self.unit.value.name}>'


class Number:
    def __init__(self, unit: ScaledUnit, quantity = 1):
        self.unit = unit  # TODO -- address the self.unit.unit redundancy
        self.quantity = quantity
        self.value = round(self.quantity * self.unit.scale.value.evaluated, 15)

    def simplify(self):
        return Number(ScaledUnit(self.unit.unit), self.value)

    # TODO -- write tests
    def to(self, new_scale: Scale):
        return Number(ScaledUnit(self.unit.unit, new_scale), self.quantity / new_scale.value.evaluated)

    def __truediv__(self, another_number) -> Number:
        scaled_unit = self.unit / another_number.unit
        quantity = self.quantity / another_number.quantity
        return Number(scaled_unit, quantity)

    def __eq__(self, another_number):
        return (self.unit == another_number.unit) and \
               (self.quantity == another_number.quantity) and \
               (self.value == another_number.value)

    def __repr__(self):
        return f'<{self.quantity} {"" if self.unit.scale.name == "one" else self.unit.scale.name}{self.unit.unit.value.name}>'


# TODO -- write tests
class Ratio:
    NotImplemented

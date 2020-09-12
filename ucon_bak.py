from __future__ import annotations

import ipdb

from enum import Enum
from typing import Union


class Scale(Enum):
    mebi = 1048576
    kibi = 1024
    kilo = 1000
    hecto = 100
    deca = 10
    one = 1
    deci = 1/10
    centi = 1/100
    milli = 1/1000

    @staticmethod
    def all():
        return dict(list(map(lambda x: (float(x.value), x.name), Scale)))

    def __truediv__(self, another_scale):
        return Scale[Scale.all()[float(self.value / another_scale.value)]]

    def __lt__(self, another_scale):
        return self.value > another_scale.value

    def __gt__(self, another_scale):
        return self.value < another_scale.value


class Unit:
    def __init__(self, name, *aliases):
        self.name = name
        self.aliases = aliases

    def __repr__(self):
        return f'<{self.name}>'


class Units(bytes, Enum):
    def __new__(cls, name, *aliases):
        obj = bytes.__new__(cls, [name])
        obj._value_ = name
        cls.name = name
        cls.aliases = aliases
    none = Unit('')
    # TODO -- accept/handle unit aliases
    volt = Unit('volt', 'v', 'V')
    liter = Unit('liter', 'l', 'L')
    gram = Unit('gram', 'g', 'G')

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
        return dict(list(map(lambda x: (x.value.name, x.value.aliases), Units)))


class ScaledUnit:
    def __init__(self, unit: Unit = Units.none, scale: Scale = Scale.one):
        self.unit = unit
        self.scale = scale

    def to(self, new_scale: Scale) -> ScaledUnit:
        return ScaledUnit(self.unit, ScaledUnit.Factor(self.scale.value/new_scale.value, new_scale.name))

    # NOTE: specifying a return class of the containing class made possible by __future__.annotations
    def __truediv__(self, another_scaled_unit) -> ScaledUnit:
        unit = self.unit / another_scaled_unit.unit
        if self.unit == Units.none:
            scale = self.to(another_scaled_unit.scale).scale
        else:
            scale = self.scale / another_scaled_unit.scale
        return ScaledUnit(unit, scale)

    def __repr__(self):
        return f'<|{self.scale.value} {self.scale.name}{self.unit.name}>'

    class Factor:
        def __init__(self, value, name):
            self.value = value
            self.name = name


class Number:
    # TODO -- consider Number.ratio -> Ratio

    def __init__(self, unit: ScaledUnit, quantity = 1):
        self.unit = unit
        self.quantity = quantity
        self.value = self.quantity * self.unit.scale.value

    def __truediv__(self, another_number) -> Number:
        quantity = self.value / another_number.value
        unit = self.unit / another_number.unit
        return Number(unit, quantity)

    def __repr__(self):
        return f'<{self.quantity} {self.unit.scale.name}{self.unit.unit.name}>'


class Identity(type):
    def __repr__(cls):
        return str(cls.value)
class Identity(Number, metaclass=Identity):
    unit = ScaledUnit(Units.none)
    quantity = 1
    value = 1

    @staticmethod
    def ratio(scaled_unit: ScaledUnit) -> Ratio:
        return Ratio(numerator=Number(scaled_unit, 1/scaled_unit.scale.value),
                     denominator=Number(ScaledUnit(scaled_unit.unit)))


class Ratio:
    """
    can do things like:
        2 volt / 1 => Ratio(Number(Units.volt, quantity=2))
        1000 millivolt / 1 voltRatio(numerator=Number(Units.volt, scale=Scale.milli, quantity=1000),
              denominator=Number(Units.volt))
    """
    def __init__(self, numerator: Number = Identity, denominator: Number = Identity):
        self.numerator = numerator
        self.denominator = denominator

    def reciprocal(self) -> Ratio:
        return Ratio(numerator=self.denominator, denominator=self.numerator)

    def evaluate(self) -> Number:
        return self.numerator / self.denominator

    def __repr__(self):
        return f'{self.numerator} / {self.denominator}'

    def __mul__(self, another_ratio):
        numerator_quantity = self.numerator.value * another_ratio.numerator.value
        denominator_quantity = self.denominator.value * another_ratio.denominator.value
        # TODO -- ensure commutivity holds
        numerator = Number(self.numerator.unit/another_ratio.denominator.unit, numerator_quantity)
        denominator = Number(another_ratio.numerator.unit/self.denominator.unit, denominator_quantity)
        return Ratio(numerator, denominator)


if __name__ == '__main__':
    r1 = Ratio(Number(ScaledUnit(Units.volt), quantity=2))
    r2 = Identity.ratio(ScaledUnit(Units.volt, Scale.milli))
    print(f'({r1}) * ({r2})')
    m = r1 * r2
    print('RESULT:', m.evaluate())
    print('RESULT:', (r2 * r1).evaluate())
    print(m.reciprocal(), m.reciprocal().evaluate())
    print(m.evaluate())
    print(ScaledUnit(Units.volt).to(Scale.milli))
    print(ScaledUnit(Units.volt).to(Scale.deca))
    print(ScaledUnit(Units.volt).to(Scale.kilo))
    print(ScaledUnit(Units.volt).to(Scale.kibi))
    m = Ratio(Number(ScaledUnit(Units.liter), 15)) * Identity.ratio(ScaledUnit(Units.liter, Scale.deci))
    print(m)
    print(m.evaluate())
    print((r1 * r2).evaluate())
    print(Units.all())
    print(Units('hello'))
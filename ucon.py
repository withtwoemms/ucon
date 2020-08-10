from __future__ import annotations

import ipdb

from enum import Enum


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


class Scale(Enum):
    mebi = 1024**2
    kibi = 1024
    kilo = 1000
    hecto = 100
    deca = 10
    one = 1
    deci = 1/deca
    centi = 1/hecto
    milli = 1/kilo
    _kibi = 1/kibi
    _mebi = 1/mebi


    @staticmethod
    def all():
        return dict(list(map(lambda x: (float(x.value), x.name), Scale)))

    def __truediv__(self, another_scale):
        return Scale[Scale.all()[float(self.value / another_scale.value)]]

    def __lt__(self, another_scale):
        return self.value > another_scale.value

    def __gt__(self, another_scale):
        return self.value < another_scale.value


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
        return f'<|{self.scale.value} {self.scale.name}{self.unit.value.name}>'

    class Factor:
        def __init__(self, value, name):
            self.value = value
            self.name = name


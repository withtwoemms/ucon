from enum import Enum

from ucon.dimension import Dimension


class Unit:
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

    def __eq__(self, unit) -> bool:
        return (self.name == unit.name) and (self.dimension == unit.dimension)

    def __hash__(self) -> int:
        return hash(tuple([self.name, self.dimension,]))


# International System of Units (SI)
class SIUnit(Enum):
    none = Unit()
    gram = Unit('g', 'G', name='gram', dimension=Dimension.mass)
    meter = Unit('m', 'M', name='meter', dimension=Dimension.length)
    second = Unit('s', 'sec', name='second', dimension=Dimension.time)
    hour = Unit('h', 'H', name='hour', dimension=Dimension.time)
    liter = Unit('L', 'l', name='liter', dimension=Dimension.volume)
    volt = Unit('V', name='volt', dimension=Dimension.voltage)
    kelvin = Unit('K', name='kelvin', dimension=Dimension.temperature)
    mole = Unit('mol', 'n', name='mole', dimension=Dimension.amount_of_substance)
    coulomb = Unit('C', name='coulomb', dimension=Dimension.charge)
    ampere = Unit('I', 'amp', name='ampere', dimension=Dimension.current)
    ohm = Unit('Ω', name='ohm', dimension=Dimension.resistance)
    joule = Unit('J', name='joule', dimension=Dimension.energy)
    watt = Unit('W', name='watt', dimension=Dimension.power)
    newton = Unit('N', name='newton', dimension=Dimension.force)

    def __hash__(self) -> int:
        return hash(self.value)

    def __iter__(self):
        for unit in self:
            yield unit

    def __truediv__(self, unit: 'SIUnit') -> 'Unit':
        return self.value / unit.value

    def __mul__(self, unit: 'SIUnit') -> 'Unit':
        return self.value * unit.value

    def __eq__(self, unit) -> bool:
        return self.value == unit.value 

    @staticmethod
    def all():
        return dict(list(map(lambda x: (x.value, x.value.aliases), SIUnit)))

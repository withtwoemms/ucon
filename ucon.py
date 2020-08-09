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

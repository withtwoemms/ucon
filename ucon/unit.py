from dataclasses import dataclass
from enum import Enum
from functools import partial, reduce
from operator import __sub__ as subtraction
from typing import Callable, Iterable, Iterator


diff: Callable[[Iterable], int] = partial(reduce, subtraction)

@dataclass
class Vector:
    """
    A collection of exponent values corresponding to the designated quantity

    (s * m * kg * A * K * cd * mol)
    (T * L *  M * I * Θ *  J *   N)

    e.g.
    Vector(T=1, L=0, M=0, I=0, Θ=0, J=0, N=0)   => "time"
    Vector(T=0, L=2, M=0, I=0, Θ=0, J=0, N=0)   => "area"
    Vector(T=-2, L=1, M=1, I=0, Θ=0, J=0, N=0)  => "force"
    """
    T: int = 0  # time
    L: int = 0  # length
    M: int = 0  # mass
    I: int = 0  # current
    Θ: int = 0  # temperature
    J: int = 0  # luminous intensity
    N: int = 0  # amount of substance

    def __iter__(self) -> Iterator[int]:
        yield self.T
        yield self.L
        yield self.M
        yield self.I
        yield self.Θ
        yield self.J
        yield self.N

    def __len__(self) -> int:
        return sum(tuple(1 for x in self))

    def __add__(self, vector: 'Vector') -> 'Vector':
        """
        Addition, here, comes from the multiplication of base quantities

        e.g. F = m * a
        F =
            (s^-2 * m^1 * kg   * A * K * cd * mol) +
            (s    * m   * kg^1 * A * K * cd * mol)
        """
        values = tuple(sum(pair) for pair in zip(tuple(self), tuple(vector)))
        return Vector(*values)

    def __sub__(self, vector: 'Vector') -> 'Vector':
        """
        Subtraction, here, comes from the division of base quantities
        """
        values = tuple(diff(pair) for pair in zip(tuple(self), tuple(vector)))
        return Vector(*values)

    def __eq__(self, vector) -> bool:
        return tuple(self) == tuple(vector)

    def __hash__(self) -> int:
        return hash(tuple(self))


class UnitType(Enum):
    none = Vector()

    # -- BASIS ---------------------------------------
    time                = Vector(1, 0, 0, 0, 0, 0, 0)
    length              = Vector(0, 1, 0, 0, 0, 0, 0)
    mass                = Vector(0, 0, 1, 0, 0, 0, 0)
    current             = Vector(0, 0, 0, 1, 0, 0, 0)
    temperature         = Vector(0, 0, 0, 0, 1, 0, 0)
    luminous_intensity  = Vector(0, 0, 0, 0, 0, 1, 0)
    amount_of_substance = Vector(0, 0, 0, 0, 0, 0, 1)
    # ------------------------------------------------

    acceleration = Vector(-2, 1, 0, 0, 0, 0, 0)
    angular_momentum = Vector(-1, 2, 1, 0, 0, 0, 0)
    area = Vector(0, 2, 0, 0, 0, 0, 0)
    capacitance = Vector(4, -2, -1, 2, 0, 0, 0)
    charge = Vector(1, 0, 0, 1, 0, 0, 0)
    conductance = Vector(3, -2, -1, 2, 0, 0, 0)
    conductivity = Vector(3, -3, -1, 2, 0, 0, 0)
    density = Vector(0, -3, 1, 0, 0, 0, 0)
    electric_field_strength = Vector(-3, 1, 1, -1, 0, 0, 0)
    energy = Vector(-2, 2, 1, 0, 0, 0, 0)
    entropy = Vector(-2, 2, 1, 0, -1, 0, 0)
    force = Vector(-2, 1, 1, 0, 0, 0, 0)
    frequency = Vector(-1, 0, 0, 0, 0, 0, 0)
    gravitation = Vector(-2, 3, -1, 0, 0, 0, 0)
    illuminance = Vector(0, -2, 0, 0, 0, 1, 0)
    inductance = Vector(-2, 2, 1, -2, 0, 0, 0)
    magnetic_flux = Vector(-2, 2, 1, -1, 0, 0, 0)
    magnetic_flux_density = Vector(-2, 0, 1, -1, 0, 0, 0)
    magnetic_permeability = Vector(-2, 1, 1, -2, 0, 0, 0)
    molar_mass = Vector(0, 0, 1, 0, 0, 0, -1)
    molar_volume = Vector(0, 3, 0, 0, 0, 0, -1)
    momentum = Vector(-1, 1, 1, 0, 0, 0, 0)
    permittivity = Vector(4, -3, -1, 2, 0, 0, 0)
    power = Vector(-3, 2, 1, 0, 0, 0, 0)
    pressure = Vector(-2, -1, 1, 0, 0, 0, 0)
    resistance = Vector(-3, 2, 1, -2, 0, 0, 0)
    resistivity = Vector(-3, 3, 1, -2, 0, 0, 0)
    specific_heat_capacity = Vector(-2, 2, 0, 0, -1, 0, 0)
    thermal_conductivity = Vector(-3, 1, 1, 0, -1, 0, 0)
    velocity = Vector(-1, 1, 0, 0, 0, 0, 0)
    voltage = Vector(-3, 2, 1, -1, 0, 0, 0)
    volume = Vector(0, 3, 0, 0, 0, 0, 0)

    def __truediv__(self, unit_type: 'UnitType') -> 'UnitType':
        return UnitType(self.value - unit_type.value)

    def __mul__(self, unit_type: 'UnitType') -> 'UnitType':
        return UnitType(self.value + unit_type.value)

    def __eq__(self, unit_type) -> bool:
        return self.value == unit_type.value

    def __hash__(self) -> int:
        return hash(self.value)


class Unit:
    def __init__(self, *aliases: str, name: str = '', type: UnitType = UnitType.none):
        self.type = type
        self.name = name
        self.aliases = aliases
        self.shorthand = aliases[0] if aliases else self.name

    def __repr__(self):
        addendum = f' | {self.name}' if self.name else ''
        return f'<{self.type.name}{addendum}>'

    # TODO -- limit `operator` param choices
    def generate_name(self, unit: 'Unit', operator: str):
        if (self.type is UnitType.none) and not (unit.type is UnitType.none):
            return unit.name
        if not (self.type is UnitType.none) and (unit.type is UnitType.none):
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
        if (self.name == unit.name) and (self.type == unit.type):
            return Unit()

        if (unit.type is UnitType.none):
            return self
        
        return Unit(name=self.generate_name(unit, '/'), type=self.type / unit.type)

    def __mul__(self, unit: 'Unit') -> 'Unit':
        return Unit(name=self.generate_name(unit, '*'), type=self.type * unit.type)

    def __eq__(self, unit) -> bool:
        return (self.name == unit.name) and (self.type == unit.type)

    def __hash__(self) -> int:
        return hash(tuple([self.name, self.type,]))


# International System of Units (SI)
class SIUnit(Enum):
    none = Unit()
    gram = Unit('g', 'G', name='gram', type=UnitType.mass)
    meter = Unit('m', 'M', name='meter', type=UnitType.length)
    second = Unit('s', 'sec', name='second', type=UnitType.time)
    hour = Unit('h', 'H', name='hour', type=UnitType.time)
    liter = Unit('L', 'l', name='liter', type=UnitType.volume)
    volt = Unit('V', name='volt', type=UnitType.voltage)
    kelvin = Unit('K', name='kelvin', type=UnitType.temperature)
    mole = Unit('mol', 'n', name='mole', type=UnitType.amount_of_substance)
    coulomb = Unit('C', name='coulomb', type=UnitType.charge)
    ampere = Unit('I', 'amp', name='ampere', type=UnitType.current)
    ohm = Unit('Ω', name='ohm', type=UnitType.resistance)
    joule = Unit('J', name='joule', type=UnitType.energy)
    watt = Unit('W', name='watt', type=UnitType.power)
    newton = Unit('N', name='newton', type=UnitType.force)

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

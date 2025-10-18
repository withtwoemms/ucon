"""
ucon.unit
==========

Defines the **Unit** abstraction — the symbolic and algebraic representation of
a measurable quantity associated with a :class:`ucon.dimension.Dimension`.

A :class:`Unit` pairs a human-readable name and aliases with its underlying
dimension.

Units are composable:

    >>> from ucon import units
    >>> units.meter / units.second
    <velocity | (m/s)>

They can be multiplied or divided to form compound units, and their dimensional
relationships are preserved algebraically.
"""
from ucon.dimension import Dimension


class Unit:
    """
    Represents a **unit of measure** associated with a :class:`Dimension`.

    Parameters
    ----------
    *aliases : str
        Optional shorthand symbols (e.g., "m", "sec").
    name : str
        Canonical name of the unit (e.g., "meter").
    dimension : Dimension
        The physical dimension this unit represents.

    Notes
    -----
    Units participate in algebraic operations that produce new compound units:

        >>> density = units.gram / units.liter
        >>> density.dimension
        <Dimension.density: Vector(T=0, L=-3, M=1, I=0, Θ=0, J=0, N=0)>

    The combination rules follow the same algebra as :class:`Dimension`.
    """
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

    def __eq__(self, unit: 'Unit') -> bool:
        if not isinstance(unit, Unit):
            raise TypeError(f'Cannot compare Unit to non-Unit type: {type(unit)}')
        return (self.name == unit.name) and (self.dimension == unit.dimension)

    def __hash__(self) -> int:
        return hash(tuple([self.name, self.dimension,]))

"""
ucon.dimension
===============

Defines the algebra of **physical dimensions**--the foundation of all unit
relationships and dimensional analysis in *ucon*.

Each :class:`Dimension` represents a physical quantity (time, mass, length, etc.)
expressed as a 7-element exponent vector following the SI base system:

    (T, L, M, I, Θ, J, N) :: (s * m * kg * A * K * cd * mol)
     time, length, mass, current, temperature, luminous intensity, substance

Derived dimensions are expressed as algebraic sums or differences of these base
vectors (e.g., `velocity = length / time`, `force = mass * acceleration`).

Classes
-------
- :class:`Vector` — Represents the exponent vector of a physical quantity.
- :class:`Dimension` — Enum of known physical quantities, each with a `Vector`
  value and operator overloads for dimensional algebra.
"""
from dataclasses import dataclass
from enum import Enum
from functools import partial, reduce
from operator import __sub__ as subtraction
from typing import Callable, Iterable, Iterator


diff: Callable[[Iterable], int] = partial(reduce, subtraction)

@dataclass
class Vector:
    """
    Represents the **exponent vector** of a physical quantity.

    Each component corresponds to the power of a base dimension in the SI system:
    time (T), length (L), mass (M), current (I), temperature (Θ),
    luminous intensity (J), and amount of substance (N).

    Arithmetic operations correspond to dimensional composition:
    - Addition (`+`) → multiplication of quantities
    - Subtraction (`-`) → division of quantities

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

    def __eq__(self, vector: 'Vector') -> bool:
        assert isinstance(vector, Vector), "Can only compare Vector to another Vector"
        return tuple(self) == tuple(vector)

    def __hash__(self) -> int:
        # Hash based on the string because tuples have been shown to collide
        # Not the most performant, but effective
        return hash(str(tuple(self)))


class Dimension(Enum):
    """
    Represents a **physical dimension** defined by a :class:`Vector`.

    Each dimension corresponds to a distinct combination of base exponents.
    Dimensions are algebraically composable via multiplication and division:

        >>> Dimension.length / Dimension.time
        <Dimension.velocity: Vector(T=-1, L=1, M=0, I=0, Θ=0, J=0, N=0)>

    This algebra forms the foundation for unit compatibility and conversion.
    """
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

    def __truediv__(self, dimension: 'Dimension') -> 'Dimension':
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot divide Dimension by non-Dimension type: {type(dimension)}")
        return Dimension(self.value - dimension.value)

    def __mul__(self, dimension: 'Dimension') -> 'Dimension':
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot multiply Dimension by non-Dimension type: {type(dimension)}")
        return Dimension(self.value + dimension.value)

    def __eq__(self, dimension) -> bool:
        if not isinstance(dimension, Dimension):
            raise TypeError(f"Cannot compare Dimension with non-Dimension type: {type(dimension)}")
        return self.value == dimension.value

    def __hash__(self) -> int:
        return hash(self.value)

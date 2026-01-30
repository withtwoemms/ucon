# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.algebra
============

Provides the low-level algebraic primitives that power the rest of the *ucon*
stack. These building blocks model exponent vectors for physical dimensions and
numeric base-exponent pairs for scale prefixes, enabling higher-level modules to
compose dimensions, units, and quantities without reimplementing arithmetic.

Other modules depend on these structures to ensure dimensional calculations,
prefix handling, and unit simplification all share the same semantics.

Classes
-------
- :class:`Vector` — Exponent tuple representing a physical dimension basis.
- :class:`Exponent` — Base/power pair supporting prefix arithmetic.
"""
import math
from dataclasses import dataclass
from functools import partial, reduce, total_ordering
from operator import __sub__ as subtraction
from typing import Callable, Iterable, Iterator, Tuple, Union


diff: Callable[[Iterable], int] = partial(reduce, subtraction)


@dataclass
class Vector:
    """
    Represents the **exponent vector** of a physical quantity.

    Each component corresponds to the power of a base dimension in the SI system
    plus information (B) as an orthogonal non-SI dimension:
    time (T), length (L), mass (M), current (I), temperature (Θ),
    luminous intensity (J), amount of substance (N), and information (B).

    Arithmetic operations correspond to dimensional composition:
    - Addition (`+`) → multiplication of quantities
    - Subtraction (`-`) → division of quantities

    e.g.
    Vector(T=1, L=0, M=0, I=0, Θ=0, J=0, N=0, B=0)   => "time"
    Vector(T=0, L=2, M=0, I=0, Θ=0, J=0, N=0, B=0)   => "area"
    Vector(T=-2, L=1, M=1, I=0, Θ=0, J=0, N=0, B=0)  => "force"
    Vector(T=0, L=0, M=0, I=0, Θ=0, J=0, N=0, B=1)   => "information"
    """
    T: int = 0  # time
    L: int = 0  # length
    M: int = 0  # mass
    I: int = 0  # current
    Θ: int = 0  # temperature
    J: int = 0  # luminous intensity
    N: int = 0  # amount of substance
    B: int = 0  # information (bits)

    def __iter__(self) -> Iterator[int]:
        yield self.T
        yield self.L
        yield self.M
        yield self.I
        yield self.Θ
        yield self.J
        yield self.N
        yield self.B

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

    def __mul__(self, scalar: Union[int, float]) -> 'Vector':
        """
        Scalar multiplication of the exponent vector.

        e.g., raising a dimension to a power:

            >>> Dimension.length ** 2   # area
            >>> Dimension.time ** -1    # frequency
        """
        values = tuple(component * scalar for component in tuple(self))
        return Vector(*values)

    def __eq__(self, vector: 'Vector') -> bool:
        assert isinstance(vector, Vector), "Can only compare Vector to another Vector"
        return tuple(self) == tuple(vector)

    def __hash__(self) -> int:
        # Hash based on the string because tuples have been shown to collide
        # Not the most performant, but effective
        return hash(str(tuple(self)))


# TODO -- consider using a dataclass
@total_ordering
class Exponent:
    """
    Represents a **base–exponent pair** (e.g., 10³ or 2¹⁰).

    Provides comparison and division semantics used internally to represent
    magnitude prefixes (e.g., kilo, mega, micro).

    TODO (wittwemms): embrace fractional exponents for closure on multiplication/division.
    """
    bases = {2: math.log2, 10: math.log10}

    __slots__ = ("base", "power")

    def __init__(self, base: int, power: Union[int, float]):
        if base not in self.bases.keys():
            raise ValueError(f'Only the following bases are supported: {reduce(lambda a,b: f"{a}, {b}", self.bases.keys())}')
        self.base = base
        self.power = power

    @property
    def evaluated(self) -> float:
        """Return the numeric value of base ** power."""
        return self.base ** self.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        """Return (base, power) tuple, used for Scale lookups."""
        return self.base, self.power

    def __eq__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            raise TypeError(f'Cannot compare Exponent to non-Exponent type: {type(other)}')
        return self.evaluated == other.evaluated

    def __lt__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        return self.evaluated < other.evaluated

    def __hash__(self):
        # Hash by rounded numeric equivalence to maintain cross-base consistency
        return hash(round(self.evaluated, 15))

    # ---------- Arithmetic Semantics ----------

    def __truediv__(self, other: 'Exponent'):
        """
        Divide two Exponents.
        - If bases match, returns a relative Exponent.
        - If bases differ, returns a numeric ratio (float).
        """
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power - other.power)
        return self.evaluated / other.evaluated

    def __mul__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power + other.power)
        return float(self.evaluated * other.evaluated)

    def __pow__(self, exponent: Union[int, float]) -> "Exponent":
        """
        Raise this Exponent to a numeric power.

        Example:
            Exponent(10, 3) ** 2
            # → Exponent(base=10, power=6)
        """
        return Exponent(self.base, self.power * exponent)

    # ---------- Conversion Utilities ----------

    def to_base(self, new_base: int) -> "Exponent":
        """
        Convert this Exponent to another base representation.

        Example:
            Exponent(2, 10).to_base(10)
            # → Exponent(base=10, power=3.010299956639812)
        """
        if new_base not in self.bases:
            supported = ", ".join(map(str, self.bases))
            raise ValueError(f"Unsupported base {new_base!r}. Supported bases: {supported}")
        new_power = self.bases[new_base](self.evaluated)
        return Exponent(new_base, new_power)

    # ---------- Numeric Interop ----------

    def __float__(self) -> float:
        return float(self.evaluated)

    def __int__(self) -> int:
        return int(self.evaluated)

    # ---------- Representation ----------

    def __repr__(self) -> str:
        return f"Exponent(base={self.base}, power={self.power})"

    def __str__(self) -> str:
        return f"{self.base}^{self.power}"

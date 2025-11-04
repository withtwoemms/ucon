from dataclasses import dataclass
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

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Dimensional exponent vector tied to a basis.

``Vector`` is the algebraic object: a tuple of ``Fraction`` exponents
indexed against a :class:`~ucon.basis.types.Basis`.

Arithmetic is strict same-basis. Cross-basis operations live in
:mod:`ucon.basis.ops`, which consults a :class:`~ucon.basis.graph.BasisGraph`
for a clean (non-lossy) projection. Keeping ``Vector`` strict resolves the
load-time cycle ``vector → graph → transforms → vector`` to a DAG.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ucon.basis.types import Basis, BasisMismatch


@dataclass(frozen=True)
class Vector:
    """A dimensional exponent vector tied to a specific basis.

    Vector represents a point in dimensional space, where each component
    is the exponent of the corresponding basis component. For example,
    velocity (length/time) in SI would be Vector(SI, (1, 0, -1, 0, 0, 0, 0, 0)).

    Args:
        basis: The Basis this vector belongs to.
        components: Tuple of Fraction exponents, one per basis component.

    Raises:
        ValueError: If components length doesn't match basis length.
    """

    basis: Basis
    components: tuple[int | Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.components) != len(self.basis):
            raise ValueError(
                f"Vector has {len(self.components)} components but "
                f"basis '{self.basis.name}' has {len(self.basis)}"
            )
        object.__setattr__(self, '_hash_cache', hash((self.basis, self.components)))

    @classmethod
    def zero(cls, basis: Basis) -> "Vector":
        """Create a zero (dimensionless) vector in the given basis.

        Args:
            basis: The basis to create the zero vector against.

        Returns:
            A Vector with all components set to ``0``.
        """
        return cls(basis, tuple(0 for _ in basis))

    def __getitem__(self, key: str | int) -> Fraction:
        """Get a component by name, symbol, or index.

        Args:
            key: Component name, symbol, or integer index.

        Returns:
            The Fraction exponent for that component.
        """
        if isinstance(key, int):
            return self.components[key]
        return self.components[self.basis.index(key)]

    def __repr__(self) -> str:
        parts = []
        for comp, exp in zip(self.basis, self.components):
            if exp != 0:
                parts.append(f"{comp.name}={exp}")
        if not parts:
            return f"Vector({self.basis.name}, dimensionless)"
        return f"Vector({self.basis.name}, {', '.join(parts)})"

    def is_dimensionless(self) -> bool:
        """Return True if all exponents are zero."""
        return all(c == 0 for c in self.components)

    def __mul__(self, other: "Vector") -> "Vector":
        """Multiply dimensions (add exponents). Strict same-basis.

        Raises
        ------
        BasisMismatch
            If ``self`` and ``other`` are in different bases. Use
            :func:`ucon.basis.ops.multiply_via` for cross-basis multiplication.
        """
        if self.basis != other.basis:
            raise BasisMismatch(
                f"Cannot multiply vectors from different bases: "
                f"'{self.basis.name}' and '{other.basis.name}'",
                left=self.basis,
                right=other.basis,
                op="multiply",
            )
        return Vector(
            self.basis,
            tuple(x + y for x, y in zip(self.components, other.components)),
        )

    def __truediv__(self, other: "Vector") -> "Vector":
        """Divide dimensions (subtract exponents). Strict same-basis.

        Raises
        ------
        BasisMismatch
            If ``self`` and ``other`` are in different bases. Use
            :func:`ucon.basis.ops.divide_via` for cross-basis division.
        """
        if self.basis != other.basis:
            raise BasisMismatch(
                f"Cannot divide vectors from different bases: "
                f"'{self.basis.name}' and '{other.basis.name}'",
                left=self.basis,
                right=other.basis,
                op="divide",
            )
        return Vector(
            self.basis,
            tuple(x - y for x, y in zip(self.components, other.components)),
        )

    def __pow__(self, exponent: int | float | Fraction) -> "Vector":
        """Raise dimension to a power (multiply all exponents)."""
        if isinstance(exponent, int):
            return Vector(
                self.basis,
                tuple(c * exponent for c in self.components),
            )
        exp = Fraction(exponent)
        return Vector(
            self.basis,
            tuple(c * exp for c in self.components),
        )

    def __neg__(self) -> "Vector":
        """Negate all exponents (reciprocal dimension)."""
        return Vector(
            self.basis,
            tuple(-c for c in self.components),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector):
            return NotImplemented
        return self.basis == other.basis and self.components == other.components

    def __hash__(self) -> int:
        return self._hash_cache

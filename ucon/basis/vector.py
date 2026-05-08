# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Dimensional exponent vector tied to a basis.

``Vector`` is the algebraic object: a tuple of ``Fraction`` exponents
indexed against a :class:`~ucon.basis.types.Basis`. Cross-basis arithmetic
consults the active :class:`~ucon.basis.graph.BasisGraph` via the
top-of-file accessor in :mod:`ucon.basis.graph`.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ucon.basis.graph import get_basis_graph
from ucon.basis.types import Basis, LossyProjection, NoTransformPath


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

    def _unify_basis(self, other: "Vector") -> "tuple[Vector, Vector] | None":
        """Attempt to bring two vectors into a common basis via the active BasisGraph.

        Returns the pair (self', other') re-expressed in a common basis, or
        None if no clean (non-lossy) transform path connects them in either
        direction.

        Bases are unified by consulting the active BasisGraph (set via
        ``using_basis_graph`` or the module default). Both directions are
        tried; the first clean projection wins. A "clean" projection is one
        that does not raise :class:`LossyProjection` — i.e., no non-zero
        component would be discarded. This makes basis-extension scenarios
        (e.g., SI embedded in an extended ``economic`` basis) compose
        transparently while preserving rejection of genuinely incompatible
        bases.
        """
        if self.basis == other.basis:
            return self, other

        graph = get_basis_graph()

        # Try projecting self into other's basis.
        try:
            transform = graph.get_transform(self.basis, other.basis)
            return transform(self), other
        except (NoTransformPath, LossyProjection):
            pass

        # Try projecting other into self's basis.
        try:
            transform = graph.get_transform(other.basis, self.basis)
            return self, transform(other)
        except (NoTransformPath, LossyProjection):
            pass

        return None

    def __mul__(self, other: "Vector") -> "Vector":
        """Multiply dimensions (add exponents).

        If the two vectors are in different bases, the active
        :class:`BasisGraph` is consulted to find a common basis via a clean
        (non-lossy) projection. This makes basis-extension scenarios compose:
        a vector in ``SI`` and a vector in an ``economic`` basis built from
        ``SI`` (e.g., via ``extend_basis``) multiply by promoting the SI
        vector into the extended basis. Only when no clean path connects the
        two bases is :class:`ValueError` raised.
        """
        unified = self._unify_basis(other)
        if unified is None:
            raise ValueError(
                f"Cannot multiply vectors from different bases: "
                f"'{self.basis.name}' and '{other.basis.name}'"
            )
        a, b = unified
        return Vector(
            a.basis,
            tuple(x + y for x, y in zip(a.components, b.components)),
        )

    def __truediv__(self, other: "Vector") -> "Vector":
        """Divide dimensions (subtract exponents).

        Cross-basis division follows the same unification rule as
        :meth:`__mul__`; see that docstring for details.
        """
        unified = self._unify_basis(other)
        if unified is None:
            raise ValueError(
                f"Cannot divide vectors from different bases: "
                f"'{self.basis.name}' and '{other.basis.name}'"
            )
        a, b = unified
        return Vector(
            a.basis,
            tuple(x - y for x, y in zip(a.components, b.components)),
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

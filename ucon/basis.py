# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Basis abstraction for user-definable dimensional coordinate systems.

This module provides the foundation for representing dimensions in arbitrary
bases (SI, CGS, CGS-ESU, natural units, custom domains) without hardcoding
to a specific set of components.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Iterator, Sequence

if TYPE_CHECKING:
    pass  # Vector will be added in Phase 2


@dataclass(frozen=True)
class BasisComponent:
    """An atomic generator of a dimensional basis.

    A BasisComponent represents a single independent dimension in a basis,
    such as "length", "mass", or "time" in SI, or custom dimensions like
    "mana" or "gold" in a game domain.

    Args:
        name: The canonical name of the component (e.g., "length").
        symbol: Optional short symbol (e.g., "L"). If None, name is used.

    Examples:
        >>> length = BasisComponent("length", "L")
        >>> str(length)
        'L'
        >>> mass = BasisComponent("mass")
        >>> str(mass)
        'mass'
    """

    name: str
    symbol: str | None = None

    def __str__(self) -> str:
        return self.symbol if self.symbol is not None else self.name


class Basis:
    """An ordered collection of basis components defining a coordinate system.

    A Basis defines the dimensional coordinate system for a set of units.
    Components are indexed by both name and symbol for flexible lookup.

    Args:
        name: A descriptive name for the basis (e.g., "SI", "CGS", "Mechanics").
        components: Sequence of component names (str) or BasisComponent objects.

    Raises:
        ValueError: If component names or symbols collide.

    Examples:
        >>> mechanics = Basis("Mechanics", ["length", "mass", "time"])
        >>> len(mechanics)
        3
        >>> "length" in mechanics
        True
        >>> mechanics.index("length")
        0

        >>> si = Basis("SI", [
        ...     BasisComponent("length", "L"),
        ...     BasisComponent("mass", "M"),
        ...     BasisComponent("time", "T"),
        ... ])
        >>> "L" in si
        True
        >>> si.index("L")
        0
    """

    __slots__ = ("_name", "_components", "_index")

    def __init__(self, name: str, components: Sequence[str | BasisComponent]) -> None:
        self._name = name

        # Normalize strings to BasisComponent
        normalized: list[BasisComponent] = []
        for c in components:
            if isinstance(c, BasisComponent):
                normalized.append(c)
            else:
                normalized.append(BasisComponent(c))

        self._components: tuple[BasisComponent, ...] = tuple(normalized)

        # Build index with collision detection
        index: dict[str, int] = {}
        for i, comp in enumerate(self._components):
            # Check name collision
            if comp.name in index:
                raise ValueError(
                    f"Basis '{name}': component name '{comp.name}' "
                    f"conflicts with existing entry"
                )
            index[comp.name] = i

            # Check symbol collision (if symbol differs from name)
            if comp.symbol is not None and comp.symbol != comp.name:
                if comp.symbol in index:
                    raise ValueError(
                        f"Basis '{name}': symbol '{comp.symbol}' "
                        f"conflicts with existing name or symbol"
                    )
                index[comp.symbol] = i

        self._index: dict[str, int] = index

    @property
    def name(self) -> str:
        """The descriptive name of this basis."""
        return self._name

    @property
    def component_names(self) -> tuple[str, ...]:
        """Tuple of component names in order."""
        return tuple(c.name for c in self._components)

    def __len__(self) -> int:
        return len(self._components)

    def __iter__(self) -> Iterator[BasisComponent]:
        return iter(self._components)

    def __contains__(self, name: str) -> bool:
        return name in self._index

    def __getitem__(self, index: int) -> BasisComponent:
        return self._components[index]

    def index(self, name: str) -> int:
        """Return the index of a component by name or symbol.

        Args:
            name: Component name or symbol to look up.

        Returns:
            The zero-based index of the component.

        Raises:
            KeyError: If name/symbol is not found in this basis.
        """
        if name not in self._index:
            raise KeyError(f"'{name}' not found in basis '{self._name}'")
        return self._index[name]

    def __repr__(self) -> str:
        return f"Basis({self._name!r}, {list(self.component_names)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Basis):
            return NotImplemented
        return self._name == other._name and self._components == other._components

    def __hash__(self) -> int:
        return hash((self._name, self._components))

    def zero_vector(self) -> "Vector":
        """Create a zero vector in this basis.

        Returns:
            A Vector with all components set to Fraction(0).
        """
        return Vector(self, tuple(Fraction(0) for _ in self._components))


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
    components: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.components) != len(self.basis):
            raise ValueError(
                f"Vector has {len(self.components)} components but "
                f"basis '{self.basis.name}' has {len(self.basis)}"
            )

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
        """Multiply dimensions (add exponents)."""
        if self.basis != other.basis:
            raise ValueError(
                f"Cannot multiply vectors from different bases: "
                f"'{self.basis.name}' and '{other.basis.name}'"
            )
        return Vector(
            self.basis,
            tuple(a + b for a, b in zip(self.components, other.components)),
        )

    def __truediv__(self, other: "Vector") -> "Vector":
        """Divide dimensions (subtract exponents)."""
        if self.basis != other.basis:
            raise ValueError(
                f"Cannot divide vectors from different bases: "
                f"'{self.basis.name}' and '{other.basis.name}'"
            )
        return Vector(
            self.basis,
            tuple(a - b for a, b in zip(self.components, other.components)),
        )

    def __pow__(self, exponent: int | Fraction) -> "Vector":
        """Raise dimension to a power (multiply all exponents)."""
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
        return hash((self.basis, self.components))

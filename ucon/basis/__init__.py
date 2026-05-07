# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Basis abstraction for user-definable dimensional coordinate systems.

This package provides the foundation for representing dimensions in arbitrary
bases (SI, CGS, CGS-ESU, natural units, custom domains) without hardcoding
to a specific set of components.

Submodules
----------
- ``builtin``: Standard bases (SI, CGS, CGS-ESU, CGS-EMU, NATURAL, PLANCK, ATOMIC)
- ``transforms``: Transform types and standard transform instances
- ``graph``: BasisGraph registry and context scoping
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Iterator, Sequence

if TYPE_CHECKING:
    pass


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
        return Vector(self, tuple(0 for _ in self._components))


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

        # ``get_basis_graph`` is bound at module level via the bottom-of-file
        # re-export from :mod:`ucon.basis.graph` (whose canonical home is
        # :mod:`ucon.basis._active`). Method bodies resolve names from
        # ``__globals__`` at call time, by which point all submodules have
        # finished loading.
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


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------


class LossyProjection(Exception):
    """Raised when a basis transform would discard dimensional information.

    This occurs when a source component has a non-zero exponent but maps
    entirely to zeros in the target basis (e.g., SI current -> CGS).
    """

    def __init__(
        self,
        component: BasisComponent,
        source: Basis,
        target: Basis,
    ) -> None:
        self.component = component
        self.source = source
        self.target = target
        super().__init__(
            f"Cannot transform {source.name} -> {target.name}: "
            f"component '{component.name}' has no representation in {target.name}.\n\n"
            f"Suggestions:\n"
            f"  - Use a richer target basis that includes '{component.name}'\n"
            f"  - For same-basis unit conversion, use graph.convert() directly\n"
            f"  - To proceed with loss: transform(v, allow_projection=True)"
        )


class NoTransformPath(Exception):
    """Raised when no path exists between two bases in a BasisGraph."""

    def __init__(self, source: Basis, target: Basis) -> None:
        self.source = source
        self.target = target
        super().__init__(
            f"No transform path from '{source.name}' to '{target.name}'. "
            f"These are isolated dimensional systems."
        )


# Re-export submodule symbols for convenience
from ucon.basis.transforms import (  # noqa: E402
    BasisTransform,
    ConstantBoundBasisTransform,
    ConstantBinding,
)
from ucon.basis.graph import (  # noqa: E402
    BasisGraph,
    get_default_basis,
    get_basis_graph,
    set_default_basis_graph,
    reset_default_basis_graph,
    using_basis,
    using_basis_graph,
)

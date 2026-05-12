# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Core basis types: ``BasisComponent``, ``Basis``, ``BasisMismatch``,
``LossyProjection``, ``NoTransformPath``.

This module is the canonical home for the basis data model. It has no
dependencies on other ``ucon.basis`` submodules; everything else in the
subpackage imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence


__all__ = [
    "Basis",
    "BasisComponent",
    "BasisMismatch",
    "LossyProjection",
    "NoTransformPath",
]


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


class BasisMismatch(ValueError):
    """Raised when a same-basis Vector operation receives operands in
    different bases.

    ``Vector`` arithmetic is strict same-basis. Cross-basis arithmetic must
    go through :mod:`ucon.basis.ops`, which consults a ``BasisGraph`` for a
    clean (non-lossy) projection.

    Subclasses :class:`ValueError` so legacy ``except ValueError`` and
    regex-matched ``pytest.raises(ValueError, ...)`` sites continue to
    catch it.

    Parameters
    ----------
    message : str
        Human-readable description.
    left, right : Basis, optional
        The two bases that failed to unify.
    op : str, optional
        The operation that triggered the mismatch (e.g., ``"multiply"``,
        ``"divide"``, ``"unify"``).
    """

    def __init__(
        self,
        message: str,
        *,
        left: "Basis | None" = None,
        right: "Basis | None" = None,
        op: str | None = None,
    ) -> None:
        super().__init__(message)
        self.left = left
        self.right = right
        self.op = op

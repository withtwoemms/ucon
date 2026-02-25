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


# -----------------------------------------------------------------------------
# BasisTransform
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class BasisTransform:
    """Linear map between dimensional bases.

    Represents how each component of the source basis expresses in terms of
    the target basis components via matrix multiplication.

    Args:
        source: The source basis.
        target: The target basis.
        matrix: Transformation matrix as tuple of tuples. Shape is
            (len(source), len(target)). Entry [i][j] is the coefficient
            of target component j when transforming source component i.

    Raises:
        ValueError: If matrix dimensions don't match basis dimensions.

    Examples:
        >>> # Identity transform
        >>> identity = BasisTransform.identity(some_basis)
        >>> identity.is_identity()
        True

        >>> # SI current in CGS-ESU: I -> L^(3/2) M^(1/2) T^(-2)
        >>> transform = BasisTransform(SI, CGS_ESU, matrix)
        >>> esu_dim = transform(si_current_vector)
    """

    source: Basis
    target: Basis
    matrix: tuple[tuple[Fraction, ...], ...]

    def __post_init__(self) -> None:
        if len(self.matrix) != len(self.source):
            raise ValueError(
                f"Matrix has {len(self.matrix)} rows but source basis "
                f"'{self.source.name}' has {len(self.source)} components"
            )
        for i, row in enumerate(self.matrix):
            if len(row) != len(self.target):
                raise ValueError(
                    f"Matrix row {i} has {len(row)} columns but target basis "
                    f"'{self.target.name}' has {len(self.target)} components"
                )

    def __repr__(self) -> str:
        return f"BasisTransform({self.source.name} -> {self.target.name})"

    def __str__(self) -> str:
        """Human-readable string with matrix visualization."""
        lines = [f"BasisTransform: {self.source.name} -> {self.target.name}"]

        # Header row with target component symbols
        target_syms = [c.symbol for c in self.target]
        header = "       " + "  ".join(f"{s:>5}" for s in target_syms)
        lines.append(header)

        # Each row: source component symbol + coefficients
        for i, row in enumerate(self.matrix):
            src_sym = self.source[i].symbol
            coeffs = []
            for frac in row:
                if frac == 0:
                    coeffs.append("    .")
                elif frac.denominator == 1:
                    coeffs.append(f"{frac.numerator:>5}")
                else:
                    coeffs.append(f"{frac.numerator}/{frac.denominator}".rjust(5))
            lines.append(f"  {src_sym:>3}  " + "  ".join(coeffs))

        return "\n".join(lines)

    def __call__(self, vector: Vector, *, allow_projection: bool = False) -> Vector:
        """Transform a vector from source basis to target basis.

        Args:
            vector: The vector to transform (must be in source basis).
            allow_projection: If False (default), raise LossyProjection when
                a non-zero component would be discarded. If True, silently
                project (drop) unrepresentable components.

        Returns:
            A new Vector in the target basis.

        Raises:
            ValueError: If vector is not in the source basis.
            LossyProjection: If allow_projection=False and a non-zero
                component maps entirely to zeros in the target basis.
        """
        if vector.basis != self.source:
            raise ValueError(
                f"Vector is in basis '{vector.basis.name}' but transform "
                f"expects basis '{self.source.name}'"
            )

        # Check for lossy projection (unless explicitly allowed)
        if not allow_projection:
            for i, src_exp in enumerate(vector.components):
                if src_exp != 0:
                    # Does this component have ANY representation in target?
                    if all(self.matrix[i][j] == 0 for j in range(len(self.target))):
                        raise LossyProjection(
                            self.source[i],
                            self.source,
                            self.target,
                        )

        # Matrix-vector multiplication
        result = [Fraction(0)] * len(self.target)
        for i, src_exp in enumerate(vector.components):
            for j, transform_coeff in enumerate(self.matrix[i]):
                result[j] += src_exp * transform_coeff

        return Vector(self.target, tuple(result))

    def inverse(self) -> "BasisTransform":
        """Return the inverse transform (target -> source).

        Uses Gaussian elimination with partial pivoting over Fraction
        for exact arithmetic.

        Returns:
            A new BasisTransform from target to source.

        Raises:
            ValueError: If the matrix is not square or is singular.
        """
        n = len(self.source)
        m = len(self.target)

        if n != m:
            raise ValueError(
                f"Cannot invert non-square transform: "
                f"{self.source.name} ({n}) -> {self.target.name} ({m}). "
                f"Use embedding() for non-square transforms."
            )

        # Augment matrix with identity: [A | I]
        aug: list[list[Fraction]] = [
            [self.matrix[i][j] for j in range(n)]
            + [Fraction(1) if i == j else Fraction(0) for j in range(n)]
            for i in range(n)
        ]

        # Forward elimination with partial pivoting
        for col in range(n):
            # Find pivot (largest absolute value in column)
            max_row = col
            for row in range(col + 1, n):
                if abs(aug[row][col]) > abs(aug[max_row][col]):
                    max_row = row
            aug[col], aug[max_row] = aug[max_row], aug[col]

            if aug[col][col] == 0:
                raise ValueError(
                    f"Singular matrix: {self.source.name} -> {self.target.name} "
                    f"is not invertible"
                )

            # Eliminate below pivot
            for row in range(col + 1, n):
                factor = aug[row][col] / aug[col][col]
                for j in range(col, 2 * n):
                    aug[row][j] -= factor * aug[col][j]

        # Back substitution
        for col in range(n - 1, -1, -1):
            # Normalize pivot row
            pivot = aug[col][col]
            aug[col] = [x / pivot for x in aug[col]]

            # Eliminate above pivot
            for row in range(col):
                factor = aug[row][col]
                for j in range(2 * n):
                    aug[row][j] -= factor * aug[col][j]

        # Extract inverse from right half of augmented matrix
        inv_matrix = tuple(
            tuple(aug[i][n + j] for j in range(n)) for i in range(n)
        )

        return BasisTransform(self.target, self.source, inv_matrix)

    def embedding(self) -> "BasisTransform":
        """Return the canonical embedding (target -> source).

        For a projection A -> B, the embedding B -> A maps each B component
        back to its source A component, with zeros for unmapped A components.

        Only valid for clean projections where each target component maps
        from exactly one source component with coefficient 1.

        Returns:
            A new BasisTransform from target to source.

        Raises:
            ValueError: If the transform is not a clean projection.
        """
        n_src = len(self.source)
        n_tgt = len(self.target)

        inv_matrix: list[list[Fraction]] = [
            [Fraction(0)] * n_src for _ in range(n_tgt)
        ]

        for i in range(n_src):
            # Find which target component(s) this source maps to
            non_zero = [
                (j, self.matrix[i][j])
                for j in range(n_tgt)
                if self.matrix[i][j] != 0
            ]

            if len(non_zero) == 1 and non_zero[0][1] == 1:
                # Clean 1-to-1 mapping: source[i] -> target[j]
                j = non_zero[0][0]
                inv_matrix[j][i] = Fraction(1)
            elif len(non_zero) == 0:
                # Source component is dropped (projected out)
                pass
            else:
                raise ValueError(
                    f"Cannot create embedding: {self.source.name} -> {self.target.name} "
                    f"is not a clean projection (component {i} has complex mapping)"
                )

        return BasisTransform(
            self.target,
            self.source,
            tuple(tuple(row) for row in inv_matrix),
        )

    def __matmul__(self, other: "BasisTransform") -> "BasisTransform":
        """Compose transforms: (self @ other)(v) = self(other(v)).

        Args:
            other: Transform to apply first.

        Returns:
            A composed transform from other.source to self.target.

        Raises:
            ValueError: If other.target != self.source.
        """
        if other.target != self.source:
            raise ValueError(
                f"Cannot compose: {other.source.name} -> {other.target.name} "
                f"with {self.source.name} -> {self.target.name} "
                f"(intermediate bases don't match)"
            )

        # Matrix multiplication: C = self.matrix @ other.matrix
        new_matrix: list[list[Fraction]] = []
        for i in range(len(other.source)):
            row: list[Fraction] = []
            for j in range(len(self.target)):
                val = Fraction(0)
                for k in range(len(self.source)):
                    val += other.matrix[i][k] * self.matrix[k][j]
                row.append(val)
            new_matrix.append(tuple(row))

        return BasisTransform(other.source, self.target, tuple(new_matrix))

    @classmethod
    def identity(cls, basis: Basis) -> "BasisTransform":
        """Return the identity transform for a basis.

        Args:
            basis: The basis for the identity transform.

        Returns:
            An identity transform where source == target == basis.
        """
        n = len(basis)
        matrix = tuple(
            tuple(Fraction(1) if i == j else Fraction(0) for j in range(n))
            for i in range(n)
        )
        return cls(basis, basis, matrix)

    def is_identity(self) -> bool:
        """Check if this transform is the identity.

        Returns:
            True if source == target and matrix is identity matrix.
        """
        if self.source != self.target:
            return False
        for i, row in enumerate(self.matrix):
            for j, val in enumerate(row):
                expected = Fraction(1) if i == j else Fraction(0)
                if val != expected:
                    return False
        return True


# -----------------------------------------------------------------------------
# BasisGraph
# -----------------------------------------------------------------------------


class BasisGraph:
    """Graph of basis transforms with path-finding and composition.

    Nodes are Basis objects (dimensional coordinate systems).
    Edges are BasisTransform objects.
    Path-finding composes transforms transitively.

    Examples:
        >>> graph = BasisGraph()
        >>> graph.add_transform(SI_TO_CGS)
        >>> graph.add_transform(CGS_TO_CGS_ESU)
        >>> # Transitive composition: SI -> CGS -> CGS-ESU
        >>> transform = graph.get_transform(SI, CGS_ESU)
    """

    def __init__(self) -> None:
        self._edges: dict[Basis, dict[Basis, BasisTransform]] = {}
        self._cache: dict[tuple[Basis, Basis], BasisTransform] = {}

    def add_transform(self, transform: BasisTransform) -> None:
        """Register a transform. Does NOT auto-register inverse.

        Args:
            transform: The transform to register.
        """
        if transform.source not in self._edges:
            self._edges[transform.source] = {}
        self._edges[transform.source][transform.target] = transform
        self._cache.clear()  # Invalidate composed transforms

    def add_transform_pair(
        self,
        forward: BasisTransform,
        reverse: BasisTransform,
    ) -> None:
        """Register bidirectional transforms (e.g., projection + embedding).

        Args:
            forward: Transform A -> B.
            reverse: Transform B -> A.
        """
        self.add_transform(forward)
        self.add_transform(reverse)

    def get_transform(self, source: Basis, target: Basis) -> BasisTransform:
        """Find or compose a transform between bases.

        Args:
            source: The source basis.
            target: The target basis.

        Returns:
            A BasisTransform from source to target.

        Raises:
            NoTransformPath: If no path exists between the bases.
        """
        if source == target:
            return BasisTransform.identity(source)

        cache_key = (source, target)
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._find_path(source, target)
        if path is None:
            raise NoTransformPath(source, target)

        composed = self._compose_path(path)
        self._cache[cache_key] = composed
        return composed

    def _find_path(
        self,
        source: Basis,
        target: Basis,
    ) -> list[BasisTransform] | None:
        """BFS to find shortest transform path."""
        from collections import deque

        if source not in self._edges:
            return None

        queue: deque[tuple[Basis, list[BasisTransform]]] = deque([(source, [])])
        visited: set[Basis] = {source}

        while queue:
            current, path = queue.popleft()
            if current not in self._edges:
                continue

            for next_basis, transform in self._edges[current].items():
                if next_basis == target:
                    return path + [transform]
                if next_basis not in visited:
                    visited.add(next_basis)
                    queue.append((next_basis, path + [transform]))

        return None

    def _compose_path(self, path: list[BasisTransform]) -> BasisTransform:
        """Compose transforms along path via matrix multiplication."""
        result = path[0]
        for transform in path[1:]:
            result = transform @ result
        return result

    def are_connected(self, a: Basis, b: Basis) -> bool:
        """Check if two bases can interoperate.

        Args:
            a: First basis.
            b: Second basis.

        Returns:
            True if a path exists between the bases.
        """
        if a == b:
            return True
        return self._find_path(a, b) is not None

    def reachable_from(self, basis: Basis) -> set[Basis]:
        """Return all bases reachable from the given basis.

        Args:
            basis: The starting basis.

        Returns:
            Set of all bases reachable via transforms.
        """
        reachable: set[Basis] = {basis}
        frontier: list[Basis] = [basis]

        while frontier:
            current = frontier.pop()
            if current not in self._edges:
                continue
            for next_basis in self._edges[current]:
                if next_basis not in reachable:
                    reachable.add(next_basis)
                    frontier.append(next_basis)

        return reachable

    def with_transform(self, transform: BasisTransform) -> "BasisGraph":
        """Return a new graph with an additional transform (copy-on-extend).

        Args:
            transform: The transform to add.

        Returns:
            A new BasisGraph with the additional transform.
        """
        new_graph = BasisGraph()
        # Deep copy edges
        for src, targets in self._edges.items():
            new_graph._edges[src] = dict(targets)
        new_graph.add_transform(transform)
        return new_graph

    def __repr__(self) -> str:
        edge_count = sum(len(targets) for targets in self._edges.values())
        basis_count = len(self._edges)
        return f"BasisGraph({basis_count} bases, {edge_count} transforms)"

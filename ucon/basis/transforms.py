# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Basis transform types and standard transform instances.

Transform Types
---------------
- BasisTransform: Linear map between dimensional bases via matrix multiplication
- ConstantBinding: Binds a source dimension to a target expression via a physical constant
- ConstantBoundBasisTransform: Transform with constants that enable inversion of non-square matrices

Standard Transforms
-------------------
- SI_TO_CGS: Projects SI to CGS (drops current, temperature, amount, luminosity, information)
- SI_TO_CGS_ESU: Maps SI to CGS-ESU (current becomes derived dimension)
- CGS_TO_SI: Embedding from CGS back to SI
- SI_TO_NATURAL: Maps SI to natural units via physical constants
- NATURAL_TO_SI: Inverse of SI_TO_NATURAL
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from ucon.basis import Basis, BasisComponent, Vector, LossyProjection


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
# ConstantBinding
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ConstantBinding:
    """Binds a source dimension to a target expression via a physical constant.

    Records that `source_component` in the source basis becomes
    `target_expression` in the target basis, with the relationship
    defined by a physical constant raised to `exponent`.

    Parameters
    ----------
    source_component : BasisComponent
        The fundamental component being transformed.
    target_expression : Vector
        How it expresses in the target basis.
    constant_symbol : str
        Symbol of the constant defining this relationship (e.g., "c", "ℏ").
        We use a string rather than a Constant object to avoid circular imports
        between ucon.basis and ucon.constants.
    exponent : Fraction
        Power of the constant in the relationship (usually ±1/2 or ±1).

    Examples
    --------
    >>> # In natural units: length = ℏc/E, so L → E⁻¹ via ℏc
    >>> from fractions import Fraction
    >>> binding = ConstantBinding(
    ...     source_component=BasisComponent("length", "L"),
    ...     target_expression=Vector(NATURAL, (Fraction(-1),)),
    ...     constant_symbol="ℏc",
    ...     exponent=Fraction(1),
    ... )
    """

    source_component: BasisComponent
    target_expression: "Vector"
    constant_symbol: str
    exponent: Fraction = field(default_factory=lambda: Fraction(1))


# -----------------------------------------------------------------------------
# ConstantBoundBasisTransform
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ConstantBoundBasisTransform:
    """A basis transform with constants that enable inversion of non-square matrices.

    Extends BasisTransform with explicit constant bindings that record which
    constants define each non-trivial mapping. This enables `inverse()` to work
    on non-square transforms by providing the information needed to reverse
    derived mappings.

    Parameters
    ----------
    source : Basis
        Source basis.
    target : Basis
        Target basis.
    matrix : tuple[tuple[Fraction, ...], ...]
        Dimensional transformation matrix. Shape is (len(source), len(target)).
    bindings : tuple[ConstantBinding, ...]
        Constants that define derived relationships.

    Examples
    --------
    >>> # SI (8 dimensions) → NATURAL (1 dimension) transform
    >>> SI_TO_NATURAL = ConstantBoundBasisTransform(
    ...     source=SI,
    ...     target=NATURAL,
    ...     matrix=(...),  # 8×1 matrix
    ...     bindings=(...),  # Bindings for L, T, M, Θ → E
    ... )
    >>> # This works because bindings record how to reverse!
    >>> NATURAL_TO_SI = SI_TO_NATURAL.inverse()
    """

    source: Basis
    target: Basis
    matrix: tuple[tuple[Fraction, ...], ...]
    bindings: tuple[ConstantBinding, ...] = ()

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
        return f"ConstantBoundBasisTransform({self.source.name} -> {self.target.name})"

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

    def inverse(self) -> "ConstantBoundBasisTransform":
        """Compute the inverse transform using constant bindings.

        For each binding (src_component → target_expression via constant):
        - The inverse maps target_expression → src_component
        - The constant exponent is negated (constant^(-exponent))

        Returns
        -------
        ConstantBoundBasisTransform
            The inverse transform from target to source.

        Raises
        ------
        ValueError
            If a source component has no binding and cannot be inverted.

        Notes
        -----
        Components that map to zero (truly dropped) cannot be recovered
        and will map to zero in the inverse. Only components with bindings
        are invertible for non-square matrices.
        """
        inv_matrix = self._compute_inverse_matrix()
        inv_bindings = self._invert_bindings()

        return ConstantBoundBasisTransform(
            source=self.target,
            target=self.source,
            matrix=inv_matrix,
            bindings=inv_bindings,
        )

    def _compute_inverse_matrix(self) -> tuple[tuple[Fraction, ...], ...]:
        """Compute inverse matrix using constant bindings.

        For each binding, we record how to map from target back to source.
        The inverse matrix has shape (len(target), len(source)).
        """
        n_src = len(self.source)
        n_tgt = len(self.target)

        # Start with zero matrix of shape (n_tgt, n_src)
        inv: list[list[Fraction]] = [
            [Fraction(0)] * n_src for _ in range(n_tgt)
        ]

        # Build a set of source components that have bindings
        bound_src_indices: set[int] = set()

        # For each binding, record the reverse mapping
        for binding in self.bindings:
            src_idx = self.source.index(binding.source_component.name)
            bound_src_indices.add(src_idx)

            # The target expression tells us which target components
            # contribute to this source component
            for tgt_idx, coeff in enumerate(binding.target_expression.components):
                if coeff != 0:
                    # For the inverse: we need to invert the coefficient
                    # E.g., if L → E⁻¹ (coeff = -1), then E → L⁻¹ means
                    # multiplying by -1 to get back the L exponent
                    inv[tgt_idx][src_idx] = Fraction(1) / coeff

        # For source components without bindings, check for clean 1:1 mappings
        for i in range(n_src):
            if i in bound_src_indices:
                continue

            # Find which target component(s) this source maps to
            non_zero = [
                (j, self.matrix[i][j])
                for j in range(n_tgt)
                if self.matrix[i][j] != 0
            ]

            if len(non_zero) == 1 and non_zero[0][1] == 1:
                # Clean 1-to-1 mapping: source[i] -> target[j] with coeff 1
                j = non_zero[0][0]
                inv[j][i] = Fraction(1)
            elif len(non_zero) == 0:
                # Source component is dropped (projected out) - leave as zero
                pass
            # For more complex mappings, we rely on bindings

        return tuple(tuple(row) for row in inv)

    def _invert_bindings(self) -> tuple[ConstantBinding, ...]:
        """Invert the constant bindings (negate exponents, swap source/target)."""
        inverted: list[ConstantBinding] = []

        for binding in self.bindings:
            src_idx = self.source.index(binding.source_component.name)

            # Find the primary target component (first non-zero)
            primary_tgt_idx = None
            for tgt_idx, coeff in enumerate(binding.target_expression.components):
                if coeff != 0:
                    primary_tgt_idx = tgt_idx
                    break

            if primary_tgt_idx is None:
                continue

            # Create inverse binding: target component → source component
            inv_binding = ConstantBinding(
                source_component=self.target[primary_tgt_idx],
                target_expression=Vector(
                    self.source,
                    tuple(
                        Fraction(1) if k == src_idx else Fraction(0)
                        for k in range(len(self.source))
                    ),
                ),
                constant_symbol=binding.constant_symbol,
                exponent=-binding.exponent,  # Negate the exponent
            )
            inverted.append(inv_binding)

        return tuple(inverted)

    def as_basis_transform(self) -> BasisTransform:
        """Return as plain BasisTransform (loses binding information).

        Useful for interoperability with code expecting BasisTransform.
        """
        return BasisTransform(
            source=self.source,
            target=self.target,
            matrix=self.matrix,
        )


# -----------------------------------------------------------------------------
# Standard Transforms
# -----------------------------------------------------------------------------

from ucon.basis.builtin import SI, CGS, CGS_ESU, NATURAL  # noqa: E402

SI_TO_CGS = BasisTransform(
    SI,
    CGS,
    (
        # SI order: T, L, M, I, Θ, J, N, B
        # CGS order: L, M, T
        (Fraction(0), Fraction(0), Fraction(1)),  # T -> T (column 2 in CGS)
        (Fraction(1), Fraction(0), Fraction(0)),  # L -> L (column 0 in CGS)
        (Fraction(0), Fraction(1), Fraction(0)),  # M -> M (column 1 in CGS)
        (Fraction(0), Fraction(0), Fraction(0)),  # I -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # Θ -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # J -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # N -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # B -> (not representable)
    ),
)
"""Transform from SI to CGS.

Projects SI dimensions to CGS by preserving length, mass, and time,
and dropping current, temperature, luminous_intensity, amount_of_substance,
and information.

Warning: This is a lossy projection. Attempting to transform a vector
with non-zero current (or other dropped components) will raise
LossyProjection unless allow_projection=True.
"""

SI_TO_CGS_ESU = BasisTransform(
    SI,
    CGS_ESU,
    (
        # SI order: T, L, M, I, Θ, J, N, B
        # CGS_ESU order: L, M, T, Q
        (Fraction(0), Fraction(0), Fraction(1), Fraction(0)),  # T -> T (column 2 in CGS_ESU)
        (Fraction(1), Fraction(0), Fraction(0), Fraction(0)),  # L -> L (column 0 in CGS_ESU)
        (Fraction(0), Fraction(1), Fraction(0), Fraction(0)),  # M -> M (column 1 in CGS_ESU)
        # I -> L^(3/2) M^(1/2) T^(-2) (current as derived dimension)
        # In ESU: 1 statampere = 1 statcoulomb/s = 1 g^(1/2) cm^(3/2) s^(-2)
        (Fraction(3, 2), Fraction(1, 2), Fraction(-2), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # Θ -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # J -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # N -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # B -> (not representable)
    ),
)
"""Transform from SI to CGS-ESU.

Maps SI dimensions to CGS-ESU. Current (I) becomes a derived dimension
expressed as L^(3/2) M^(1/2) T^(-2), which is the dimensional formula
for charge/time in the ESU system.

Temperature, luminous_intensity, amount_of_substance, and information
are not representable in CGS-ESU and will raise LossyProjection if non-zero.
"""


# -----------------------------------------------------------------------------
# Embedding transforms (reverse mappings where valid)
# -----------------------------------------------------------------------------

CGS_TO_SI = SI_TO_CGS.embedding()
"""Embedding from CGS back to SI.

Maps CGS dimensions back to SI with zeros for components that were
dropped in the projection (current, temperature, amount, luminosity, angle).
"""

# Note: CGS_ESU_TO_SI cannot be created via embedding() because SI_TO_CGS_ESU
# is not a clean projection — current (I) maps to a complex derived dimension
# L^(3/2) M^(1/2) T^(-2), not a simple 1:1 mapping. Users needing CGS-ESU -> SI
# conversion should construct the transform manually based on their use case.


# -----------------------------------------------------------------------------
# Natural Units Transforms
# -----------------------------------------------------------------------------

# Bindings for SI → NATURAL (c = ℏ = k_B = 1)
_NATURAL_BINDINGS = (
    # Length: L = ℏc/E → L ~ E⁻¹ via ℏc
    ConstantBinding(
        source_component=SI[1],  # length (index 1 in SI)
        target_expression=Vector(NATURAL, (Fraction(-1),)),
        constant_symbol="ℏc",
        exponent=Fraction(1),
    ),
    # Time: T = ℏ/E → T ~ E⁻¹ via ℏ
    ConstantBinding(
        source_component=SI[0],  # time (index 0 in SI)
        target_expression=Vector(NATURAL, (Fraction(-1),)),
        constant_symbol="ℏ",
        exponent=Fraction(1),
    ),
    # Mass: M = E/c² → M ~ E via c⁻²
    ConstantBinding(
        source_component=SI[2],  # mass (index 2 in SI)
        target_expression=Vector(NATURAL, (Fraction(1),)),
        constant_symbol="c",
        exponent=Fraction(-2),
    ),
    # Temperature: Θ = E/k_B → Θ ~ E via k_B⁻¹
    ConstantBinding(
        source_component=SI[4],  # temperature (index 4 in SI)
        target_expression=Vector(NATURAL, (Fraction(1),)),
        constant_symbol="k_B",
        exponent=Fraction(-1),
    ),
)

SI_TO_NATURAL = ConstantBoundBasisTransform(
    source=SI,
    target=NATURAL,
    matrix=(
        # SI order: T, L, M, I, Θ, J, N, B
        # NATURAL order: E
        (Fraction(-1),),  # T → E⁻¹
        (Fraction(-1),),  # L → E⁻¹
        (Fraction(1),),   # M → E
        (Fraction(0),),   # I → 0 (not representable)
        (Fraction(1),),   # Θ → E
        (Fraction(0),),   # J → 0 (not representable)
        (Fraction(0),),   # N → 0 (not representable)
        (Fraction(0),),   # B → 0 (not representable)
    ),
    bindings=_NATURAL_BINDINGS,
)
"""Transform from SI to natural units.

Maps SI dimensions to the single energy dimension in natural units:
- Time (T) → E⁻¹ (via ℏ)
- Length (L) → E⁻¹ (via ℏc)
- Mass (M) → E (via c²)
- Temperature (Θ) → E (via k_B)

Current (I), luminous_intensity (J), amount_of_substance (N), and
information (B) are not representable in natural units and will raise
LossyProjection if non-zero (unless allow_projection=True).

Key consequences:
- Velocity (L/T) → E⁰ (dimensionless, since c = 1)
- Energy (ML²T⁻²) → E (as expected)
- Action (ML²T⁻¹) → E⁰ (dimensionless, since ℏ = 1)
"""

NATURAL_TO_SI = SI_TO_NATURAL.inverse()
"""Transform from natural units back to SI.

This is the inverse of SI_TO_NATURAL, computed using the constant bindings.
Allows converting natural unit dimensions back to their SI representation.

Note: Information about which specific combination of L, T, M, Θ a given
E dimension originated from is tracked via the constant bindings. However,
the numeric conversion factors require the actual constant values from
ucon.constants.
"""

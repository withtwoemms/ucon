# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Standard dimensional bases and transforms.

This module defines the standard bases (SI, CGS, CGS-ESU) and the transforms
between them. These are the building blocks for cross-system dimensional
analysis.

Bases
-----
- SI: The International System of Units (8 components)
- CGS: Centimetre-gram-second system (3 components)
- CGS_ESU: CGS electrostatic units (4 components, charge is fundamental)

Transforms
----------
- SI_TO_CGS: Projects SI to CGS (drops current, temperature, amount, luminosity, angle)
- SI_TO_CGS_ESU: Maps SI to CGS-ESU (current becomes derived: L^(3/2) M^(1/2) T^(-2))
"""

from fractions import Fraction

from ucon.basis import (
    Basis,
    BasisComponent,
    BasisTransform,
    ConstantAwareBasisTransform,
    ConstantBinding,
    Vector,
)


# -----------------------------------------------------------------------------
# Standard Bases
# -----------------------------------------------------------------------------

SI = Basis(
    "SI",
    [
        BasisComponent("time", "T"),
        BasisComponent("length", "L"),
        BasisComponent("mass", "M"),
        BasisComponent("current", "I"),
        BasisComponent("temperature", "Θ"),
        BasisComponent("luminous_intensity", "J"),
        BasisComponent("amount_of_substance", "N"),
        BasisComponent("information", "B"),
    ],
)
"""The International System of Units.

8 base dimensions in canonical order: time, length, mass, current, temperature,
luminous_intensity, amount_of_substance, and information (T, L, M, I, Θ, J, N, B).
"""

CGS = Basis(
    "CGS",
    [
        BasisComponent("length", "L"),
        BasisComponent("mass", "M"),
        BasisComponent("time", "T"),
    ],
)
"""Centimetre-gram-second system.

3 base dimensions: length, mass, time. Mechanical quantities only.
"""

CGS_ESU = Basis(
    "CGS-ESU",
    [
        BasisComponent("length", "L"),
        BasisComponent("mass", "M"),
        BasisComponent("time", "T"),
        BasisComponent("charge", "Q"),
    ],
)
"""CGS electrostatic units.

4 base dimensions: length, mass, time, charge. In CGS-ESU, charge is
a fundamental dimension (unlike SI where current is fundamental and
charge is derived as current * time).
"""


# -----------------------------------------------------------------------------
# Standard Transforms
# -----------------------------------------------------------------------------

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
# Natural Units Basis
# -----------------------------------------------------------------------------

NATURAL = Basis(
    "natural",
    [BasisComponent("energy", "E")],
)
"""Natural units basis with single energy dimension.

In natural units (particle physics conventions), physical constants c, ℏ, and k_B
are set to 1. This collapses length, time, mass, and temperature into expressions
of energy:

- c = 1  →  Length and time have same dimension
- ℏ = 1  →  Energy × time is dimensionless
- k_B = 1 →  Temperature is energy

As a result:
- Mass [M] → E (via E = mc²)
- Length [L] → E⁻¹ (via ℏc/E)
- Time [T] → E⁻¹ (via ℏ/E)
- Temperature [Θ] → E (via k_B T)
- Velocity is dimensionless (c = 1)

Electromagnetic quantities (current, etc.) are not representable in pure
natural units and will raise LossyProjection.
"""

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

SI_TO_NATURAL = ConstantAwareBasisTransform(
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

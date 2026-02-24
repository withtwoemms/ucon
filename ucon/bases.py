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

from ucon.basis import Basis, BasisComponent, BasisTransform


# -----------------------------------------------------------------------------
# Standard Bases
# -----------------------------------------------------------------------------

SI = Basis(
    "SI",
    [
        BasisComponent("length", "L"),
        BasisComponent("mass", "M"),
        BasisComponent("time", "T"),
        BasisComponent("current", "I"),
        BasisComponent("temperature", "Θ"),
        BasisComponent("amount", "N"),
        BasisComponent("luminosity", "J"),
        BasisComponent("angle", "A"),
    ],
)
"""The International System of Units.

8 base dimensions: length, mass, time, current, temperature, amount,
luminosity, and angle.
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
        (Fraction(1), Fraction(0), Fraction(0)),  # L -> L
        (Fraction(0), Fraction(1), Fraction(0)),  # M -> M
        (Fraction(0), Fraction(0), Fraction(1)),  # T -> T
        (Fraction(0), Fraction(0), Fraction(0)),  # I -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # Θ -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # N -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # J -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0)),  # A -> (not representable)
    ),
)
"""Transform from SI to CGS.

Projects SI dimensions to CGS by preserving length, mass, and time,
and dropping current, temperature, amount, luminosity, and angle.

Warning: This is a lossy projection. Attempting to transform a vector
with non-zero current (or other dropped components) will raise
LossyProjection unless allow_projection=True.
"""

SI_TO_CGS_ESU = BasisTransform(
    SI,
    CGS_ESU,
    (
        (Fraction(1), Fraction(0), Fraction(0), Fraction(0)),  # L -> L
        (Fraction(0), Fraction(1), Fraction(0), Fraction(0)),  # M -> M
        (Fraction(0), Fraction(0), Fraction(1), Fraction(0)),  # T -> T
        # I -> L^(3/2) M^(1/2) T^(-2) (current as derived dimension)
        # In ESU: 1 statampere = 1 statcoulomb/s = 1 g^(1/2) cm^(3/2) s^(-2)
        (Fraction(3, 2), Fraction(1, 2), Fraction(-2), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # Θ -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # N -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # J -> (not representable)
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),  # A -> (not representable)
    ),
)
"""Transform from SI to CGS-ESU.

Maps SI dimensions to CGS-ESU. Current (I) becomes a derived dimension
expressed as L^(3/2) M^(1/2) T^(-2), which is the dimensional formula
for charge/time in the ESU system.

Temperature, amount, luminosity, and angle are not representable in
CGS-ESU and will raise LossyProjection if non-zero.
"""


# -----------------------------------------------------------------------------
# Embedding transforms (CGS/CGS-ESU back to SI)
# -----------------------------------------------------------------------------

CGS_TO_SI = SI_TO_CGS.embedding()
"""Embedding from CGS back to SI.

Maps CGS dimensions back to SI with zeros for components that were
dropped in the projection (current, temperature, amount, luminosity, angle).
"""

CGS_ESU_TO_SI = SI_TO_CGS_ESU.embedding()
"""Embedding from CGS-ESU back to SI.

Maps CGS-ESU dimensions back to SI. Note that charge (Q) in CGS-ESU
does not have a direct representation in SI (where charge = current * time),
so this embedding maps Q to zero.
"""

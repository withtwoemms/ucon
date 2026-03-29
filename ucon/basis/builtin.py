# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Built-in dimensional bases shipped with ucon.

Bases
-----
- SI: The International System of Units (8 components)
- CGS: Centimetre-gram-second system (3 components)
- CGS_ESU: CGS electrostatic units (4 components, charge is fundamental)
- NATURAL: Natural units (1 component, energy)
"""

from ucon.basis import Basis, BasisComponent


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

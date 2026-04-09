# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Built-in dimensional bases shipped with ucon.

Bases
-----
- SI: The International System of Units (8 components)
- CGS: Centimetre-gram-second system (3 components)
- CGS_ESU: CGS electrostatic units (4 components, charge is fundamental)
- CGS_EMU: CGS electromagnetic units (4 components, magnetic pole strength is fundamental)
- NATURAL: Natural units (1 component, energy)
- PLANCK: Planck units (1 component, energy; ℏ=c=G=k_B=1)
- ATOMIC: Atomic units (1 component, energy; ℏ=e=mₑ=4πε₀=1)
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

CGS_EMU = Basis(
    "CGS-EMU",
    [
        BasisComponent("length", "L"),
        BasisComponent("mass", "M"),
        BasisComponent("time", "T"),
        BasisComponent("magnetic_pole_strength", "Φ"),
    ],
)
"""CGS electromagnetic units.

4 base dimensions: length, mass, time, magnetic pole strength. In CGS-EMU,
current (Φ) is a fundamental dimension. Charge is derived as Φ·T.
This differs from CGS-ESU where charge Q is fundamental and current is Q/T.
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

PLANCK = Basis(
    "planck",
    [BasisComponent("energy", "E")],
)
"""Planck units basis with single energy dimension.

In Planck units, physical constants ℏ, c, G, and k_B are all set to 1.
This fixes the energy scale to the Planck energy √(ℏc⁵/G) and collapses
all mechanical and thermal dimensions into powers of energy:

- Mass [M] → E (via E = mc²)
- Length [L] → E⁻¹ (via ℏc/E)
- Time [T] → E⁻¹ (via ℏ/E)
- Temperature [Θ] → E (via k_B T)

Like natural units, electromagnetic quantities (current, etc.) are not
representable and will raise LossyProjection.
"""

ATOMIC = Basis(
    "atomic",
    [BasisComponent("energy", "E")],
)
"""Atomic units (Hartree) basis with single energy dimension.

In atomic units, physical constants ℏ, e, mₑ, and 4πε₀ are all set to 1.
This collapses mechanical and electromagnetic dimensions into powers of energy:

- Mass [M] → E (via mₑc²)
- Length [L] → E⁻¹ (via Bohr radius a₀)
- Time [T] → E⁻¹ (via ℏ/Eₕ)
- Current [I] → E (via e/ℏ, since charge is dimensionless)

Temperature is not representable (k_B ≠ 1) and will raise LossyProjection.
"""

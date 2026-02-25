#!/usr/bin/env python
# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Example: Physical Constants in Physics Formulas

Demonstrates using CODATA physical constants with ucon
for real physics calculations like E=mc², photon energy,
and gravitational force.
"""

from ucon import constants, units


def main():
    # -------------------------------------------------------------------------
    # Inspecting Constants
    # -------------------------------------------------------------------------
    print("=== Physical Constants ===")
    print(f"Speed of light:      {constants.c}")
    print(f"Planck constant:     {constants.h}")
    print(f"Gravitational const: {constants.G}")
    print()

    # -------------------------------------------------------------------------
    # SI Defining Constants (Exact)
    # -------------------------------------------------------------------------
    print("=== SI Defining Constants (Exact) ===")
    print(f"c  = {constants.speed_of_light.value} m/s (exact: {constants.c.is_exact})")
    print(f"h  = {constants.planck_constant.value} J·s (exact: {constants.h.is_exact})")
    print(f"e  = {constants.elementary_charge.value} C (exact: {constants.e.is_exact})")
    print(f"kB = {constants.boltzmann_constant.value} J/K (exact: {constants.k_B.is_exact})")
    print(f"NA = {constants.avogadro_constant.value} mol⁻¹ (exact: {constants.N_A.is_exact})")
    print()

    # -------------------------------------------------------------------------
    # Measured Constants (With Uncertainty)
    # -------------------------------------------------------------------------
    print("=== Measured Constants (With Uncertainty) ===")
    print(f"G = {constants.G.value} ± {constants.G.uncertainty} m³/(kg·s²)")
    print(f"α = {constants.alpha.value} ± {constants.alpha.uncertainty} (dimensionless)")
    print(f"mₑ = {constants.m_e.value} ± {constants.m_e.uncertainty} kg")
    print()

    # -------------------------------------------------------------------------
    # E = mc² (Mass-Energy Equivalence)
    # -------------------------------------------------------------------------
    print("=== E = mc² ===")
    mass = units.kilogram(1)
    energy = mass * constants.c ** 2
    print(f"Mass:   {mass}")
    print(f"Energy: {energy}")
    print(f"        = {energy.quantity:.3e} J")
    print()

    # -------------------------------------------------------------------------
    # E = hν (Photon Energy)
    # -------------------------------------------------------------------------
    print("=== E = hν (Photon Energy) ===")
    # Green light frequency (~540 THz)
    frequency = units.hertz(5.4e14)
    photon_energy = constants.h * frequency
    print(f"Frequency:     {frequency}")
    print(f"Photon energy: {photon_energy}")
    print(f"               = {photon_energy.quantity:.3e} J")
    print()

    # -------------------------------------------------------------------------
    # de Broglie Wavelength: λ = h/p
    # -------------------------------------------------------------------------
    print("=== de Broglie Wavelength: λ = h/p ===")
    # Electron moving at 1% speed of light
    electron_mass = constants.m_e.as_number()
    velocity = constants.c * 0.01
    momentum = electron_mass * velocity
    wavelength = constants.h / momentum
    print(f"Electron mass: {electron_mass}")
    print(f"Velocity:      {velocity}")
    print(f"Momentum:      {momentum}")
    print(f"Wavelength:    {wavelength}")
    print()

    # -------------------------------------------------------------------------
    # Gravitational Force: F = Gm₁m₂/r²
    # -------------------------------------------------------------------------
    print("=== Gravitational Force (with uncertainty) ===")
    m1 = units.kilogram(1000)  # 1 ton
    m2 = units.kilogram(1000)  # 1 ton
    r = units.meter(1)
    force = constants.G * m1 * m2 / (r ** 2)
    print(f"m₁ = {m1}")
    print(f"m₂ = {m2}")
    print(f"r  = {r}")
    print(f"F  = {force}")
    print(f"   Note: Uncertainty propagated from G")
    print()

    # -------------------------------------------------------------------------
    # Ideal Gas Constant: R = kB × NA
    # -------------------------------------------------------------------------
    print("=== Ideal Gas Constant ===")
    k_B = constants.boltzmann_constant.value
    N_A = constants.avogadro_constant.value
    R = constants.molar_gas_constant.value
    print(f"k_B × N_A = {k_B * N_A:.6f} J/(mol·K)")
    print(f"R         = {R:.6f} J/(mol·K)")
    print(f"Match:      {abs(R - k_B * N_A) < 1e-10}")
    print()

    # -------------------------------------------------------------------------
    # Using Aliases
    # -------------------------------------------------------------------------
    print("=== Alias Examples ===")
    print("Unicode aliases:")
    print(f"  constants.c    = {constants.c.symbol}")
    print(f"  constants.α    = {constants.alpha.symbol}")
    print(f"  constants.ε₀   = {constants.epsilon_0.symbol}")
    print()
    print("ASCII aliases:")
    print(f"  constants.hbar      = {constants.hbar.symbol}")
    print(f"  constants.epsilon_0 = {constants.epsilon_0.symbol}")
    print(f"  constants.m_e       = {constants.m_e.symbol}")


if __name__ == "__main__":
    main()

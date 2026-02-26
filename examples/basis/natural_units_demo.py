#!/usr/bin/env python3
"""
ConstantAwareBasisTransform Demo: Natural Units

Demonstrates how ConstantAwareBasisTransform enables inversion of non-square
transformation matrices by tracking physical constant bindings.

Background:
-----------
In natural units (particle physics), physical constants c, h-bar, and k_B
are set to 1, collapsing length, time, mass, and temperature into a single
energy dimension. This creates a non-square transform (8 SI dims -> 1 energy).

A regular BasisTransform cannot invert a non-square matrix. But by recording
which constants define each dimensional relationship (via ConstantBinding),
ConstantAwareBasisTransform can compute the inverse.

Key concepts:
- Non-square transformation matrices (e.g., 8x1)
- ConstantBinding records constant-dimension relationships
- inverse() works despite non-square matrix
- Velocity becomes dimensionless when c=1
- Mass and energy share the same dimension (E=mc^2)
"""

from fractions import Fraction

from ucon.basis import (
    Basis,
    BasisComponent,
    ConstantAwareBasisTransform,
    ConstantBinding,
    LossyProjection,
    Vector,
)


def custom_example():
    """Demonstrate building a custom ConstantAwareBasisTransform."""
    print("=" * 70)
    print("PART 1: Custom ConstantAwareBasisTransform")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Define two bases: Mechanics (3D) and Energy (1D)
    # -------------------------------------------------------------------------
    MECHANICS = Basis(
        "Mechanics",
        [
            BasisComponent("length", "L"),
            BasisComponent("mass", "M"),
            BasisComponent("time", "T"),
        ],
    )

    ENERGY = Basis(
        "Energy",
        [BasisComponent("energy", "E")],
    )

    print(f"\nSource basis: {MECHANICS.name} ({len(MECHANICS)} components)")
    print(f"Target basis: {ENERGY.name} ({len(ENERGY)} components)")
    print(f"Matrix shape: {len(MECHANICS)} x {len(ENERGY)} (non-square)")

    # -------------------------------------------------------------------------
    # Define how each mechanics dimension maps to energy
    # -------------------------------------------------------------------------
    # In natural units with c = h-bar = 1:
    #   Length: L = h-bar*c / E  =>  L ~ E^(-1)
    #   Mass:   M = E / c^2      =>  M ~ E^(+1)
    #   Time:   T = h-bar / E    =>  T ~ E^(-1)

    bindings = (
        ConstantBinding(
            source_component=MECHANICS[0],  # length
            target_expression=Vector(ENERGY, (Fraction(-1),)),  # E^(-1)
            constant_symbol="h-bar*c",
            exponent=Fraction(1),
        ),
        ConstantBinding(
            source_component=MECHANICS[1],  # mass
            target_expression=Vector(ENERGY, (Fraction(1),)),  # E^(+1)
            constant_symbol="c",
            exponent=Fraction(-2),
        ),
        ConstantBinding(
            source_component=MECHANICS[2],  # time
            target_expression=Vector(ENERGY, (Fraction(-1),)),  # E^(-1)
            constant_symbol="h-bar",
            exponent=Fraction(1),
        ),
    )

    print("\nConstant bindings (how each dimension relates to energy):")
    for b in bindings:
        sign = "+" if b.target_expression["E"] > 0 else ""
        print(f"  {b.source_component.symbol} -> E^({sign}{b.target_expression['E']}) "
              f"via {b.constant_symbol}^{b.exponent}")

    # -------------------------------------------------------------------------
    # Create the ConstantAwareBasisTransform
    # -------------------------------------------------------------------------
    transform = ConstantAwareBasisTransform(
        source=MECHANICS,
        target=ENERGY,
        matrix=(
            (Fraction(-1),),  # L -> E^(-1)
            (Fraction(1),),   # M -> E^(+1)
            (Fraction(-1),),  # T -> E^(-1)
        ),
        bindings=bindings,
    )

    print(f"\nCreated transform: {transform}")

    # -------------------------------------------------------------------------
    # Transform dimensional vectors
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Transforming dimensional vectors:")
    print("-" * 50)

    # Length
    length = Vector(MECHANICS, (Fraction(1), Fraction(0), Fraction(0)))
    length_natural = transform(length)
    print(f"\nLength (L^1):")
    print(f"  Mechanics: {length}")
    print(f"  Energy:    {length_natural}  (inverse energy)")

    # Mass
    mass = Vector(MECHANICS, (Fraction(0), Fraction(1), Fraction(0)))
    mass_natural = transform(mass)
    print(f"\nMass (M^1):")
    print(f"  Mechanics: {mass}")
    print(f"  Energy:    {mass_natural}  (energy!)")

    # Velocity (L/T)
    velocity = Vector(MECHANICS, (Fraction(1), Fraction(0), Fraction(-1)))
    velocity_natural = transform(velocity)
    print(f"\nVelocity (L^1 T^-1):")
    print(f"  Mechanics: {velocity}")
    print(f"  Energy:    {velocity_natural}")
    print(f"  Dimensionless? {velocity_natural.is_dimensionless()}  (c = 1!)")

    # Energy (M L^2 T^-2)
    energy = Vector(MECHANICS, (Fraction(2), Fraction(1), Fraction(-2)))
    energy_natural = transform(energy)
    print(f"\nEnergy (M^1 L^2 T^-2):")
    print(f"  Mechanics: {energy}")
    print(f"  Energy:    {energy_natural}  (pure energy, as expected)")

    # -------------------------------------------------------------------------
    # Compute the inverse transform
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Computing inverse (non-square matrix!):")
    print("-" * 50)

    inverse = transform.inverse()
    print(f"\nInverse transform: {inverse}")
    print(f"Matrix shape: {len(inverse.source)} x {len(inverse.target)}")

    print("\nInverse bindings (exponents negated):")
    for b in inverse.bindings:
        print(f"  {b.source_component.symbol} -> {b.target_expression.basis.name} "
              f"via {b.constant_symbol}^{b.exponent}")

    # -------------------------------------------------------------------------
    # Verify round-trip
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Round-trip verification:")
    print("-" * 50)

    # E^1 in energy basis
    e1 = Vector(ENERGY, (Fraction(1),))
    back_to_mechanics = inverse(e1)
    print(f"\nE^1 in Energy basis -> Mechanics:")
    print(f"  {e1} -> {back_to_mechanics}")


def builtin_natural_units():
    """Demonstrate the built-in SI_TO_NATURAL transform."""
    print("\n")
    print("=" * 70)
    print("PART 2: Built-in SI -> NATURAL Transform")
    print("=" * 70)

    from ucon import NATURAL, SI, SI_TO_NATURAL, NATURAL_TO_SI, BasisVector

    print(f"\nSI basis: {len(SI)} components")
    print(f"NATURAL basis: {len(NATURAL)} component (energy only)")
    print(f"\nSI_TO_NATURAL is a ConstantAwareBasisTransform:")
    print(f"  Type: {type(SI_TO_NATURAL).__name__}")
    print(f"  Bindings: {len(SI_TO_NATURAL.bindings)}")

    print("\n" + "-" * 50)
    print("SI dimension mappings to natural units:")
    print("-" * 50)

    # SI order: T, L, M, I, Theta, J, N, B
    dims = [
        ("Time", (1, 0, 0, 0, 0, 0, 0, 0)),
        ("Length", (0, 1, 0, 0, 0, 0, 0, 0)),
        ("Mass", (0, 0, 1, 0, 0, 0, 0, 0)),
        ("Temperature", (0, 0, 0, 0, 1, 0, 0, 0)),
        ("Velocity (L/T)", (-1, 1, 0, 0, 0, 0, 0, 0)),
        ("Energy (ML^2/T^2)", (-2, 2, 1, 0, 0, 0, 0, 0)),
        ("Action (ML^2/T)", (-1, 2, 1, 0, 0, 0, 0, 0)),
        ("Momentum (ML/T)", (-1, 1, 1, 0, 0, 0, 0, 0)),
    ]

    for name, comps in dims:
        vec = BasisVector(SI, tuple(Fraction(c) for c in comps))
        result = SI_TO_NATURAL(vec)
        dimless = " (dimensionless!)" if result.is_dimensionless() else ""
        print(f"  {name:20} -> E^{result['E']}{dimless}")

    # -------------------------------------------------------------------------
    # Show lossy projection for electromagnetic dimensions
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Electromagnetic dimensions (not representable):")
    print("-" * 50)

    si_current = BasisVector(SI, (
        Fraction(0), Fraction(0), Fraction(0), Fraction(1),
        Fraction(0), Fraction(0), Fraction(0), Fraction(0),
    ))

    print(f"\nSI Current (I^1): {si_current}")
    try:
        SI_TO_NATURAL(si_current)
    except LossyProjection as e:
        print(f"  Raises LossyProjection: current has no representation")
        print(f"  (Pure natural units only cover mechanical + thermal dimensions)")

    # With allow_projection=True
    result = SI_TO_NATURAL(si_current, allow_projection=True)
    print(f"\n  With allow_projection=True: {result}")

    # -------------------------------------------------------------------------
    # Inverse transform
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Inverse transform (NATURAL_TO_SI):")
    print("-" * 50)

    print(f"\nNATURAL_TO_SI computed via inverse():")
    print(f"  Type: {type(NATURAL_TO_SI).__name__}")
    print(f"  Source: {NATURAL_TO_SI.source.name}")
    print(f"  Target: {NATURAL_TO_SI.target.name}")

    # Transform E^1 back to SI
    natural_energy = BasisVector(NATURAL, (Fraction(1),))
    si_result = NATURAL_TO_SI(natural_energy)
    print(f"\n  E^1 in natural -> {si_result}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("ConstantAwareBasisTransform Demonstration")
    print("=" * 70)
    print("""
This demo shows how ConstantAwareBasisTransform enables inversion of
non-square transformation matrices by recording constant bindings.

In particle physics natural units (c = h-bar = k_B = 1):
  - Velocity becomes dimensionless (c = 1)
  - Mass and energy share dimension (E = mc^2)
  - Length and time are inverse energy (L = h-bar*c/E, T = h-bar/E)
""")

    custom_example()
    builtin_natural_units()

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

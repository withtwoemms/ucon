#!/usr/bin/env python3
"""
ConstantAwareBasisTransform Demo: Geometrized Units (General Relativity)

Demonstrates creating a custom ConstantAwareBasisTransform for geometrized
units, commonly used in general relativity where G = c = 1.

Background:
-----------
In geometrized units:
  - c = 1: Length and time have the same dimension
  - G = 1: Mass becomes a length (Schwarzschild radius ~ GM/c^2)

This gives:
  - Length [L] -> L (unchanged, our reference)
  - Time [T] -> L (via c)
  - Mass [M] -> L (via G/c^2)

Key result: Everything is measured in lengths!
  - 1 solar mass ~ 1.48 km (Schwarzschild radius / 2)
  - 1 second ~ 3e8 meters (light-second)

This example shows:
  1. Creating a custom geometrized basis
  2. Building a ConstantAwareBasisTransform from SI to geometrized
  3. Transforming physical quantities
  4. Computing the inverse transform
  5. Verifying that the Schwarzschild radius formula simplifies
"""

from fractions import Fraction

from ucon.basis import (
    Basis,
    BasisComponent,
    ConstantAwareBasisTransform,
    ConstantBinding,
    Vector,
)


def main():
    print("=" * 70)
    print("Geometrized Units (General Relativity): G = c = 1")
    print("=" * 70)
    print("""
In general relativity, setting G = c = 1 simplifies equations dramatically.
The Schwarzschild radius formula:

  r_s = 2GM/c^2  (SI)  -->  r_s = 2M  (geometrized)

This example builds a ConstantAwareBasisTransform for this system.
""")

    # -------------------------------------------------------------------------
    # Define the bases
    # -------------------------------------------------------------------------
    # Simplified SI with just mechanical dimensions
    SI_MECH = Basis(
        "SI-Mechanical",
        [
            BasisComponent("length", "L"),
            BasisComponent("mass", "M"),
            BasisComponent("time", "T"),
        ],
    )

    # Geometrized: everything is length
    GEOMETRIZED = Basis(
        "Geometrized",
        [BasisComponent("length", "L")],
    )

    print(f"Source: {SI_MECH.name} ({len(SI_MECH)} components: L, M, T)")
    print(f"Target: {GEOMETRIZED.name} ({len(GEOMETRIZED)} component: L)")

    # -------------------------------------------------------------------------
    # Define the dimensional mappings with constant bindings
    # -------------------------------------------------------------------------
    # c = 1:  T -> L  (1 second = c meters ~ 3e8 m)
    # G = 1:  M -> L  (1 kg = G/c^2 meters ~ 7.4e-28 m)
    #
    # More precisely:
    #   [L] = L           (reference)
    #   [T] = L / c       so T -> L via c^(-1)
    #   [M] = L * c^2 / G so M -> L via (G/c^2)^(+1)

    bindings = (
        # Length stays length (coefficient 1, no constant needed)
        # We don't need a binding for clean 1:1 mappings

        # Time -> Length via c
        ConstantBinding(
            source_component=SI_MECH[2],  # time
            target_expression=Vector(GEOMETRIZED, (Fraction(1),)),  # L^1
            constant_symbol="c",
            exponent=Fraction(1),  # multiply by c to get length
        ),
        # Mass -> Length via G/c^2
        ConstantBinding(
            source_component=SI_MECH[1],  # mass
            target_expression=Vector(GEOMETRIZED, (Fraction(1),)),  # L^1
            constant_symbol="G/c^2",
            exponent=Fraction(1),  # multiply by G/c^2 to get length
        ),
    )

    print("\nConstant bindings:")
    print("  L -> L (identity, no binding needed)")
    for b in bindings:
        print(f"  {b.source_component.symbol} -> L via {b.constant_symbol}^{b.exponent}")

    # -------------------------------------------------------------------------
    # Build the transform
    # -------------------------------------------------------------------------
    # Matrix: each SI dimension maps to L^1 in geometrized
    SI_TO_GEOMETRIZED = ConstantAwareBasisTransform(
        source=SI_MECH,
        target=GEOMETRIZED,
        matrix=(
            (Fraction(1),),  # L -> L
            (Fraction(1),),  # M -> L (mass is a length!)
            (Fraction(1),),  # T -> L (time is a length!)
        ),
        bindings=bindings,
    )

    print(f"\nTransform: {SI_TO_GEOMETRIZED}")
    print(f"Matrix: 3x1 (non-square)")

    # -------------------------------------------------------------------------
    # Transform example dimensions
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Dimensional transformations:")
    print("-" * 50)

    examples = [
        ("Length", (1, 0, 0)),
        ("Mass", (0, 1, 0)),
        ("Time", (0, 0, 1)),
        ("Velocity (L/T)", (1, 0, -1)),
        ("Acceleration (L/T^2)", (1, 0, -2)),
        ("Force (ML/T^2)", (1, 1, -2)),
        ("Energy (ML^2/T^2)", (2, 1, -2)),
        ("Schwarzschild factor (M/L)", (-1, 1, 0)),
    ]

    for name, (l, m, t) in examples:
        vec = Vector(SI_MECH, (Fraction(l), Fraction(m), Fraction(t)))
        result = SI_TO_GEOMETRIZED(vec)
        exp = result["L"]

        if result.is_dimensionless():
            interpretation = "dimensionless"
        elif exp == 1:
            interpretation = "length"
        elif exp == -1:
            interpretation = "inverse length"
        elif exp == 2:
            interpretation = "area"
        else:
            interpretation = f"L^{exp}"

        print(f"  {name:25} -> L^{exp:+2} ({interpretation})")

    # -------------------------------------------------------------------------
    # Physical interpretation
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Physical interpretations:")
    print("-" * 50)

    print("""
In geometrized units:
  - Velocity is dimensionless (like c = 1 in natural units)
  - Mass has dimension of length (Schwarzschild radius)
  - Energy has dimension of length (via E = Mc^2 = M in geom.)
  - The Schwarzschild radius r_s = 2GM/c^2 becomes r_s = 2M

Example masses in geometrized units:
  - Sun:   M_sun ~ 1.48 km
  - Earth: M_earth ~ 4.4 mm
  - Human: M_human ~ 5e-26 m (unmeasurably small!)
""")

    # -------------------------------------------------------------------------
    # Compute inverse transform
    # -------------------------------------------------------------------------
    print("-" * 50)
    print("Inverse transform (GEOMETRIZED -> SI):")
    print("-" * 50)

    GEOMETRIZED_TO_SI = SI_TO_GEOMETRIZED.inverse()
    print(f"\n{GEOMETRIZED_TO_SI}")
    print(f"Matrix: 1x3")

    print("\nInverse bindings (exponents negated):")
    for b in GEOMETRIZED_TO_SI.bindings:
        print(f"  {b.source_component.symbol} -> {b.target_expression}")
        print(f"    via {b.constant_symbol}^{b.exponent}")

    # -------------------------------------------------------------------------
    # Verify round-trip
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Round-trip verification:")
    print("-" * 50)

    # L^1 in geometrized
    geom_length = Vector(GEOMETRIZED, (Fraction(1),))
    si_result = GEOMETRIZED_TO_SI(geom_length)
    print(f"\nL^1 (geometrized) -> SI: {si_result}")

    # L^2 in geometrized (area)
    geom_area = Vector(GEOMETRIZED, (Fraction(2),))
    si_area = GEOMETRIZED_TO_SI(geom_area)
    print(f"L^2 (geometrized) -> SI: {si_area}")

    # -------------------------------------------------------------------------
    # The Schwarzschild radius simplification
    # -------------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Schwarzschild radius formula:")
    print("-" * 50)
    print("""
SI formula:       r_s = 2GM/c^2
                  [r_s] = L

Dimensional analysis in SI:
  [G] = L^3 M^-1 T^-2
  [M] = M
  [c^2] = L^2 T^-2

  [GM/c^2] = (L^3 M^-1 T^-2)(M) / (L^2 T^-2)
           = L^3 T^-2 / L^2 T^-2
           = L  (correct!)

In geometrized units (G = c = 1):
  r_s = 2M

  Since [M] = L in geometrized units,
  [r_s] = L (still correct, but the formula is simpler!)
""")

    # Verify dimensionally
    print("Verification via transform:")
    # GM/c^2 in SI has dimension [L^3 M^-1 T^-2][M] / [L^2 T^-2] = L
    # Which equals just [M] when transformed to geometrized
    si_mass_dim = Vector(SI_MECH, (Fraction(0), Fraction(1), Fraction(0)))
    geom_mass = SI_TO_GEOMETRIZED(si_mass_dim)
    print(f"  [M]_SI in geometrized: {geom_mass}")
    print(f"  Confirms: mass dimension = length dimension in geometrized units")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

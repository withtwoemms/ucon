#!/usr/bin/env python3
"""
ConstantAwareBasisTransform Demo: Classical Elemental Units

A fantasy unit system based on classical elements where dimensions are
FUNDAMENTALLY different from SI - not just scaled versions.

The Elemental Basis:
--------------------
In the world of Alchemia, natural philosophers discovered that reality
is composed of five fundamental essences:

  - Fire (Fi):   The principle of transformation and energy release
  - Water (Wa):  The principle of flow and continuity
  - Earth (Ea):  The principle of substance and permanence
  - Air (Ai):    The principle of motion and change
  - Aether (Ae): The quintessence - purely magical, has NO physical analog

Key Features:
-------------
1. CONVOLUTIONS: Elemental dimensions map to COMBINATIONS of SI dimensions:
   - Fire is not just energy, it's POWER (energy/time) - transformation rate
   - Water is not volume, it's FLOW (volume/time) - continuous motion
   - Air is not length, it's VELOCITY (length/time) - change itself

2. NON-SI DIMENSION: Aether has no physical representation and raises
   LossyProjection when transformed to SI - it's purely magical!

3. NON-SQUARE MATRIX: 5 elemental dimensions -> 4 SI dimensions

This demonstrates ConstantAwareBasisTransform with true dimensional complexity.
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


def main():
    print("=" * 70)
    print("  THE ELEMENTAL BASIS: Classical Alchemy Meets Dimensional Analysis")
    print("=" * 70)

    # =========================================================================
    # PART 1: Define the Elemental and SI Bases
    # =========================================================================
    print("\n" + "=" * 70)
    print("PART 1: The Five Elements")
    print("=" * 70)

    ELEMENTAL = Basis(
        "Elemental",
        [
            BasisComponent("fire", "Fi"),    # Transformation/power
            BasisComponent("water", "Wa"),   # Flow
            BasisComponent("earth", "Ea"),   # Substance
            BasisComponent("air", "Ai"),     # Motion
            BasisComponent("aether", "Ae"),  # The quintessence (magical)
        ],
    )

    SI_MECH = Basis(
        "SI-Mechanical",
        [
            BasisComponent("length", "L"),
            BasisComponent("mass", "M"),
            BasisComponent("time", "T"),
            BasisComponent("temperature", "K"),  # For heat/fire concepts
        ],
    )

    print(f"""
The Elemental Basis ({len(ELEMENTAL)} dimensions):

  Fire (Fi):   "That which transforms"
               Not mere energy, but the RATE of transformation
               Maps to: POWER = M * L^2 * T^-3

  Water (Wa):  "That which flows"
               Not volume, but continuous FLOW
               Maps to: VOLUMETRIC FLOW = L^3 * T^-1

  Earth (Ea):  "That which endures"
               Pure substance, mass itself
               Maps to: MASS = M

  Air (Ai):    "That which moves"
               Not distance, but VELOCITY - motion itself
               Maps to: VELOCITY = L * T^-1

  Aether (Ae): "The quintessence"
               Purely magical, exists beyond physical reality
               Maps to: NOTHING (raises LossyProjection!)

SI-Mechanical Basis ({len(SI_MECH)} dimensions): L, M, T, K
Matrix shape: {len(ELEMENTAL)} x {len(SI_MECH)} = 5 x 4 (non-square!)
""")

    # =========================================================================
    # PART 2: Define the Alchemical Constants
    # =========================================================================
    print("=" * 70)
    print("PART 2: The Alchemical Constants")
    print("=" * 70)

    print("""
The great alchemist Paracelsus discovered the Universal Constants that
bridge elemental essences to mundane physics:

  Phi (phi_fire):    The Promethean constant
                     Relates Fire to Power (M*L^2*T^-3)
                     "One unit of Fire equals phi watts of transformation"

  Psi (psi_water):   The Heraclitan constant
                     Relates Water to Flow (L^3*T^-1)
                     "All things flow at rate psi"

  Sigma (sigma_earth): The Stoic constant
                       Relates Earth to Mass (M)
                       "Substance is conserved at ratio sigma"

  Omega (omega_air): The Zephyrian constant
                     Relates Air to Velocity (L*T^-1)
                     "Motion itself has measure omega"

  Aether has NO constant - it transcends physical measurement!
""")

    # =========================================================================
    # PART 3: Build the ConstantAwareBasisTransform
    # =========================================================================
    print("=" * 70)
    print("PART 3: The Elemental Transform Matrix")
    print("=" * 70)

    # SI order: L, M, T, K
    # Fire  -> Power      = M^1 * L^2 * T^-3  = (2, 1, -3, 0)
    # Water -> Flow       = L^3 * T^-1        = (3, 0, -1, 0)
    # Earth -> Mass       = M^1               = (0, 1,  0, 0)
    # Air   -> Velocity   = L^1 * T^-1        = (1, 0, -1, 0)
    # Aether -> Nothing   = 0                 = (0, 0,  0, 0)

    bindings = (
        ConstantBinding(
            source_component=ELEMENTAL[0],  # Fire
            target_expression=Vector(SI_MECH, (Fraction(2), Fraction(1), Fraction(-3), Fraction(0))),
            constant_symbol="phi",  # Promethean constant
            exponent=Fraction(1),
        ),
        ConstantBinding(
            source_component=ELEMENTAL[1],  # Water
            target_expression=Vector(SI_MECH, (Fraction(3), Fraction(0), Fraction(-1), Fraction(0))),
            constant_symbol="psi",  # Heraclitan constant
            exponent=Fraction(1),
        ),
        ConstantBinding(
            source_component=ELEMENTAL[2],  # Earth
            target_expression=Vector(SI_MECH, (Fraction(0), Fraction(1), Fraction(0), Fraction(0))),
            constant_symbol="sigma",  # Stoic constant
            exponent=Fraction(1),
        ),
        ConstantBinding(
            source_component=ELEMENTAL[3],  # Air
            target_expression=Vector(SI_MECH, (Fraction(1), Fraction(0), Fraction(-1), Fraction(0))),
            constant_symbol="omega",  # Zephyrian constant
            exponent=Fraction(1),
        ),
        # NOTE: No binding for Aether - it has no physical representation!
    )

    ELEMENTAL_TO_SI = ConstantAwareBasisTransform(
        source=ELEMENTAL,
        target=SI_MECH,
        matrix=(
            # L,  M,  T,  K
            (Fraction(2), Fraction(1), Fraction(-3), Fraction(0)),   # Fi -> M*L^2*T^-3 (power)
            (Fraction(3), Fraction(0), Fraction(-1), Fraction(0)),   # Wa -> L^3*T^-1 (flow)
            (Fraction(0), Fraction(1), Fraction(0), Fraction(0)),    # Ea -> M (mass)
            (Fraction(1), Fraction(0), Fraction(-1), Fraction(0)),   # Ai -> L*T^-1 (velocity)
            (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),    # Ae -> 0 (nothing!)
        ),
        bindings=bindings,
    )

    print(f"Transform: {ELEMENTAL_TO_SI}")
    print(f"\nTransformation matrix (5 x 4, non-square!):")
    print("           L    M    T    K")
    elem_names = ["Fire ", "Water", "Earth", "Air  ", "Aethr"]
    for i, name in enumerate(elem_names):
        row = ELEMENTAL_TO_SI.matrix[i]
        formatted = []
        for v in row:
            if v == 0:
                formatted.append("   .")
            elif v > 0:
                formatted.append(f"  +{v}")
            else:
                formatted.append(f"  {v}")
        print(f"  {name}  {''.join(formatted)}")

    print("""
Notice:
  - Fire's row (2, 1, -3, 0) encodes POWER: L^2 * M * T^-3
  - Water's row (3, 0, -1, 0) encodes FLOW: L^3 * T^-1
  - Air's row (1, 0, -1, 0) encodes VELOCITY: L * T^-1
  - Aether's row is all zeros - it has NO physical representation!
""")

    # =========================================================================
    # PART 4: Transform Base Elemental Dimensions
    # =========================================================================
    print("=" * 70)
    print("PART 4: Base Element Transformations")
    print("=" * 70)

    elements = [
        ("Fire", (1, 0, 0, 0, 0)),
        ("Water", (0, 1, 0, 0, 0)),
        ("Earth", (0, 0, 1, 0, 0)),
        ("Air", (0, 0, 0, 1, 0)),
    ]

    for name, comps in elements:
        vec = Vector(ELEMENTAL, tuple(Fraction(c) for c in comps))
        result = ELEMENTAL_TO_SI(vec)

        # Format SI result
        si_parts = []
        for c in SI_MECH:
            exp = result[c.symbol]
            if exp == 1:
                si_parts.append(c.symbol)
            elif exp == -1:
                si_parts.append(f"{c.symbol}^-1")
            elif exp != 0:
                si_parts.append(f"{c.symbol}^{exp}")

        print(f"  {name:6} -> {' * '.join(si_parts)}")

    # =========================================================================
    # PART 5: Aether - The Unphysical Dimension
    # =========================================================================
    print("\n" + "=" * 70)
    print("PART 5: Aether - Beyond Physical Reality")
    print("=" * 70)

    aether = Vector(ELEMENTAL, (Fraction(0), Fraction(0), Fraction(0), Fraction(0), Fraction(1)))

    print(f"""
Aether (Ae^1) is the quintessence - it exists in the elemental realm
but has NO representation in mundane physics.

Attempting to transform pure Aether to SI:
  {aether}
""")

    try:
        ELEMENTAL_TO_SI(aether)
        print("  (This should not happen!)")
    except LossyProjection as e:
        print(f"  Raises LossyProjection!")
        print(f"  '{e.component.name}' cannot be expressed in {e.target.name}")

    print("\n  With allow_projection=True (the Aether is... lost):")
    result = ELEMENTAL_TO_SI(aether, allow_projection=True)
    print(f"  {aether} -> {result}")
    print(f"  Dimensionless? {result.is_dimensionless()} (the magic dissipates)")

    # =========================================================================
    # PART 6: Compound Elemental Quantities
    # =========================================================================
    print("\n" + "=" * 70)
    print("PART 6: Compound Elemental Quantities")
    print("=" * 70)

    print("""
Alchemists work with compound essences. Let's see how they map to physics:
""")

    compounds = [
        ("Steam (Fire + Water)", (1, 1, 0, 0, 0),
         "Hot flowing substance"),
        ("Earthquake (Earth * Air)", (0, 0, 1, 1, 0),
         "Moving mass = momentum!"),
        ("Lightning (Fire / Air)", (1, 0, 0, -1, 0),
         "Power per velocity = force!"),
        ("Flood (Water / Air)", (0, 1, 0, -1, 0),
         "Flow per velocity = area!"),
        ("Volcano (Fire * Earth / Water)", (1, -1, 1, 0, 0),
         "Complex transformation"),
        ("Enchantment (Fire + Aether)", (1, 0, 0, 0, 1),
         "Magical power - LOSSY!"),
    ]

    for name, comps, desc in compounds:
        vec = Vector(ELEMENTAL, tuple(Fraction(c) for c in comps))

        # Check if it has Aether
        has_aether = comps[4] != 0

        if has_aether:
            print(f"\n  {name}")
            print(f"    Description: {desc}")
            print(f"    Elemental:   {vec}")
            try:
                ELEMENTAL_TO_SI(vec)
            except LossyProjection:
                print(f"    SI:          LOSSY! (contains Aether)")
                projected = ELEMENTAL_TO_SI(vec, allow_projection=True)
                si_parts = []
                for c in SI_MECH:
                    exp = projected[c.symbol]
                    if exp == 1:
                        si_parts.append(c.symbol)
                    elif exp != 0:
                        si_parts.append(f"{c.symbol}^{exp}")
                print(f"    Projected:   {' * '.join(si_parts) if si_parts else '(dimensionless)'}")
        else:
            result = ELEMENTAL_TO_SI(vec)
            si_parts = []
            for c in SI_MECH:
                exp = result[c.symbol]
                if exp == 1:
                    si_parts.append(c.symbol)
                elif exp != 0:
                    si_parts.append(f"{c.symbol}^{exp}")

            print(f"\n  {name}")
            print(f"    Description: {desc}")
            print(f"    Elemental:   {vec}")
            print(f"    SI:          {' * '.join(si_parts) if si_parts else '(dimensionless)'}")

    # =========================================================================
    # PART 7: The Inverse Transform
    # =========================================================================
    print("\n" + "=" * 70)
    print("PART 7: The Inverse Transform (SI to Elemental)")
    print("=" * 70)

    SI_TO_ELEMENTAL = ELEMENTAL_TO_SI.inverse()

    print(f"""
The inverse transform lets us express physical quantities in elemental terms.
Note: The inverse is a 4x5 matrix!

{SI_TO_ELEMENTAL}

Inverse bindings (constants inverted):""")

    for b in SI_TO_ELEMENTAL.bindings:
        src = b.source_component.symbol
        # Find non-zero target components
        tgt_parts = []
        for c in ELEMENTAL:
            exp = b.target_expression[c.symbol]
            if exp == 1:
                tgt_parts.append(c.symbol)
            elif exp != 0:
                tgt_parts.append(f"{c.symbol}^{exp}")
        print(f"  {src} -> {' * '.join(tgt_parts)} via {b.constant_symbol}^{b.exponent}")

    # =========================================================================
    # PART 8: Physical Quantities in Elemental Terms
    # =========================================================================
    print("\n" + "=" * 70)
    print("PART 8: Expressing Physics in Elemental Terms")
    print("=" * 70)

    print("""
How do familiar physical quantities appear in the elemental worldview?
""")

    # SI quantities: (L, M, T, K)
    physical = [
        ("Length (L)", (1, 0, 0, 0)),
        ("Mass (M)", (0, 1, 0, 0)),
        ("Time (T)", (0, 0, 1, 0)),
        ("Velocity (L/T)", (1, 0, -1, 0)),
        ("Force (M*L/T^2)", (1, 1, -2, 0)),
        ("Energy (M*L^2/T^2)", (2, 1, -2, 0)),
        ("Power (M*L^2/T^3)", (2, 1, -3, 0)),
    ]

    for name, comps in physical:
        si_vec = Vector(SI_MECH, tuple(Fraction(c) for c in comps))
        elem_result = SI_TO_ELEMENTAL(si_vec)

        # Format elemental result
        elem_parts = []
        for c in ELEMENTAL:
            exp = elem_result[c.symbol]
            if exp == 1:
                elem_parts.append(c.symbol)
            elif exp == -1:
                elem_parts.append(f"{c.symbol}^-1")
            elif exp != 0:
                elem_parts.append(f"{c.symbol}^{exp}")

        print(f"  {name:22} -> {' * '.join(elem_parts) if elem_parts else '(pure number)'}")

    print("""
Observations:
  - Velocity IS Air (Ai) - motion itself!
  - Power IS Fire (Fi) - transformation rate!
  - Energy is Fire * Air^-1 - transformation without motion (stored potential)
  - Force is Fire * Air^-2 - transformation resisting motion
""")

    # =========================================================================
    # PART 9: The Philosopher's Stone Problem
    # =========================================================================
    print("=" * 70)
    print("PART 9: The Philosopher's Stone Problem")
    print("=" * 70)

    print("""
The legendary Philosopher's Stone is said to combine ALL five elements
in perfect unity. What happens when we try to measure it physically?

  Philosopher's Stone: Fi^1 * Wa^1 * Ea^1 * Ai^1 * Ae^1
""")

    stone = Vector(ELEMENTAL, (Fraction(1), Fraction(1), Fraction(1), Fraction(1), Fraction(1)))
    print(f"  Elemental dimension: {stone}")

    try:
        ELEMENTAL_TO_SI(stone)
    except LossyProjection:
        print("  Physical dimension:  UNMEASURABLE (contains Aether)")
        projected = ELEMENTAL_TO_SI(stone, allow_projection=True)

        si_parts = []
        for c in SI_MECH:
            exp = projected[c.symbol]
            if exp != 0:
                si_parts.append(f"{c.symbol}^{exp}")

        print(f"  Projected (losing Ae): {' * '.join(si_parts)}")
        print("""
  The Stone's physical projection is L^6 * M^2 * T^-5:
    = (Power) * (Flow) * (Mass) * (Velocity)
    = (L^2*M*T^-3) * (L^3*T^-1) * (M) * (L*T^-1)
    = L^6 * M^2 * T^-5

  But without Aether, it's just... a very energetic fluid.
  The TRUE Philosopher's Stone transcends physical measurement!
""")

    print("=" * 70)
    print("  'The wise alchemist knows: some things cannot be weighed.'")
    print("   - Attributed to Hermes Trismegistus")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

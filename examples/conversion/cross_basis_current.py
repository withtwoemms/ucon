#!/usr/bin/env python3
"""
Cross-Basis Electrical Conversion: SI Ampere -> CGS-ESU Statampere

Demonstrates non-trivial cross-basis conversion where the dimensional
structure is fundamentally different between systems.

In SI:      Current (I) is a fundamental dimension
In CGS-ESU: Current is derived as L^(3/2) M^(1/2) T^(-2)

The BasisTransform performs non-trivial dimensional remapping:
    SI current (I^1) -> CGS-ESU (L^(3/2) M^(1/2) T^(-2))

Physical relationship: 1 ampere = 2.99792458e9 statamperes
(exact: c/10 where c is speed of light in cm/s)

Key concepts:
- Fractional exponents in dimensional transformation
- Fundamental dimension becomes derived combination
- Physical constants emerge from unit system definitions
"""

from fractions import Fraction

from ucon import Dimension, units
from ucon.basis import BasisGraph, Vector
from ucon.bases import CGS_ESU, SI_TO_CGS_ESU
from ucon.core import Unit
from ucon.graph import ConversionGraph
from ucon.maps import LinearMap


def main():
    # -------------------------------------------------------------------------
    # Create CGS-ESU current dimension
    # -------------------------------------------------------------------------
    # In CGS-ESU, current has dimension L^(3/2) M^(1/2) T^(-2)
    # This is what SI current (I) transforms to via SI_TO_CGS_ESU
    #
    # Physical origin: In CGS-ESU, charge is defined via Coulomb's law with k=1:
    #   F = q1*q2/r^2
    # This gives charge dimension: [q] = [F]^(1/2) [L] = M^(1/2) L^(3/2) T^(-1)
    # And current = charge/time: [I] = M^(1/2) L^(3/2) T^(-2)

    cgs_esu_current = Dimension(
        vector=Vector(CGS_ESU, (
            Fraction(3, 2),   # L^(3/2)
            Fraction(1, 2),   # M^(1/2)
            Fraction(-2),     # T^(-2)
            Fraction(0),      # Q^0 (charge component unused for current)
        )),
        name="cgs_esu_current",
        symbol="I_esu",
    )
    statampere = Unit(
        name="statampere",
        dimension=cgs_esu_current,
        aliases=("statA", "esu_current"),
    )

    # -------------------------------------------------------------------------
    # Set up BasisGraph with SI <-> CGS-ESU connectivity
    # -------------------------------------------------------------------------
    basis_graph = BasisGraph()
    basis_graph = basis_graph.with_transform(SI_TO_CGS_ESU)

    # -------------------------------------------------------------------------
    # Create ConversionGraph with BasisGraph
    # -------------------------------------------------------------------------
    graph = ConversionGraph()
    graph._basis_graph = basis_graph

    # -------------------------------------------------------------------------
    # Add cross-basis edge: ampere (SI) -> statampere (CGS-ESU)
    # -------------------------------------------------------------------------
    # 1 ampere = 2.99792458e9 statamperes
    # This factor is c/10 where c = 2.99792458e10 cm/s (speed of light)
    # The factor arises from the definition of electromagnetic units
    STATAMPERE_PER_AMPERE = 2.99792458e9

    graph.add_edge(
        src=units.ampere,
        dst=statampere,
        map=LinearMap(STATAMPERE_PER_AMPERE),
        basis_transform=SI_TO_CGS_ESU,
    )

    # -------------------------------------------------------------------------
    # Perform conversion
    # -------------------------------------------------------------------------
    conversion_map = graph.convert(src=units.ampere, dst=statampere)
    result = conversion_map(1)
    print(f"1 ampere = {result:.6e} statamperes")

    # -------------------------------------------------------------------------
    # Show dimensional transformation details
    # -------------------------------------------------------------------------
    print(f"\nDimensional transformation:")
    print(f"  SI ampere dimension:       {units.ampere.dimension}")
    print(f"  CGS-ESU statampere dim:    {statampere.dimension}")

    # -------------------------------------------------------------------------
    # Show the relevant row of the transform matrix
    # -------------------------------------------------------------------------
    print(f"\nSI_TO_CGS_ESU transform (current row):")
    print(f"  I (SI) -> L^(3/2) M^(1/2) T^(-2) (CGS-ESU)")
    print(f"\nFull transform matrix:")
    print(SI_TO_CGS_ESU)

    # -------------------------------------------------------------------------
    # Verify the transform was applied correctly
    # -------------------------------------------------------------------------
    # Transform SI ampere's dimension vector through SI_TO_CGS_ESU
    si_current_vector = units.ampere.dimension.vector
    transformed = SI_TO_CGS_ESU(si_current_vector)

    print(f"\nVerification:")
    print(f"  SI ampere vector:          {si_current_vector}")
    print(f"  After SI_TO_CGS_ESU:       {transformed}")
    print(f"  Expected (statampere):     {statampere.dimension.vector}")
    print(f"  Match: {transformed == statampere.dimension.vector}")

    # -------------------------------------------------------------------------
    # Inspect RebasedUnit
    # -------------------------------------------------------------------------
    rebased_units = graph.list_rebased_units()
    rebased_ampere = rebased_units[units.ampere]

    print(f"\nRebasedUnit created:")
    print(f"  Original: {rebased_ampere.original.name}")
    print(f"  Rebased dimension: {rebased_ampere.rebased_dimension}")

    # -------------------------------------------------------------------------
    # Compatibility check
    # -------------------------------------------------------------------------
    print(f"\nCompatibility:")
    print(f"  ampere.is_compatible(statampere, basis_graph): "
          f"{units.ampere.is_compatible(statampere, basis_graph=basis_graph)}")


if __name__ == "__main__":
    main()

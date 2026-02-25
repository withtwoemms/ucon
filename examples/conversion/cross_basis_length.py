#!/usr/bin/env python3
"""
Cross-Basis Conversion Example

Demonstrates non-trivial cross-basis conversion using ConversionGraph.convert()
where units from different dimensional bases (SI and CGS-ESU) are connected
via BasisTransform.

Key concepts:
- SI basis has 8 components: T, L, M, I, Theta, J, N, B
- CGS-ESU basis has 4 components: L, M, T, Q (charge is fundamental)
- BasisTransform maps dimensions between bases
- RebasedUnit wraps a unit in a different basis's dimension partition
- BasisGraph tracks connectivity between bases
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
    # Create a CGS-ESU length unit with proper dimension
    # -------------------------------------------------------------------------
    # CGS-ESU basis order: L, M, T, Q (charge is fundamental)
    # Length dimension: L^1 M^0 T^0 Q^0
    cgs_esu_length = Dimension(
        vector=Vector(CGS_ESU, (Fraction(1), Fraction(0), Fraction(0), Fraction(0))),
        name="cgs_esu_length",
        symbol="L",
    )
    centimeter = Unit(name="centimeter", dimension=cgs_esu_length, aliases=("cm",))

    # -------------------------------------------------------------------------
    # Set up BasisGraph connecting SI and CGS-ESU
    # -------------------------------------------------------------------------
    basis_graph = BasisGraph()
    basis_graph = basis_graph.with_transform(SI_TO_CGS_ESU)

    # -------------------------------------------------------------------------
    # Create ConversionGraph with BasisGraph for cross-basis validation
    # -------------------------------------------------------------------------
    graph = ConversionGraph()
    graph._basis_graph = basis_graph

    # -------------------------------------------------------------------------
    # Add cross-basis edge: meter (SI) -> centimeter (CGS-ESU)
    # -------------------------------------------------------------------------
    # 1 meter = 100 centimeters
    # The basis_transform validates that SI length maps to CGS-ESU length
    graph.add_edge(
        src=units.meter,          # SI unit (dimension in SI basis)
        dst=centimeter,           # CGS-ESU unit (dimension in CGS-ESU basis)
        map=LinearMap(100),       # scaling factor: 1 m = 100 cm
        basis_transform=SI_TO_CGS_ESU,
    )

    # -------------------------------------------------------------------------
    # Perform conversion
    # -------------------------------------------------------------------------
    conversion_map = graph.convert(src=units.meter, dst=centimeter)
    result = conversion_map(1)
    print(f"1 meter = {result} centimeters")

    # -------------------------------------------------------------------------
    # Inspect the RebasedUnit created by add_edge
    # -------------------------------------------------------------------------
    rebased_units = graph.list_rebased_units()
    rebased_meter = rebased_units[units.meter]

    print(f"\nRebased unit details:")
    print(f"  Original unit: {rebased_meter.original.name}")
    print(f"  Rebased dimension: {rebased_meter.rebased_dimension}")
    print(f"  Transform: {rebased_meter.basis_transform!r}")

    # -------------------------------------------------------------------------
    # Show the SI_TO_CGS_ESU transform matrix
    # -------------------------------------------------------------------------
    # The interesting part: current (I) maps to L^(3/2) M^(1/2) T^(-2)
    # This is because in ESU, charge is fundamental and current is derived
    print(f"\nBasis transform matrix:")
    print(SI_TO_CGS_ESU)

    # -------------------------------------------------------------------------
    # Verify dimensional compatibility via Unit.is_compatible
    # -------------------------------------------------------------------------
    print(f"\nCompatibility checks:")
    print(f"  meter.is_compatible(centimeter, basis_graph): "
          f"{units.meter.is_compatible(centimeter, basis_graph=basis_graph)}")
    print(f"  meter.is_compatible(units.second): "
          f"{units.meter.is_compatible(units.second)}")


if __name__ == "__main__":
    main()

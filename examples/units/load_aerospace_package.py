#!/usr/bin/env python3
"""
Loading Domain-Specific Unit Packages

Demonstrates loading and using a TOML-defined unit package for aerospace units.
The aerospace.ucon.toml file defines:
  - Units: slug, knot, nautical_mile, poundal
  - Edges: conversions to SI base units (kg, m/s, m, N)

Usage:
    python load_aerospace_package.py
    python load_aerospace_package.py /path/to/custom.ucon.toml
"""

from __future__ import annotations

import sys
from pathlib import Path


def load_and_demonstrate(toml_path: str | Path):
    """Load a unit package and demonstrate conversions."""
    from ucon import Number, get_default_graph
    from ucon.core import Scale
    from ucon.packages import load_package, PackageLoadError

    # -------------------------------------------------------------------------
    # Load the package from TOML
    # -------------------------------------------------------------------------
    try:
        package = load_package(toml_path)
    except PackageLoadError as e:
        print(f"Error loading package: {e}")
        sys.exit(1)

    print(f"Loaded package: {package.name} v{package.version}")
    print(f"Description: {package.description}")
    print()

    # -------------------------------------------------------------------------
    # Show package contents
    # -------------------------------------------------------------------------
    print("Units defined:")
    for unit_def in package.units:
        aliases = ", ".join(unit_def.aliases) if unit_def.aliases else "(none)"
        print(f"  {unit_def.name} [{unit_def.dimension}] aliases: {aliases}")
    print()

    print("Edges defined:")
    for edge_def in package.edges:
        print(f"  {edge_def.src} -> {edge_def.dst} (factor: {edge_def.factor})")
    print()

    # -------------------------------------------------------------------------
    # Create graph with package applied
    # -------------------------------------------------------------------------
    base_graph = get_default_graph()
    graph = base_graph.with_package(package)

    print(f"Graph now has {len(graph._name_registry)} registered unit names")
    print()

    # -------------------------------------------------------------------------
    # Demonstrate conversions
    # -------------------------------------------------------------------------
    from ucon.graph import using_graph

    with using_graph(graph):
        from ucon import get_unit_by_name

        # Resolve package units
        slug = get_unit_by_name("slug")
        knot = get_unit_by_name("knot")
        nautical_mile = get_unit_by_name("nautical_mile")
        poundal = get_unit_by_name("poundal")

        # Resolve SI units
        kilogram = get_unit_by_name("kilogram")
        meter_per_second = get_unit_by_name("meter/second")
        meter = get_unit_by_name("meter")
        newton = get_unit_by_name("newton")

        print("Conversions:")

        # Mass: slug -> kilogram
        mass_map = graph.convert(src=slug, dst=kilogram)
        print(f"  1 slug = {mass_map(1):.4f} kg")

        # Velocity: knot -> m/s
        vel_map = graph.convert(src=knot, dst=meter_per_second)
        print(f"  1 knot = {vel_map(1):.6f} m/s")

        # Length: nautical mile -> meter
        len_map = graph.convert(src=nautical_mile, dst=meter)
        print(f"  1 nautical mile = {len_map(1):.0f} m")

        # Force: poundal -> newton
        force_map = graph.convert(src=poundal, dst=newton)
        print(f"  1 poundal = {force_map(1):.6f} N")

        print()

        # -------------------------------------------------------------------------
        # Use Number.to() for quantity conversion
        # -------------------------------------------------------------------------
        print("Quantity conversions with Number.to():")

        # Aircraft groundspeed
        groundspeed = Number(450, knot)
        groundspeed_si = groundspeed.to(meter_per_second, graph=graph)
        print(f"  {groundspeed} = {groundspeed_si}")

        # Flight distance
        distance = Number(2500, nautical_mile)
        distance_si = distance.to(meter, graph=graph)
        print(f"  {distance} = {Number(distance_si.value / 1000, Scale.kilo * get_unit_by_name('meter'))}")

        # Aircraft mass (Boeing 747 empty weight)
        mass = Number(12000, slug)
        mass_si = mass.to(kilogram, graph=graph)
        print(f"  {mass} = {mass_si}")

        print()

        # -------------------------------------------------------------------------
        # Alias resolution
        # -------------------------------------------------------------------------
        print("Alias resolution:")
        print(f"  'kt' resolves to: {get_unit_by_name('kt').name}")
        print(f"  'nmi' resolves to: {get_unit_by_name('nmi').name}")
        print(f"  'pdl' resolves to: {get_unit_by_name('pdl').name}")


def main():
    # Default path relative to this script
    default_path = Path(__file__).parent.parent / "units" / "aerospace.ucon.toml"

    if len(sys.argv) > 1:
        toml_path = sys.argv[1]
    else:
        toml_path = default_path

    load_and_demonstrate(toml_path)


if __name__ == "__main__":
    main()

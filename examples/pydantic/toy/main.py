#!/usr/bin/env python
# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Vehicle simulation example.

Demonstrates:
- Loading YAML config into Pydantic models with Number[Dimension] validation
- Dimensional validation at function boundaries via @enforce_dimensions
- Unit conversion and arithmetic

Usage:
    python main.py
    python main.py path/to/custom/config.yaml
"""

import sys
from pathlib import Path

import yaml

from ucon import units

from models import Settings
from physics import drag_force, kinetic_energy, stopping_distance, time_to_stop


def load_settings(config_path: Path) -> Settings:
    """Load and validate configuration from YAML."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return Settings(**data)


def main(config_path: Path) -> None:
    print(f"Loading configuration from {config_path}\n")
    settings = load_settings(config_path)

    # Extract values (already validated as correct dimensions)
    mass = settings.vehicle.mass
    max_speed = settings.vehicle.max_speed
    drag_coeff = settings.vehicle.drag_coefficient
    area = settings.vehicle.frontal_area
    air_density = settings.environment.air_density
    gravity = settings.environment.gravity

    print("=== Vehicle Properties ===")
    print(f"  Mass:             {mass}")
    print(f"  Max speed:        {max_speed}")
    print(f"  Drag coefficient: {drag_coeff}")
    print(f"  Frontal area:     {area}")
    print()

    print("=== Environment ===")
    print(f"  Air density:      {air_density}")
    print(f"  Gravity:          {gravity}")
    print()

    # Calculate kinetic energy at max speed
    ke = kinetic_energy(mass, max_speed)
    print("=== Calculations ===")
    print(f"  Kinetic energy at max speed:")
    print(f"    {ke}")
    print()

    # Calculate drag force at max speed
    drag = drag_force(air_density, max_speed, drag_coeff, area)
    print(f"  Drag force at max speed:")
    print(f"    {drag}")
    print()

    # Calculate stopping distance with 8 m/s² braking
    braking = (units.meter / units.second ** 2)(8)
    distance = stopping_distance(max_speed, braking)
    time = time_to_stop(max_speed, braking)
    print(f"  Emergency braking ({braking}):")
    print(f"    Stopping distance: {distance.to(units.meter)}")
    print(f"    Time to stop:      {time.to(units.second)}")
    print()

    # Demonstrate dimension error catching
    print("=== Dimension Safety ===")
    try:
        # Intentionally swap mass and velocity
        kinetic_energy(max_speed, mass)
    except (ValueError, TypeError) as e:
        print(f"  Caught dimension error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = Path(sys.argv[1])
    else:
        config_file = Path(__file__).parent / "config.yaml"

    main(config_file)

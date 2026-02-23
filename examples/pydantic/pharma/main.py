#!/usr/bin/env python
# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Pharmaceutical compounding example.

Demonstrates:
- Complex Pydantic models with Number[Dimension] validation
- Custom dimension validation (mg/kg/day)
- Cross-field validation (min < max)
- Uncertainty propagation through calculations
- Computed properties and methods

Usage:
    python main.py
    python main.py path/to/custom/config.yaml
"""

import sys
from pathlib import Path

import yaml

from ucon import Scale, units

from models import PharmacySettings

# Define milliliter for convenience
milliliter = Scale.milli * units.liter


def load_settings(config_path: Path) -> PharmacySettings:
    """Load and validate configuration from YAML."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return PharmacySettings(**data)


def main(config_path: Path) -> None:
    print(f"Loading configuration from {config_path}\n")
    settings = load_settings(config_path)

    print("=== Drug Information ===")
    print(f"  Name:          {settings.drug.name}")
    print(f"  Concentration: {settings.drug.concentration}")
    print(f"  Stability:     {settings.drug.stability_duration}")
    print(f"  Storage temp:  {settings.drug.storage_temp.min} to "
          f"{settings.drug.storage_temp.max}")
    print()

    print("=== Patient Information ===")
    print(f"  Weight:        {settings.patient.weight}")
    print(f"  Age category:  {settings.patient.age_category}")
    print()

    print("=== Dosing Parameters ===")
    print(f"  Target dose:   {settings.dosing.target_dose}")
    print(f"  Frequency:     {settings.dosing.frequency} doses/day")
    print(f"  Dose range:    {settings.dosing.min_single_dose} to "
          f"{settings.dosing.max_single_dose}")
    print()

    # Calculate doses (uncertainty propagates automatically)
    daily_dose = settings.calculate_daily_dose()
    single_dose = settings.calculate_single_dose()
    volume = settings.calculate_volume_per_dose()

    print("=== Calculated Values ===")
    print(f"  Daily dose:    {daily_dose}")
    print(f"  Single dose:   {single_dose}")
    print(f"  Volume/dose:   {volume}")
    print(f"                 {volume.to(milliliter)}")
    print()

    # Calculate doses per vial
    vial_volume = milliliter(100)
    doses_per_vial = settings.calculate_doses_per_vial(vial_volume)
    print(f"  Doses per {vial_volume} vial: {doses_per_vial}")
    print()

    # Infusion calculations (if configured)
    if settings.infusion:
        print("=== Infusion ===")
        print(f"  Rate:          {settings.infusion.rate}")
        print(f"  Duration:      {settings.infusion.duration}")
        print(f"  Total volume:  {settings.infusion.total_volume}")
        print()

    # Demonstrate validation errors
    print("=== Validation Examples ===")
    demonstrate_validation_errors()


def demonstrate_validation_errors() -> None:
    """Show how various validation errors are caught."""
    import yaml
    from pydantic import ValidationError

    # Wrong dimension for concentration
    bad_config_1 = """
drug:
  name: "Test"
  concentration: { quantity: 250, unit: "mg" }
  stability_duration: { quantity: 14, unit: "day" }
  storage_temp:
    min: { quantity: 2, unit: "degC" }
    max: { quantity: 8, unit: "degC" }
patient:
  weight: { quantity: 70, unit: "kg" }
  age_category: "adult"
dosing:
  target_dose: { quantity: 25, unit: "mg/kg/day" }
  frequency: 3
  max_single_dose: { quantity: 500, unit: "mg" }
  min_single_dose: { quantity: 100, unit: "mg" }
"""
    try:
        PharmacySettings(**yaml.safe_load(bad_config_1))
    except ValidationError as e:
        print(f"  Wrong dimension: {e.errors()[0]['msg'][:60]}...")

    # Temperature range violation
    bad_config_2 = """
drug:
  name: "Test"
  concentration: { quantity: 250, unit: "mg/mL" }
  stability_duration: { quantity: 14, unit: "day" }
  storage_temp:
    min: { quantity: 10, unit: "degC" }
    max: { quantity: 5, unit: "degC" }
patient:
  weight: { quantity: 70, unit: "kg" }
  age_category: "adult"
dosing:
  target_dose: { quantity: 25, unit: "mg/kg/day" }
  frequency: 3
  max_single_dose: { quantity: 500, unit: "mg" }
  min_single_dose: { quantity: 100, unit: "mg" }
"""
    try:
        PharmacySettings(**yaml.safe_load(bad_config_2))
    except ValidationError as e:
        print(f"  Range violation: {e.errors()[0]['msg'][:60]}...")

    # Negative value
    bad_config_3 = """
drug:
  name: "Test"
  concentration: { quantity: 250, unit: "mg/mL" }
  stability_duration: { quantity: 14, unit: "day" }
  storage_temp:
    min: { quantity: 2, unit: "degC" }
    max: { quantity: 8, unit: "degC" }
patient:
  weight: { quantity: -70, unit: "kg" }
  age_category: "adult"
dosing:
  target_dose: { quantity: 25, unit: "mg/kg/day" }
  frequency: 3
  max_single_dose: { quantity: 500, unit: "mg" }
  min_single_dose: { quantity: 100, unit: "mg" }
"""
    try:
        PharmacySettings(**yaml.safe_load(bad_config_3))
    except ValidationError as e:
        print(f"  Negative value: {e.errors()[0]['msg'][:60]}...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = Path(sys.argv[1])
    else:
        config_file = Path(__file__).parent / "config.yaml"

    main(config_file)

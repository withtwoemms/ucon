# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Pharmaceutical compounding configuration models.

Demonstrates advanced Pydantic patterns with Number[Dimension]:
- Composite dimension validation
- Custom validators (positivity, range checking)
- Cross-field validation (min < max)
- Computed properties
- Uncertainty propagation through calculations
"""

from typing import Annotated, Literal

from pydantic import BaseModel, field_validator, model_validator
from pydantic.functional_validators import AfterValidator

from ucon import Dimension, Number, Scale, units
from ucon.pydantic import Number as PydanticNumber, constrained_number

# Define milliliter for convenience
milliliter = Scale.milli * units.liter


# ---------------------------------------------------------------------------
# Custom validators
# ---------------------------------------------------------------------------


def must_be_positive(n: Number) -> Number:
    """Validator: quantity must be > 0."""
    if n.quantity <= 0:
        raise ValueError(f"must be positive, got {n.quantity}")
    return n


# Subscriptable positive number type
PositiveNumber = constrained_number(AfterValidator(must_be_positive))


# ---------------------------------------------------------------------------
# Nested models with constrained ranges
# ---------------------------------------------------------------------------


class TemperatureRange(BaseModel):
    """Temperature bounds with cross-field validation."""

    min: PydanticNumber[Dimension.temperature]
    max: PydanticNumber[Dimension.temperature]

    @model_validator(mode='after')
    def min_less_than_max(self) -> 'TemperatureRange':
        """Ensure min < max after converting to common unit."""
        min_k = self.min.to(units.kelvin).quantity
        max_k = self.max.to(units.kelvin).quantity
        if min_k >= max_k:
            raise ValueError(
                f"min ({self.min}) must be less than max ({self.max})"
            )
        return self


# ---------------------------------------------------------------------------
# Domain models with dimensional constraints
# ---------------------------------------------------------------------------


class DrugConfig(BaseModel):
    """Drug formulation properties."""

    name: str
    concentration: PositiveNumber[Dimension.density]
    stability_duration: PositiveNumber[Dimension.time]
    storage_temp: TemperatureRange


class PatientConfig(BaseModel):
    """Patient demographics."""

    weight: PositiveNumber[Dimension.mass]
    age_category: Literal["pediatric", "adult", "geriatric"]

    @property
    def weight_kg(self) -> float:
        """Weight in kg for calculations."""
        return self.weight.to(units.kilogram).quantity


class DosingConfig(BaseModel):
    """Dosing parameters."""

    target_dose: PositiveNumber  # mg/kg/day - validated below
    frequency: int
    max_single_dose: PositiveNumber[Dimension.mass]
    min_single_dose: PositiveNumber[Dimension.mass]

    @field_validator('target_dose')
    @classmethod
    def validate_dose_rate_dimension(cls, v: Number) -> Number:
        """Ensure target_dose has dose-rate dimension (mass/mass/time)."""
        expected = Dimension.mass / Dimension.mass / Dimension.time
        actual = v.unit.dimension if v.unit else Dimension.none
        if actual != expected:
            raise ValueError(
                f"target_dose must have dimension '{expected.name}', "
                f"got '{actual.name}'"
            )
        return v

    @field_validator('frequency')
    @classmethod
    def validate_frequency_positive(cls, v: int) -> int:
        """Ensure frequency is positive."""
        if v <= 0:
            raise ValueError(f"frequency must be positive, got {v}")
        return v

    @model_validator(mode='after')
    def min_less_than_max(self) -> 'DosingConfig':
        """Ensure min_single_dose < max_single_dose."""
        mg = Scale.milli * units.gram
        min_mg = self.min_single_dose.to(mg).quantity
        max_mg = self.max_single_dose.to(mg).quantity
        if min_mg >= max_mg:
            raise ValueError(
                f"min_single_dose ({self.min_single_dose}) must be less than "
                f"max_single_dose ({self.max_single_dose})"
            )
        return self


class InfusionConfig(BaseModel):
    """IV infusion parameters."""

    rate: PositiveNumber[Dimension.volume / Dimension.time]
    duration: PositiveNumber[Dimension.time]

    @property
    def total_volume(self) -> Number:
        """Computed: total infusion volume."""
        return self.rate * self.duration


# ---------------------------------------------------------------------------
# Root settings with computed methods
# ---------------------------------------------------------------------------


class PharmacySettings(BaseModel):
    """Root configuration for pharmaceutical compounding."""

    drug: DrugConfig
    patient: PatientConfig
    dosing: DosingConfig
    infusion: InfusionConfig | None = None

    def calculate_daily_dose(self) -> Number:
        """Calculate total daily dose based on patient weight."""
        return self.dosing.target_dose * self.patient.weight * units.day(1)

    def calculate_single_dose(self) -> Number:
        """Calculate single dose with bounds clamping."""
        daily_dose = self.calculate_daily_dose()
        single_dose = daily_dose / self.dosing.frequency

        # Clamp to bounds
        mg = Scale.milli * units.gram
        dose_mg = single_dose.to(mg).quantity
        min_mg = self.dosing.min_single_dose.to(mg).quantity
        max_mg = self.dosing.max_single_dose.to(mg).quantity

        clamped = max(min_mg, min(max_mg, dose_mg))

        # Preserve uncertainty if present
        return mg(clamped, uncertainty=single_dose.uncertainty)

    def calculate_volume_per_dose(self) -> Number:
        """Calculate volume of drug solution per dose."""
        dose = self.calculate_single_dose()
        return dose / self.drug.concentration

    def calculate_doses_per_vial(self, vial_volume: Number) -> int:
        """Calculate number of doses available from a vial."""
        volume_per_dose = self.calculate_volume_per_dose()
        return int(vial_volume.to(milliliter).quantity /
                   volume_per_dose.to(milliliter).quantity)

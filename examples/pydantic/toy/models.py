# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Vehicle simulation configuration models.

Demonstrates using Number[Dimension] type hints with Pydantic
for dimensionally-validated configuration loading.
"""

from pydantic import BaseModel

from ucon import Dimension
from ucon.pydantic import Number


class VehicleConfig(BaseModel):
    """Vehicle physical properties."""

    mass: Number[Dimension.mass]
    max_speed: Number[Dimension.velocity]
    drag_coefficient: Number[Dimension.ratio]  # dimensionless coefficient
    frontal_area: Number[Dimension.area]


class SimulationConfig(BaseModel):
    """Simulation parameters."""

    time_step: Number[Dimension.time]
    duration: Number[Dimension.time]


class EnvironmentConfig(BaseModel):
    """Environmental conditions."""

    air_density: Number[Dimension.density]
    gravity: Number[Dimension.acceleration]


class Settings(BaseModel):
    """Root configuration model."""

    vehicle: VehicleConfig
    simulation: SimulationConfig
    environment: EnvironmentConfig

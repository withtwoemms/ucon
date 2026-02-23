# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Physics calculations with dimensional validation.

All functions use @enforce_dimensions to catch unit errors at call time.
"""

from ucon import Dimension, Number, enforce_dimensions


@enforce_dimensions
def kinetic_energy(
    mass: Number[Dimension.mass],
    velocity: Number[Dimension.velocity],
) -> Number[Dimension.energy]:
    """Calculate kinetic energy: KE = ½mv²"""
    return mass * velocity ** 2 / 2


@enforce_dimensions
def drag_force(
    density: Number[Dimension.density],
    velocity: Number[Dimension.velocity],
    drag_coeff: Number[Dimension.ratio],
    area: Number[Dimension.area],
) -> Number[Dimension.force]:
    """Calculate aerodynamic drag: F_drag = ½ρv²CdA"""
    return density * velocity ** 2 * drag_coeff * area / 2


@enforce_dimensions
def stopping_distance(
    velocity: Number[Dimension.velocity],
    deceleration: Number[Dimension.acceleration],
) -> Number[Dimension.length]:
    """Calculate stopping distance: d = v² / 2a"""
    return velocity ** 2 / deceleration / 2


@enforce_dimensions
def time_to_stop(
    velocity: Number[Dimension.velocity],
    deceleration: Number[Dimension.acceleration],
) -> Number[Dimension.time]:
    """Calculate time to stop: t = v / a"""
    return velocity / deceleration

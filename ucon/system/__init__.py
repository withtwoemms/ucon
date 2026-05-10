# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.system
===========

System-level value types for ucon.

This subpackage hosts the abstractions that record which units a coherent
unit system uses for each dimension. In v1.8 the only public type is
:class:`BaseUnits`, the renamed predecessor of ``ucon.UnitSystem``. A
richer ``UnitSystem`` value type (which will own a ``BaseUnits`` as its
``base_units`` field) is planned for later phases.
"""

from dataclasses import dataclass
from typing import Dict

from ucon.core import DimensionNotCovered, Unit
from ucon.dimension import Dimension


@dataclass(frozen=True)
class BaseUnits:
    """
    A named mapping from dimensions to base units.

    Represents a coherent unit system like SI or Imperial, where each
    covered dimension has exactly one base unit. Partial systems are
    allowed (Imperial doesn't need mole).

    Parameters
    ----------
    name : str
        The name of the unit system (e.g., "SI", "Imperial").
    bases : dict[Dimension, Unit]
        Mapping from dimensions to their base units.

    Raises
    ------
    ValueError
        If name is empty, bases is empty, or a unit's dimension doesn't
        match its declared dimension key.

    Examples
    --------
    >>> si = BaseUnits(
    ...     name="SI",
    ...     bases={
    ...         LENGTH: meter,
    ...         MASS: kilogram,
    ...         TIME: second,
    ...     }
    ... )
    >>> si.base_for(LENGTH)
    <Unit m>
    """
    name: str
    bases: Dict[Dimension, 'Unit']

    def __post_init__(self):
        if not self.name:
            raise ValueError("BaseUnits must have a name")
        if not self.bases:
            raise ValueError("BaseUnits must have at least one base unit")

        for dim, unit in self.bases.items():
            if unit.dimension != dim:
                raise ValueError(
                    f"Base unit {unit.name} has dimension {unit.dimension.name}, "
                    f"but was declared as base for {dim.name}"
                )

    def base_for(self, dim: Dimension) -> 'Unit':
        """Return the base unit for a dimension.

        Raises
        ------
        DimensionNotCovered
            If this system has no base unit for the dimension.
        """
        if dim not in self.bases:
            raise DimensionNotCovered(
                f"{self.name} has no base unit for {dim.name}"
            )
        return self.bases[dim]

    def covers(self, dim: Dimension) -> bool:
        """Return True if this system has a base unit for the dimension."""
        return dim in self.bases

    @property
    def dimensions(self) -> set:
        """Return the set of dimensions covered by this system."""
        return set(self.bases.keys())

    def __hash__(self):
        # Frozen dataclass with dict field needs custom hash
        return hash((self.name, tuple(sorted(self.bases.items(), key=lambda x: x[0].name))))


__all__ = ['BaseUnits']

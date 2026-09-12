# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Aspects: the discriminator that gates combination below the kind layer.

An *aspect* qualifies a quantity on terms the kind cannot express: two
dose equivalents — same dimension, same unit, same kind — may still be
weighted per different standards, and their sum conforms to neither.
Aspects are tree nodes grouped by family (the tree's root); resolution
is family-wise, and the flat-set model this package shipped through
v2.1.x (which could not distinguish *conflict* from *absence*) is gone.

Design record: ``docs/internal/decisions/008-aspect-stratum.md``.
"""

from ucon.aspects.exceptions import (
    AspectError,
    AspectNotApplicable,
    AspectRefused,
)
from ucon.aspects.forest import AspectForest
from ucon.aspects.types import Aspect, MultPolicy

__all__ = [
    "Aspect",
    "AspectForest",
    "MultPolicy",
    "AspectError",
    "AspectRefused",
    "AspectNotApplicable",
]

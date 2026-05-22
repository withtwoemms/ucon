# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Aspects: provenance and processing tags carried alongside quantities.

An *aspect* is a covariant tag that describes context about a
quantity — that it was reduced from many samples, that it was
calibrated against a reference, that it represents a signal summary,
etc. Aspects are orthogonal to :class:`~ucon.kinds.Kind`: aspects
travel with a quantity through multiplication (per the formula's
:class:`AspectRule` declarations) and through addition (per the
:class:`AspectJoinPolicy` chosen by the caller).

This subpackage provides the data types and the pure join operation.
It does not own any storage on :class:`~ucon.quantity.Number`; aspects
remain caller-side in v1.9.x. v2.0 binds aspects to ``Number``
alongside kinds.

``AspectRule`` shipped from :mod:`ucon.formulas` in v1.9.0; it lives
here in v1.9.1. :mod:`ucon.formulas` continues to re-export the
symbol so that v1.9.0 import paths keep working unchanged.
"""

from ucon.aspects.types import (
    AspectJoinPolicy,
    AspectRule,
    AspectSet,
    join_aspects,
)


__all__ = [
    "AspectSet",
    "AspectRule",
    "AspectJoinPolicy",
    "join_aspects",
]

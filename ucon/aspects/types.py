# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Aspect data types.

An *aspect* is a covariant tag carried alongside a quantity that
describes its provenance, processing, or calibration state rather
than its physical identity. Aspects are orthogonal to kinds: two
quantities sharing a kind can differ in aspects, and two quantities
with different kinds can share aspects.

This module defines the storage type (:data:`AspectSet`), the
behaviour declarations attached to formulas (:class:`AspectRule`),
the policy controlling how aspects combine under lattice join
(:class:`AspectJoinPolicy`), and the pure join operation
(:func:`join_aspects`).

Aspects gained operational semantics in v1.9.1. In v1.9.0
``AspectRule`` shipped from :mod:`ucon.formulas` as an opaque
declaration; it now lives here, with :mod:`ucon.formulas`
re-exporting the symbol for backward compatibility.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


__all__ = [
    "AspectSet",
    "AspectRule",
    "AspectJoinPolicy",
    "join_aspects",
]


#: An immutable set of aspect names carried alongside a quantity.
#:
#: Aspects are strings by convention; ucon does not validate them
#: against a registry. Callers and formulas agree on aspect names
#: out of band.
AspectSet = FrozenSet[str]


class AspectRule(Enum):
    """How a formula treats an operand aspect facet under multiplication.

    ``CONSUME`` drops the operand's aspects on the output (the formula
    transcends the distinction). ``CARRY`` propagates the operand's
    aspects to the output.

    Declared per binding name in
    :attr:`~ucon.formulas.types.KindFormula.aspect_rules`. Bindings not
    mentioned default to ``CARRY``.
    """

    CONSUME = "consume"
    CARRY = "carry"


class AspectJoinPolicy(Enum):
    """How two aspect sets combine when their kinds join at the lattice.

    ``INTERSECT`` keeps only aspects present on both sides — the
    conservative choice, matching the spirit of LCA join (the result
    is less specific than either operand, so unshared aspects cannot
    be honestly attributed to it).

    ``UNION`` keeps every aspect from either side — useful when
    aspects model additive provenance (e.g. "either operand was
    calibrated").
    """

    INTERSECT = "intersect"
    UNION = "union"


def join_aspects(
    a: AspectSet,
    b: AspectSet,
    policy: AspectJoinPolicy = AspectJoinPolicy.INTERSECT,
) -> AspectSet:
    """Combine two aspect sets under the given policy.

    Pure operation. Does not consult a kind lattice; callers compose
    with :meth:`~ucon.kinds.lattice.KindLattice.join` explicitly.

    Parameters
    ----------
    a, b
        Aspect sets to combine.
    policy
        :class:`AspectJoinPolicy` controlling the combination.
        Defaults to ``INTERSECT``.

    Returns
    -------
    AspectSet
        The combined aspect set.

    Raises
    ------
    ValueError
        If ``policy`` is not a recognised :class:`AspectJoinPolicy`.
    """
    if policy is AspectJoinPolicy.INTERSECT:
        return a & b
    if policy is AspectJoinPolicy.UNION:
        return a | b
    raise ValueError(f"unknown AspectJoinPolicy: {policy!r}")

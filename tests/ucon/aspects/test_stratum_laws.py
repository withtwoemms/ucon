# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""The stratum laws as test oracles (A7 of the aspect stratum, #296).

Law 0 — kind-independence: aspect verdicts never read kind values.
The resolvers take no kind parameter, so the law holds by construction;
these tests pin it as a regression oracle by running identical aspect
scenarios across wildly different kind configurations (sensible,
garbage, absent) and asserting byte-identical aspect outcomes.

Law 7 — context-freedom: resolution reads only the operand aspect sets
and the ambient strict bit. Swapping every other context field (kind
lattice, formula registry) must not move any aspect verdict.

Plus the ADR case studies not already pinned by the arithmetic tests:
sample-basis refusal (case 5), coverage-on-unkinded (cases 7a/7b),
n-ary invariance, and the drop-laundering regression.
"""

from __future__ import annotations

import warnings

import pytest

import ucon
from ucon import Aspect, AspectRefused, Number, units
from ucon.aspects import resolve_add_aspects, resolve_mul_aspects
from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import FormulaRegistry
from ucon.kinds import Kind, KindLattice
from ucon.system import use


SPECIFIC_ENERGY_DIM = (LENGTH ** 2) / (TIME ** 2)


def _radsafe():
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"*"}))
    icrp60 = Aspect("icrp60", parent=family)
    icrp103 = Aspect("icrp103", parent=family)
    return family, icrp60, icrp103


def _coverage():
    coverage = Aspect("coverage", applies_to=frozenset({"*"}))
    return coverage, Aspect("k2", parent=coverage)


# ---------- Law 0: the kind-independence oracle ----------

def _aspect_verdict(left_aspects, right_aspects, *, kind):
    """Run one addition with a fixed kind configuration on both sides;
    return the aspect outcome as comparable data."""
    a = Number(2.0, units.gray, kind=kind, aspects=left_aspects)
    b = Number(3.0, units.gray, kind=kind, aspects=right_aspects)
    try:
        return ("ok", frozenset(x.name for x in (a + b).aspects))
    except AspectRefused as exc:
        return ("refused", exc.family.name,
                exc.left.name if exc.left else None,
                exc.right.name if exc.right else None)


def test_law0_verdicts_identical_across_kind_configurations():
    """Mock the kinds to garbage: every aspect verdict is unchanged.

    The kind is held equal on both operands so the kind stratum stays
    inert in every configuration — what varies is the *value* the
    aspect layer would see if it (illegally) peeked.
    """
    _, icrp60, icrp103 = _radsafe()
    kind_configs = [
        None,
        Kind("dose_equivalent", dimension=SPECIFIC_ENERGY_DIM),
        Kind("garbage", dimension=SPECIFIC_ENERGY_DIM),
        Kind("utterly_wrong", dimension=SPECIFIC_ENERGY_DIM,
             aliases=("nonsense",)),
    ]
    scenarios = [
        (frozenset({icrp103}), frozenset({icrp103})),   # equal → carry
        (frozenset({icrp60}), frozenset({icrp103})),    # differ → refuse
        (frozenset({icrp103}), frozenset()),            # partial → refuse
        (frozenset(), frozenset()),                     # silent → silent
    ]
    for left, right in scenarios:
        verdicts = {_aspect_verdict(left, right, kind=kind)
                    for kind in kind_configs}
        assert len(verdicts) == 1, (
            f"aspect verdict varied with kind for {left} + {right}: "
            f"{verdicts}"
        )


def test_law0_resolvers_take_no_kind_parameter():
    """The structural half of the oracle: the resolution functions
    cannot read kinds because no kind reaches them."""
    import inspect
    for fn in (resolve_add_aspects, resolve_mul_aspects):
        params = set(inspect.signature(fn).parameters)
        assert not any("kind" in p for p in params)


# ---------- Law 7: context-freedom beyond the strict bit ----------

def test_law7_kind_lattice_and_formulas_do_not_move_verdicts():
    _, icrp60, icrp103 = _radsafe()
    a = Number(2.0, units.gray, aspects=[icrp103])
    b = Number(3.0, units.gray, aspects=[icrp60])
    c = Number(3.0, units.gray, aspects=[icrp103])

    decoy_lattice = KindLattice([
        Kind("decoy", dimension=SPECIFIC_ENERGY_DIM),
        Kind("noise", dimension=MASS),
    ])
    decoy_formulas = FormulaRegistry()

    contexts = [
        {},
        {"kinds": decoy_lattice},
        {"formulas": decoy_formulas},
        {"kinds": decoy_lattice, "formulas": decoy_formulas},
    ]
    for overrides in contexts:
        with use(ucon.active_system(), strict=True, **overrides):
            with pytest.raises(AspectRefused):
                a + b
            assert (a + c).aspects == frozenset({icrp103})


def test_law7_strict_bit_is_the_only_ambient_input():
    """The one sanctioned ambient read: partial presence flips between
    refuse and inherit on strict alone, everything else fixed."""
    _, _, icrp103 = _radsafe()
    a = Number(2.0, units.gray, aspects=[icrp103])
    b = Number(3.0, units.gray)
    with use(ucon.active_system(), strict=True):
        with pytest.raises(AspectRefused):
            a + b
    with use(ucon.active_system(), strict=False):
        with pytest.warns(UserWarning, match="aspect-silent"):
            assert (a + b).aspects == frozenset({icrp103})


# ---------- ADR case 5: sample basis ----------

def test_case_5_sample_basis_refuses():
    """0.42 dry-basis + 0.35 wet-basis mass fractions: identical
    dimension (none), unit (one), kind — the bases still refuse."""
    ag = Aspect("sample_basis", applies_to=frozenset({"*"}))
    dry = Aspect("dry", parent=ag)
    wet = Aspect("wet", parent=ag)
    mass_fraction = Kind("mass_fraction", dimension=MASS / MASS)
    a = Number(0.42, kind=mass_fraction, aspects=[dry])
    b = Number(0.35, kind=mass_fraction, aspects=[wet])
    with pytest.raises(AspectRefused) as exc_info:
        a + b
    assert exc_info.value.family.name == "sample_basis"


# ---------- ADR cases 7a/7b: coverage on unkinded Numbers ----------

def test_case_7a_equal_coverage_on_unkinded_carries():
    """Aspects need no kind underneath: two unkinded uncertainties at
    the same coverage factor combine and keep it."""
    _, k2 = _coverage()
    a = Number(0.10, units.meter, aspects=[k2])
    b = Number(0.05, units.meter, aspects=[k2])
    total = a + b
    assert total.kind is None
    assert total.aspects == frozenset({k2})


def test_case_7b_partial_coverage_on_unkinded_still_refuses():
    """Strictness does not soften just because nothing is kinded: a
    k2-expanded uncertainty plus a bare number is still a category
    error at the aspect layer."""
    _, k2 = _coverage()
    a = Number(0.10, units.meter, aspects=[k2])
    b = Number(0.05, units.meter)
    with pytest.raises(AspectRefused):
        a + b


# ---------- n-ary invariance ----------

def test_nary_invariance_of_carry():
    """(a+b)+c and a+(b+c) agree, in value and in aspects."""
    _, _, icrp103 = _radsafe()
    a = Number(1.0, units.gray, aspects=[icrp103])
    b = Number(2.0, units.gray, aspects=[icrp103])
    c = Number(3.0, units.gray, aspects=[icrp103])
    left = (a + b) + c
    right = a + (b + c)
    assert left.quantity == right.quantity == 6.0
    assert left.aspects == right.aspects == frozenset({icrp103})


def test_nary_invariance_of_refusal():
    """A refusal fires regardless of association order."""
    _, icrp60, icrp103 = _radsafe()
    a = Number(1.0, units.gray, aspects=[icrp103])
    b = Number(2.0, units.gray, aspects=[icrp103])
    c = Number(3.0, units.gray, aspects=[icrp60])
    with pytest.raises(AspectRefused):
        (a + b) + c
    with pytest.raises(AspectRefused):
        a + (b + c)


def test_nary_invariance_under_multiplication_order():
    """Carry composes: the aspect survives any product ordering."""
    _, _, icrp103 = _radsafe()
    a = Number(2.0, units.gray, aspects=[icrp103])
    t = units.second(3)
    s = units.second(5)
    assert ((a * t) * s).aspects == frozenset({icrp103})
    assert (a * (t * s)).aspects == frozenset({icrp103})


# ---------- drop-laundering regression ----------

def test_no_operation_sequence_launders_an_aspect_away():
    """There is no `drop`: no arithmetic path silently sheds a
    position. Every value-preserving trip keeps the aspect; shedding
    it requires constructing a new Number on purpose."""
    _, _, icrp103 = _radsafe()
    n = Number(2.0, units.gray, aspects=[icrp103])
    trips = [
        n * 1,                          # scalar identity
        n / 1,
        (n * units.second(2)) / units.second(2),   # carry round trip
        n.to(units.gray),               # self-conversion
        n.simplify(),
        n.to_base(),
        (n ** 1),
    ]
    for result in trips:
        assert icrp103 in result.aspects, (
            f"aspect laundered away by {result!r}"
        )


def test_permissive_partial_inherits_rather_than_drops():
    """The permissive escape hatch is inherit-with-warning — the
    position is never quietly discarded from either side."""
    _, _, icrp103 = _radsafe()
    a = Number(2.0, units.gray, aspects=[icrp103])
    b = Number(3.0, units.gray)
    with use(ucon.active_system(), strict=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert (a + b).aspects == frozenset({icrp103})
            assert (b + a).aspects == frozenset({icrp103})

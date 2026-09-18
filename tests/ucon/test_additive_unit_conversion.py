# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for unit normalization in ``Number.__add__`` / ``__sub__``.

Additive operations combine magnitudes, so operands stated in different
units of the same dimension must be rescaled before being combined.
Regression coverage for the defect where they were not: ``1 volt`` minus
``1000 millivolt`` returned ``-999 V`` while ``==`` reported the two
equal.

The invariant these tests pin is agreement between comparison and
arithmetic: whenever ``a == b``, ``(a - b).quantity`` is zero.
"""

from __future__ import annotations

import math

import pytest

from ucon import Number, Scale, units
from ucon.core import UnitFactor, UnitProduct


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def scaled(unit, scale: Scale) -> UnitProduct:
    """A single-factor ``UnitProduct`` for ``unit`` at ``scale``.

    Built directly rather than through the parser so these tests exercise
    the arithmetic and nothing else.
    """
    return UnitProduct({UnitFactor(unit, scale): 1.0})


MILLIVOLT = scaled(units.volt, Scale.milli)
CENTIMETER = scaled(units.meter, Scale.centi)


# ---------------------------------------------------------------------------
# The reported defect
# ---------------------------------------------------------------------------

class TestReportedCases:
    """Every pair from the original report, with its expected value."""

    @pytest.mark.parametrize(
        "left, right, expected_difference, expected_sum",
        [
            (Number(1, units.volt), Number(1000, MILLIVOLT), 0.0, 2.0),
            (Number(1, units.volt), Number(500, MILLIVOLT), 0.5, 1.5),
            (Number(1, units.meter), Number(100, CENTIMETER), 0.0, 2.0),
            (Number(1, units.hour), Number(30, units.minute), 0.5, 1.5),
            (Number(1, units.kilogram), Number(500, units.gram), 0.5, 1.5),
        ],
    )
    def test_operands_are_rescaled_before_combining(
        self, left, right, expected_difference, expected_sum
    ) -> None:
        assert (left - right).quantity == pytest.approx(expected_difference)
        assert (left + right).quantity == pytest.approx(expected_sum)

    def test_result_is_stated_in_the_left_operand_unit(self) -> None:
        result = Number(1, units.volt) - Number(500, MILLIVOLT)
        assert result.unit == units.volt

    def test_subtraction_is_antisymmetric_across_units(self) -> None:
        """``b - a`` is ``-(a - b)`` even when the units differ."""
        a, b = Number(1, units.volt), Number(500, MILLIVOLT)
        assert (a - b).quantity == pytest.approx(0.5)
        assert (b - a).quantity == pytest.approx(-500.0)  # stated in mV


# ---------------------------------------------------------------------------
# The invariant
# ---------------------------------------------------------------------------

class TestComparisonAndArithmeticAgree:
    """``a == b`` implies ``(a - b).quantity == 0``, and conversely."""

    @pytest.mark.parametrize(
        "left, right",
        [
            (Number(1, units.volt), Number(1000, MILLIVOLT)),
            (Number(1, units.meter), Number(100, CENTIMETER)),
            (Number(1, units.hour), Number(60, units.minute)),
            (Number(1, units.kilogram), Number(1000, units.gram)),
            (Number(2.5, units.volt), Number(2500, MILLIVOLT)),
        ],
    )
    def test_equal_operands_difference_to_zero(self, left, right) -> None:
        assert left == right
        assert (left - right).quantity == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "left, right",
        [
            (Number(1, units.volt), Number(500, MILLIVOLT)),
            (Number(1, units.hour), Number(30, units.minute)),
        ],
    )
    def test_unequal_operands_difference_to_nonzero(self, left, right) -> None:
        assert left != right
        assert (left - right).quantity != pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Same-unit arithmetic is untouched
# ---------------------------------------------------------------------------

class TestSameUnitUnchanged:
    """Matched operands behave exactly as before — no rescaling applied."""

    def test_same_unit_addition(self) -> None:
        result = Number(100, units.joule) + Number(200, units.joule)
        assert result.quantity == 300
        assert result.unit == units.joule

    def test_same_unit_subtraction(self) -> None:
        result = Number(200, units.joule) - Number(50, units.joule)
        assert result.quantity == 150

    def test_same_unit_quantity_is_bit_identical(self) -> None:
        """The normalization must not perturb matched-unit magnitudes.

        A float that survives ``* 1.0`` is uninteresting; one that would
        not survive a round-trip through a computed scale factor is the
        point.
        """
        awkward = 0.1 + 0.2  # 0.30000000000000004
        result = Number(awkward, units.volt) + Number(0.0, units.volt)
        assert result.quantity == awkward

    def test_equivalent_but_distinct_unit_objects(self) -> None:
        """Two equal-but-not-identical unit values still take the fast path."""
        left = Number(1.5, scaled(units.volt, Scale.milli))
        right = Number(0.5, scaled(units.volt, Scale.milli))
        assert (left - right).quantity == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Uncertainty rides the same factor
# ---------------------------------------------------------------------------

class TestUncertaintyIsRescaled:
    """Uncertainty is converted with the quantity, not combined raw."""

    def test_uncertainty_converted_before_quadrature(self) -> None:
        # 100 mV ± 10 mV is 0.1 V ± 0.01 V; combined with 1 V ± 0.03 V the
        # result is sqrt(0.03² + 0.01²), not sqrt(0.03² + 10²).
        left = Number(1.0, units.volt, uncertainty=0.03)
        right = Number(100.0, MILLIVOLT, uncertainty=10.0)
        result = left + right

        assert result.quantity == pytest.approx(1.1)
        assert result.uncertainty == pytest.approx(math.hypot(0.03, 0.01))

    def test_subtraction_propagates_the_same_way(self) -> None:
        left = Number(1.0, units.volt, uncertainty=0.03)
        right = Number(100.0, MILLIVOLT, uncertainty=10.0)
        result = left - right

        assert result.quantity == pytest.approx(0.9)
        assert result.uncertainty == pytest.approx(math.hypot(0.03, 0.01))

    def test_absent_uncertainty_stays_absent(self) -> None:
        result = Number(1, units.volt) + Number(500, MILLIVOLT)
        assert result.uncertainty is None

    def test_one_sided_uncertainty_is_rescaled(self) -> None:
        """Only the operand carrying uncertainty contributes, in target units."""
        result = Number(1.0, units.volt) + Number(100.0, MILLIVOLT, uncertainty=10.0)
        assert result.uncertainty == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# Guards that must survive
# ---------------------------------------------------------------------------

class TestDimensionGuardStillApplies:
    """Rescaling is for same-dimension operands only."""

    def test_addition_across_dimensions_still_raises(self) -> None:
        with pytest.raises(TypeError, match="different dimensions"):
            Number(1, units.volt) + Number(1, units.meter)

    def test_subtraction_across_dimensions_still_raises(self) -> None:
        with pytest.raises(TypeError, match="different dimensions"):
            Number(1, units.volt) - Number(1, units.meter)

    def test_non_number_operand_is_not_implemented(self) -> None:
        with pytest.raises(TypeError):
            Number(1, units.volt) + 1


class TestUnitsWithoutBaseForm:
    """Affine and graph-only units normalize to themselves.

    Documents current behavior rather than endorsing it: ``_canonical_magnitude``
    cannot express an offset, so affine scales combine unscaled. The point of
    the assertion is that arithmetic and comparison still *agree* — they are
    consistently wrong here rather than inconsistently.
    """

    def test_affine_operands_agree_with_comparison(self) -> None:
        kelvin_one = Number(1, units.kelvin)
        celsius_one = Number(1, units.celsius)

        # Neither carries a base_form offset, so both normalize to 1.0.
        assert (kelvin_one == celsius_one) is True
        assert (kelvin_one - celsius_one).quantity == pytest.approx(0.0)

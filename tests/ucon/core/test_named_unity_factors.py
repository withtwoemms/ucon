# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""A dimension-one unit that names a quantity survives a product (#318).

``UnitProduct`` dropped every ``Dimension(none)`` factor at construction,
before any arithmetic, keeping its *scale* and discarding the unit. The
question #318 poses is whether a ``Dimension(none)`` unit is semantically
unity — in which case dropping it is right — or a distinguishable symbol that
products must preserve.

It is both, and the discriminator is identity rather than name: the unity folds
into ``canonical_scale``; anything else is a symbol. Keying on *anonymity*
stopped working when #307 named the canonical unity ``one``.
"""

import pytest

from ucon import Number, Unit, units
from ucon.core import Scale, UnitFactor, UnitProduct
from ucon.dimension import NONE
from ucon.kinds.types import Kind


@pytest.fixture
def usd_unit():
    return Unit(name='USD', dimension=NONE)


@pytest.fixture
def mwh():
    return UnitProduct({UnitFactor(units.watt, Scale.mega): 1.0,
                        UnitFactor(units.hour, Scale.one): 1.0})


@pytest.fixture
def usd_per_mwh(usd_unit):
    return UnitProduct({UnitFactor(usd_unit, Scale.one): 1.0,
                        UnitFactor(units.watt, Scale.mega): -1.0,
                        UnitFactor(units.hour, Scale.one): -1.0})


class TestTheSymbolSurvives:
    def test_a_named_dimension_one_factor_is_kept(self, usd_unit):
        p = UnitProduct({UnitFactor(usd_unit, Scale.one): 1.0,
                         UnitFactor(units.hour, Scale.one): -1.0})
        assert 'USD' in [fu.name for fu in p.factors]
        assert 'USD/h' in str(p)

    def test_a_rate_unit_is_now_expressible(self, usd_per_mwh):
        """``USD/kWh`` rendered as ``1/(kW·h)`` and lost the money entirely."""
        assert 'USD' in [fu.name for fu in usd_per_mwh.factors]
        assert 'USD' in str(usd_per_mwh)

    def test_a_bare_named_dimensionless_unit_renders(self, usd_unit):
        """``Unit.shorthand`` blanked every ``Dimension(none)`` unit.

        A one-factor ``UnitProduct`` of the same unit rendered it, so the two
        spellings disagreed about whether the money was visible.
        """
        assert usd_unit.shorthand == 'USD'
        assert 'USD' in str(Number(100.0, usd_unit))


class TestTheUnityStillFolds:
    @pytest.mark.parametrize('unity', ['one', 'none'])
    def test_multiplying_by_the_unity_is_identity(self, unity):
        u = getattr(units, unity)
        p = UnitProduct({UnitFactor(u, Scale.one): 1.0,
                         UnitFactor(units.kilogram, Scale.one): 1.0})
        assert [fu.name for fu in p.factors] == ['kilogram']

    def test_the_unity_renders_as_nothing(self):
        assert units.one.shorthand == ''
        assert units.none.shorthand == ''

    def test_a_scaled_unity_folds_into_canonical_scale(self):
        p = UnitProduct({UnitFactor(units.none, Scale.centi): 1.0,
                         UnitFactor(units.hour, Scale.one): -1.0})
        assert p.factors.keys() == {UnitFactor(units.hour, Scale.one)}
        assert p.canonical_scale == pytest.approx(0.01)


class TestMagnitudeIsPreserved:
    def test_a_scaled_symbol_keeps_its_scale_on_the_factor(self, usd_unit):
        """The corruption #318 names: the scale survived without its unit.

        Now the scale rides on the surviving factor instead of being absorbed,
        and the magnitude is unchanged either way.
        """
        p = UnitProduct({UnitFactor(usd_unit, Scale.centi): 1.0,
                         UnitFactor(units.hour, Scale.one): -1.0})
        assert p.canonical_scale == pytest.approx(1.0)
        assert p.fold_scale() == pytest.approx(0.01)
        assert Number(100, p).canonical_magnitude == pytest.approx(100 * 0.01 / 3600)


class TestTheAdrElevenPattern:
    """The money-rate pattern ADR 011 reserves for fee schedules.

    #318 recorded that a rate unit "cannot be constructed, cannot be kinded,
    and cannot carry its declaration", so the pattern could not be written at
    all. The first two are now false; this is the worked example from ADR 013
    section 4.
    """

    def test_a_tariff_resolves_to_money(self, mwh, usd_per_mwh):
        from ucon._active import _active

        usd = Kind(name='usd_t', dimension=NONE)
        energy_q = Kind(name='energy_q_t', dimension=mwh.dimension)
        rate = Kind(name='usd_per_energy_t', dimension=usd_per_mwh.dimension)

        from ucon.formulas import KindFormula
        _active.get().formulas.register(KindFormula(
            name='tariff_t', expression='E * p',
            input_kinds={'E': energy_q, 'p': rate}, output_kind=usd,
        ))

        energy = Number(500.0, mwh, kind=energy_q)
        price = Number(48.0, usd_per_mwh, kind=rate)

        for product in (energy * price, price * energy):
            assert product.quantity == pytest.approx(24000.0)
            assert product.kind.name == 'usd_t'
            assert 'USD' in str(product)

    def test_the_rate_unit_can_carry_a_kind(self, usd_per_mwh):
        """Previously ``KindDimensionMismatch``: a ``Dimension(none)`` money
        kind could not refine ``1/(kW·h)``, because that is what the rate had
        been reduced to."""
        rate = Kind(name='usd_per_energy_k', dimension=usd_per_mwh.dimension)
        value = Number(48.0, usd_per_mwh, kind=rate)
        assert value.kind.name == 'usd_per_energy_k'

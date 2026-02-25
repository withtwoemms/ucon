# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for logarithmic units (v0.9.1).

Tests LogMap reference parameter, logarithmic unit definitions,
and conversions involving logarithmic units like dBm, dBW, dBV, dBSPL, and pH.
"""

import math
import pytest

from ucon import units
from ucon.maps import LogMap, ExpMap


class TestLogMapReference:
    """Test LogMap with reference parameter."""

    def test_default_reference_is_one(self):
        m = LogMap(scale=10, base=10)
        assert m.reference == 1.0

    def test_reference_affects_output(self):
        # Without reference: 10 * log10(1) = 0
        m1 = LogMap(scale=10, base=10)
        assert m1(1.0) == 0.0

        # With reference=0.001: 10 * log10(1/0.001) = 10 * log10(1000) = 30
        m2 = LogMap(scale=10, base=10, reference=0.001)
        assert m2(1.0) == pytest.approx(30.0)

    def test_inverse_preserves_reference(self):
        m = LogMap(scale=10, base=10, reference=0.001)
        inv = m.inverse()
        assert inv.reference == 0.001
        # Round-trip
        assert inv(m(0.5)) == pytest.approx(0.5)

    def test_dbm_conversion_values(self):
        """dBm: 0 dBm = 1 mW, 30 dBm = 1 W"""
        m = LogMap(scale=10, base=10, reference=1e-3)
        assert m(1e-3) == pytest.approx(0.0)   # 1 mW -> 0 dBm
        assert m(1.0) == pytest.approx(30.0)   # 1 W -> 30 dBm
        assert m(1e-6) == pytest.approx(-30.0) # 1 uW -> -30 dBm

    def test_dbw_conversion_values(self):
        """dBW: 0 dBW = 1 W"""
        m = LogMap(scale=10, base=10, reference=1.0)
        assert m(1.0) == pytest.approx(0.0)    # 1 W -> 0 dBW
        assert m(1000.0) == pytest.approx(30.0)  # 1 kW -> 30 dBW
        assert m(0.001) == pytest.approx(-30.0)  # 1 mW -> -30 dBW

    def test_dbv_conversion_values(self):
        """dBV: 20 * log10(V/1V) for amplitude"""
        m = LogMap(scale=20, base=10, reference=1.0)
        assert m(1.0) == pytest.approx(0.0)    # 1 V -> 0 dBV
        assert m(10.0) == pytest.approx(20.0)  # 10 V -> 20 dBV
        assert m(0.1) == pytest.approx(-20.0)  # 0.1 V -> -20 dBV

    def test_dbspl_conversion_values(self):
        """dBSPL: 20 * log10(P/20uPa), reference = 20e-6 Pa"""
        m = LogMap(scale=20, base=10, reference=20e-6)
        assert m(20e-6) == pytest.approx(0.0)  # 20 uPa -> 0 dBSPL
        assert m(1.0) == pytest.approx(93.98, abs=0.01)  # 1 Pa ~ 94 dBSPL

    def test_ph_conversion_values(self):
        """pH: -log10([H+]/1 mol/L)"""
        m = LogMap(scale=-1, base=10, reference=1.0)
        assert m(1e-7) == pytest.approx(7.0)   # 1e-7 mol/L -> pH 7
        assert m(1e-4) == pytest.approx(4.0)   # 1e-4 mol/L -> pH 4
        assert m(1e-14) == pytest.approx(14.0) # 1e-14 mol/L -> pH 14

    def test_neper_with_reference(self):
        """Neper: ln(x/ref)"""
        m = LogMap(scale=1, base=math.e, reference=1.0)
        assert m(math.e) == pytest.approx(1.0)
        assert m(math.e ** 2) == pytest.approx(2.0)


class TestExpMapReference:
    """Test ExpMap with reference parameter."""

    def test_default_reference_is_one(self):
        m = ExpMap(scale=1, base=10)
        assert m.reference == 1.0

    def test_reference_affects_output(self):
        # With reference=0.001: 0.001 * 10^(0.1 * 30) = 0.001 * 1000 = 1.0
        m = ExpMap(scale=0.1, base=10, reference=0.001)
        assert m(30.0) == pytest.approx(1.0)  # 30 dBm -> 1 W

    def test_inverse_preserves_reference(self):
        m = ExpMap(scale=0.1, base=10, reference=0.001)
        inv = m.inverse()
        assert inv.reference == 0.001
        # Round-trip
        assert m(inv(0.5)) == pytest.approx(0.5)

    def test_dbm_to_watts(self):
        """Convert dBm values back to watts"""
        # ExpMap for dBm -> W: reference * 10^(scale * x)
        # We want W = 1e-3 * 10^(x/10)
        m = ExpMap(scale=0.1, base=10, reference=1e-3)
        assert m(0.0) == pytest.approx(1e-3)   # 0 dBm -> 1 mW
        assert m(30.0) == pytest.approx(1.0)   # 30 dBm -> 1 W
        assert m(-30.0) == pytest.approx(1e-6) # -30 dBm -> 1 uW


class TestLogarithmicUnits:
    """Test logarithmic unit definitions."""

    def test_decibel_exists(self):
        assert units.decibel.name == 'decibel'
        assert 'dB' in units.decibel.aliases

    def test_bel_exists(self):
        assert units.bel.name == 'bel'
        # Note: 'B' alias omitted to avoid conflict with byte ('B')

    def test_neper_exists(self):
        assert units.neper.name == 'neper'
        assert 'Np' in units.neper.aliases

    def test_dbm_exists(self):
        assert units.decibel_milliwatt.name == 'decibel_milliwatt'
        assert 'dBm' in units.decibel_milliwatt.aliases

    def test_dbw_exists(self):
        assert units.decibel_watt.name == 'decibel_watt'
        assert 'dBW' in units.decibel_watt.aliases

    def test_dbv_exists(self):
        assert units.decibel_volt.name == 'decibel_volt'
        assert 'dBV' in units.decibel_volt.aliases

    def test_dbspl_exists(self):
        assert units.decibel_spl.name == 'decibel_spl'
        assert 'dBSPL' in units.decibel_spl.aliases

    def test_pH_exists(self):
        assert units.pH.name == 'pH'


class TestLogarithmicConversions:
    """Test conversions involving logarithmic units."""

    def test_watt_to_dbm(self):
        """1 W = 30 dBm"""
        power = units.watt(1.0)
        dbm = power.to(units.decibel_milliwatt)
        assert dbm.quantity == pytest.approx(30.0)

    def test_dbm_to_watt(self):
        """0 dBm = 1 mW"""
        dbm = units.decibel_milliwatt(0.0)
        power = dbm.to(units.watt)
        assert power.quantity == pytest.approx(1e-3)

    def test_milliwatt_to_dbm_via_watt(self):
        """1 mW = 0 dBm (via watt conversion)"""
        from ucon.core import Scale
        # milliwatt = gram with milli scale, but we need to use watt with milli scale
        milliwatt = units.watt(1e-3)  # 1 mW as 0.001 W
        dbm = milliwatt.to(units.decibel_milliwatt)
        assert dbm.quantity == pytest.approx(0.0)

    def test_watt_to_dbw(self):
        """1 W = 0 dBW"""
        power = units.watt(1.0)
        dbw = power.to(units.decibel_watt)
        assert dbw.quantity == pytest.approx(0.0)

    def test_dbw_to_watt(self):
        """10 dBW = 10 W"""
        dbw = units.decibel_watt(10.0)
        power = dbw.to(units.watt)
        assert power.quantity == pytest.approx(10.0)

    def test_volt_to_dbv(self):
        """1 V = 0 dBV"""
        voltage = units.volt(1.0)
        dbv = voltage.to(units.decibel_volt)
        assert dbv.quantity == pytest.approx(0.0)

    def test_dbv_to_volt(self):
        """20 dBV = 10 V"""
        dbv = units.decibel_volt(20.0)
        voltage = dbv.to(units.volt)
        assert voltage.quantity == pytest.approx(10.0)

    def test_pascal_to_dbspl(self):
        """20 uPa = 0 dBSPL"""
        pressure = units.pascal(20e-6)
        dbspl = pressure.to(units.decibel_spl)
        assert dbspl.quantity == pytest.approx(0.0)

    def test_dbspl_to_pascal(self):
        """94 dBSPL ~ 1 Pa"""
        # 20 * log10(1/20e-6) = 20 * log10(50000) ~ 93.98
        dbspl = units.decibel_spl(93.9794)
        pressure = dbspl.to(units.pascal)
        assert pressure.quantity == pytest.approx(1.0, abs=0.01)

    def test_ratio_to_bel(self):
        """ratio 10 = 1 B"""
        ratio = units.fraction(10.0)
        bel = ratio.to(units.bel)
        assert bel.quantity == pytest.approx(1.0)

    def test_ratio_to_decibel(self):
        """ratio 10 = 10 dB"""
        ratio = units.fraction(10.0)
        db = ratio.to(units.decibel)
        assert db.quantity == pytest.approx(10.0)

    def test_bel_to_decibel(self):
        """1 B = 10 dB"""
        bel = units.bel(1.0)
        db = bel.to(units.decibel)
        assert db.quantity == pytest.approx(10.0)

    def test_ratio_to_neper(self):
        """ratio e = 1 Np"""
        ratio = units.fraction(math.e)
        np = ratio.to(units.neper)
        assert np.quantity == pytest.approx(1.0)


class TestpHConversions:
    """Test pH conversions.

    pH has concentration dimension (amount_of_substance/volume), consistent with
    how dBm has POWER dimension. This enables direct mol/L <-> pH conversions.
    """

    def test_ph_unit_can_be_created(self):
        """pH unit can be instantiated directly"""
        ph = units.pH(7.0)
        assert ph.quantity == 7.0
        assert ph.unit == units.pH

    def test_concentration_to_ph(self):
        """1e-7 mol/L = pH 7 (neutral)"""
        conc = (units.mole / units.liter)(1e-7)
        ph = conc.to(units.pH)
        assert ph.quantity == pytest.approx(7.0)

    def test_ph_to_concentration(self):
        """pH 7 = 1e-7 mol/L"""
        ph = units.pH(7.0)
        conc = ph.to(units.mole / units.liter)
        assert conc.quantity == pytest.approx(1e-7)

    def test_acidic_concentration_to_ph(self):
        """1e-3 mol/L = pH 3 (acidic)"""
        conc = (units.mole / units.liter)(1e-3)
        ph = conc.to(units.pH)
        assert ph.quantity == pytest.approx(3.0)

    def test_basic_concentration_to_ph(self):
        """1e-11 mol/L = pH 11 (basic)"""
        conc = (units.mole / units.liter)(1e-11)
        ph = conc.to(units.pH)
        assert ph.quantity == pytest.approx(11.0)

    def test_ph_roundtrip(self):
        """mol/L -> pH -> mol/L should preserve value"""
        original = (units.mole / units.liter)(3.16e-5)
        ph = original.to(units.pH)
        back = ph.to(units.mole / units.liter)
        assert back.quantity == pytest.approx(3.16e-5, rel=1e-6)


class TestLogarithmicRoundTrips:
    """Test round-trip conversions through logarithmic maps."""

    def test_watt_dbm_roundtrip(self):
        """W -> dBm -> W should preserve value"""
        original = units.watt(0.5)
        dbm = original.to(units.decibel_milliwatt)
        back = dbm.to(units.watt)
        assert back.quantity == pytest.approx(0.5)

    def test_volt_dbv_roundtrip(self):
        """V -> dBV -> V should preserve value"""
        original = units.volt(3.5)
        dbv = original.to(units.decibel_volt)
        back = dbv.to(units.volt)
        assert back.quantity == pytest.approx(3.5)

    def test_pascal_dbspl_roundtrip(self):
        """Pa -> dBSPL -> Pa should preserve value"""
        original = units.pascal(0.1)
        dbspl = original.to(units.decibel_spl)
        back = dbspl.to(units.pascal)
        assert back.quantity == pytest.approx(0.1)

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the default ConversionGraph with temperature, pressure, and base SI conversions.

These tests verify that Number.to() works correctly with the default graph for:
- Temperature conversions (Celsius, Kelvin, Fahrenheit) using AffineMap
- Pressure conversions (Pascal, Bar, PSI, Atmosphere)
- Base SI conversions (length, mass, time, volume, energy, power, information)
"""

import unittest

from ucon import units
from ucon.graph import get_default_graph, reset_default_graph


class TestTemperatureConversions(unittest.TestCase):
    """Tests for temperature conversions using AffineMap in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_celsius_to_kelvin_freezing(self):
        """0°C = 273.15 K"""
        result = units.celsius(0).to(units.kelvin)
        self.assertAlmostEqual(result.quantity, 273.15, places=2)

    def test_celsius_to_kelvin_boiling(self):
        """100°C = 373.15 K"""
        result = units.celsius(100).to(units.kelvin)
        self.assertAlmostEqual(result.quantity, 373.15, places=2)

    def test_kelvin_to_celsius_absolute_zero(self):
        """0 K = -273.15°C"""
        result = units.kelvin(0).to(units.celsius)
        self.assertAlmostEqual(result.quantity, -273.15, places=2)

    def test_kelvin_to_celsius_room_temp(self):
        """293.15 K = 20°C"""
        result = units.kelvin(293.15).to(units.celsius)
        self.assertAlmostEqual(result.quantity, 20, places=1)

    def test_fahrenheit_to_celsius_freezing(self):
        """32°F = 0°C"""
        result = units.fahrenheit(32).to(units.celsius)
        self.assertAlmostEqual(result.quantity, 0, places=1)

    def test_fahrenheit_to_celsius_boiling(self):
        """212°F = 100°C"""
        result = units.fahrenheit(212).to(units.celsius)
        self.assertAlmostEqual(result.quantity, 100, places=1)

    def test_celsius_to_fahrenheit_freezing(self):
        """0°C = 32°F"""
        result = units.celsius(0).to(units.fahrenheit)
        self.assertAlmostEqual(result.quantity, 32, places=1)

    def test_celsius_to_fahrenheit_boiling(self):
        """100°C = 212°F"""
        result = units.celsius(100).to(units.fahrenheit)
        self.assertAlmostEqual(result.quantity, 212, places=1)

    def test_fahrenheit_to_kelvin_absolute_zero(self):
        """-459.67°F = 0 K (approximately)"""
        result = units.fahrenheit(-459.67).to(units.kelvin)
        self.assertAlmostEqual(result.quantity, 0, places=0)

    def test_kelvin_to_fahrenheit_boiling(self):
        """373.15 K = 212°F"""
        result = units.kelvin(373.15).to(units.fahrenheit)
        self.assertAlmostEqual(result.quantity, 212, places=0)

    def test_temperature_round_trip_celsius(self):
        """Round-trip: C → K → C"""
        original = 25.0
        via_kelvin = units.celsius(original).to(units.kelvin)
        back = via_kelvin.to(units.celsius)
        self.assertAlmostEqual(back.quantity, original, places=10)

    def test_temperature_round_trip_fahrenheit(self):
        """Round-trip: F → C → F"""
        original = 98.6  # body temperature
        via_celsius = units.fahrenheit(original).to(units.celsius)
        back = via_celsius.to(units.fahrenheit)
        self.assertAlmostEqual(back.quantity, original, places=10)


class TestPressureConversions(unittest.TestCase):
    """Tests for pressure conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_pascal_to_bar(self):
        """100000 Pa = 1 bar"""
        result = units.pascal(100000).to(units.bar)
        self.assertAlmostEqual(result.quantity, 1.0, places=5)

    def test_bar_to_pascal(self):
        """1 bar = 100000 Pa"""
        result = units.bar(1).to(units.pascal)
        self.assertAlmostEqual(result.quantity, 100000, places=0)

    def test_pascal_to_psi(self):
        """6894.76 Pa ≈ 1 psi"""
        result = units.pascal(6894.76).to(units.psi)
        self.assertAlmostEqual(result.quantity, 1.0, places=2)

    def test_psi_to_pascal(self):
        """1 psi ≈ 6894.76 Pa"""
        result = units.psi(1).to(units.pascal)
        self.assertAlmostEqual(result.quantity, 6894.76, places=0)

    def test_atmosphere_to_pascal(self):
        """1 atm = 101325 Pa"""
        result = units.atmosphere(1).to(units.pascal)
        self.assertAlmostEqual(result.quantity, 101325, places=0)

    def test_pascal_to_atmosphere(self):
        """101325 Pa = 1 atm"""
        result = units.pascal(101325).to(units.atmosphere)
        self.assertAlmostEqual(result.quantity, 1.0, places=5)

    def test_atmosphere_to_bar(self):
        """1 atm ≈ 1.01325 bar"""
        result = units.atmosphere(1).to(units.bar)
        self.assertAlmostEqual(result.quantity, 1.01325, places=4)

    def test_bar_to_atmosphere(self):
        """1 bar ≈ 0.986923 atm"""
        result = units.bar(1).to(units.atmosphere)
        self.assertAlmostEqual(result.quantity, 0.986923, places=4)

    def test_atmosphere_to_psi(self):
        """1 atm ≈ 14.696 psi"""
        result = units.atmosphere(1).to(units.psi)
        self.assertAlmostEqual(result.quantity, 14.696, places=2)

    def test_psi_to_atmosphere(self):
        """14.696 psi ≈ 1 atm"""
        result = units.psi(14.696).to(units.atmosphere)
        self.assertAlmostEqual(result.quantity, 1.0, places=2)

    def test_pressure_round_trip(self):
        """Round-trip: Pa → bar → Pa"""
        original = 250000
        via_bar = units.pascal(original).to(units.bar)
        back = via_bar.to(units.pascal)
        self.assertAlmostEqual(back.quantity, original, places=5)


class TestBaseSILengthConversions(unittest.TestCase):
    """Tests for length conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_meter_to_foot(self):
        """1 m ≈ 3.28084 ft"""
        result = units.meter(1).to(units.foot)
        self.assertAlmostEqual(result.quantity, 3.28084, places=4)

    def test_foot_to_meter(self):
        """1 ft ≈ 0.3048 m"""
        result = units.foot(1).to(units.meter)
        self.assertAlmostEqual(result.quantity, 0.3048, places=4)

    def test_foot_to_inch(self):
        """1 ft = 12 in"""
        result = units.foot(1).to(units.inch)
        self.assertAlmostEqual(result.quantity, 12, places=10)

    def test_inch_to_foot(self):
        """12 in = 1 ft"""
        result = units.inch(12).to(units.foot)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_meter_to_inch(self):
        """1 m ≈ 39.37 in (via foot)"""
        result = units.meter(1).to(units.inch)
        self.assertAlmostEqual(result.quantity, 39.37, places=1)

    def test_foot_to_yard(self):
        """3 ft = 1 yd"""
        result = units.foot(3).to(units.yard)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_yard_to_foot(self):
        """1 yd = 3 ft"""
        result = units.yard(1).to(units.foot)
        self.assertAlmostEqual(result.quantity, 3.0, places=10)

    def test_mile_to_foot(self):
        """1 mi = 5280 ft"""
        result = units.mile(1).to(units.foot)
        self.assertAlmostEqual(result.quantity, 5280, places=0)

    def test_foot_to_mile(self):
        """5280 ft = 1 mi"""
        result = units.foot(5280).to(units.mile)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_meter_to_mile(self):
        """1609.34 m ≈ 1 mi (multi-hop: m → ft → mi)"""
        result = units.meter(1609.34).to(units.mile)
        self.assertAlmostEqual(result.quantity, 1.0, places=2)

    def test_meter_to_yard(self):
        """1 m ≈ 1.094 yd (multi-hop: m → ft → yd)"""
        result = units.meter(1).to(units.yard)
        self.assertAlmostEqual(result.quantity, 1.094, places=2)


class TestBaseSIMassConversions(unittest.TestCase):
    """Tests for mass conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_kilogram_to_gram(self):
        """1 kg = 1000 g"""
        result = units.kilogram(1).to(units.gram)
        self.assertAlmostEqual(result.quantity, 1000, places=10)

    def test_gram_to_kilogram(self):
        """1000 g = 1 kg"""
        result = units.gram(1000).to(units.kilogram)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_kilogram_to_pound(self):
        """1 kg ≈ 2.20462 lb"""
        result = units.kilogram(1).to(units.pound)
        self.assertAlmostEqual(result.quantity, 2.20462, places=4)

    def test_pound_to_kilogram(self):
        """1 lb ≈ 0.453592 kg"""
        result = units.pound(1).to(units.kilogram)
        self.assertAlmostEqual(result.quantity, 0.453592, places=4)

    def test_pound_to_ounce(self):
        """1 lb = 16 oz"""
        result = units.pound(1).to(units.ounce)
        self.assertAlmostEqual(result.quantity, 16, places=10)

    def test_ounce_to_pound(self):
        """16 oz = 1 lb"""
        result = units.ounce(16).to(units.pound)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_gram_to_pound(self):
        """453.592 g ≈ 1 lb (via kg)"""
        result = units.gram(453.592).to(units.pound)
        self.assertAlmostEqual(result.quantity, 1.0, places=2)

    def test_kilogram_to_ounce(self):
        """1 kg ≈ 35.274 oz (multi-hop: kg → lb → oz)"""
        result = units.kilogram(1).to(units.ounce)
        self.assertAlmostEqual(result.quantity, 35.274, places=1)


class TestBaseSITimeConversions(unittest.TestCase):
    """Tests for time conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_second_to_minute(self):
        """60 s = 1 min"""
        result = units.second(60).to(units.minute)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_minute_to_second(self):
        """1 min = 60 s"""
        result = units.minute(1).to(units.second)
        self.assertAlmostEqual(result.quantity, 60, places=10)

    def test_minute_to_hour(self):
        """60 min = 1 hr"""
        result = units.minute(60).to(units.hour)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_hour_to_minute(self):
        """1 hr = 60 min"""
        result = units.hour(1).to(units.minute)
        self.assertAlmostEqual(result.quantity, 60, places=10)

    def test_hour_to_day(self):
        """24 hr = 1 day"""
        result = units.hour(24).to(units.day)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_day_to_hour(self):
        """1 day = 24 hr"""
        result = units.day(1).to(units.hour)
        self.assertAlmostEqual(result.quantity, 24, places=10)

    def test_second_to_hour(self):
        """3600 s = 1 hr (multi-hop: s → min → hr)"""
        result = units.second(3600).to(units.hour)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_second_to_day(self):
        """86400 s = 1 day (multi-hop: s → min → hr → day)"""
        result = units.second(86400).to(units.day)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_day_to_second(self):
        """1 day = 86400 s"""
        result = units.day(1).to(units.second)
        self.assertAlmostEqual(result.quantity, 86400, places=0)


class TestBaseSIVolumeConversions(unittest.TestCase):
    """Tests for volume conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_liter_to_gallon(self):
        """1 L ≈ 0.264172 gal"""
        result = units.liter(1).to(units.gallon)
        self.assertAlmostEqual(result.quantity, 0.264172, places=5)

    def test_gallon_to_liter(self):
        """1 gal ≈ 3.78541 L"""
        result = units.gallon(1).to(units.liter)
        self.assertAlmostEqual(result.quantity, 3.78541, places=3)


class TestBaseSIEnergyConversions(unittest.TestCase):
    """Tests for energy conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_joule_to_calorie(self):
        """4.184 J = 1 cal"""
        result = units.joule(4.184).to(units.calorie)
        self.assertAlmostEqual(result.quantity, 1.0, places=3)

    def test_calorie_to_joule(self):
        """1 cal = 4.184 J"""
        result = units.calorie(1).to(units.joule)
        self.assertAlmostEqual(result.quantity, 4.184, places=3)

    def test_joule_to_btu(self):
        """1055.06 J ≈ 1 BTU"""
        result = units.joule(1055.06).to(units.btu)
        self.assertAlmostEqual(result.quantity, 1.0, places=2)

    def test_btu_to_joule(self):
        """1 BTU ≈ 1055.06 J"""
        result = units.btu(1).to(units.joule)
        self.assertAlmostEqual(result.quantity, 1055.06, places=0)

    def test_calorie_to_btu(self):
        """252 cal ≈ 1 BTU (multi-hop via joule)"""
        result = units.calorie(252).to(units.btu)
        self.assertAlmostEqual(result.quantity, 1.0, places=1)


class TestBaseSIPowerConversions(unittest.TestCase):
    """Tests for power conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_watt_to_horsepower(self):
        """745.7 W ≈ 1 hp"""
        result = units.watt(745.7).to(units.horsepower)
        self.assertAlmostEqual(result.quantity, 1.0, places=2)

    def test_horsepower_to_watt(self):
        """1 hp ≈ 745.7 W"""
        result = units.horsepower(1).to(units.watt)
        self.assertAlmostEqual(result.quantity, 745.7, places=0)


class TestInformationConversions(unittest.TestCase):
    """Tests for information unit conversions in the default graph."""

    def setUp(self):
        reset_default_graph()

    def test_byte_to_bit(self):
        """1 B = 8 b"""
        result = units.byte(1).to(units.bit)
        self.assertAlmostEqual(result.quantity, 8, places=10)

    def test_bit_to_byte(self):
        """8 b = 1 B"""
        result = units.bit(8).to(units.byte)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_kilobyte_to_bit(self):
        """1 KB = 8000 b (using Scale.kilo)"""
        from ucon.core import Scale
        kilobyte = Scale.kilo * units.byte
        result = kilobyte(1).to(units.bit)
        self.assertAlmostEqual(result.quantity, 8000, places=0)


class TestConversionRoundTrips(unittest.TestCase):
    """Tests verifying round-trip conversion accuracy."""

    def setUp(self):
        reset_default_graph()

    def test_length_round_trip(self):
        """meter → foot → meter"""
        original = 42.5
        via_foot = units.meter(original).to(units.foot)
        back = via_foot.to(units.meter)
        self.assertAlmostEqual(back.quantity, original, places=8)

    def test_mass_round_trip(self):
        """kilogram → pound → kilogram"""
        original = 75.0
        via_pound = units.kilogram(original).to(units.pound)
        back = via_pound.to(units.kilogram)
        self.assertAlmostEqual(back.quantity, original, places=8)

    def test_time_round_trip(self):
        """second → day → second"""
        original = 172800  # 2 days
        via_day = units.second(original).to(units.day)
        back = via_day.to(units.second)
        self.assertAlmostEqual(back.quantity, original, places=5)

    def test_pressure_multi_hop_round_trip(self):
        """pascal → atmosphere → bar → pascal"""
        original = 500000
        via_atm = units.pascal(original).to(units.atmosphere)
        via_bar = via_atm.to(units.bar)
        back = via_bar.to(units.pascal)
        self.assertAlmostEqual(back.quantity, original, places=2)


if __name__ == '__main__':
    unittest.main()

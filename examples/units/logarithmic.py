#!/usr/bin/env python3
# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Logarithmic Unit Conversions

Demonstrates ucon's logarithmic unit support for:
- Power ratios: decibel (dB), bel (B), neper (Np)
- Absolute power: dBm (ref 1 mW), dBW (ref 1 W)
- Voltage: dBV (ref 1 V)
- Acoustics: dBSPL (ref 20 µPa)
- Chemistry: pH (-log10 of H+ concentration)
- SRE: nines notation for availability

Usage:
    python logarithmic.py
"""

from ucon import units


def section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_ratio_conversions():
    """Basic ratio to logarithmic conversions."""
    section("Ratio Conversions (dimensionless)")

    # Decibels for power ratios: dB = 10 * log10(ratio)
    print("Power ratios to decibels:")
    for ratio in [1, 2, 10, 100, 1000]:
        r = units.fraction(ratio)
        db = r.to(units.decibel)
        print(f"  ratio {ratio:4} = {db.quantity:6.2f} dB")

    print()

    # Nepers use natural logarithm: Np = ln(ratio)
    print("Amplitude ratios to nepers:")
    import math
    for ratio in [1, math.e, math.e**2, 10]:
        r = units.fraction(ratio)
        np = r.to(units.neper)
        print(f"  ratio {ratio:6.3f} = {np.quantity:5.2f} Np")

    print()

    # Bel to decibel
    print("Bel to decibel conversion:")
    bel = units.bel(2.0)
    db = bel.to(units.decibel)
    print(f"  {bel} = {db}")


def demo_power_dbm():
    """Power in dBm (decibel-milliwatts)."""
    section("Power: Watts to dBm")

    # dBm is relative to 1 milliwatt
    # dBm = 10 * log10(P / 1mW)
    print("Common power levels in dBm:")

    power_levels = [
        (1e-6, "1 µW (weak signal)"),
        (1e-3, "1 mW (0 dBm reference)"),
        (0.1, "100 mW (WiFi router)"),
        (1.0, "1 W (30 dBm)"),
        (100.0, "100 W (FM broadcast)"),
    ]

    for watts, description in power_levels:
        p = units.watt(watts)
        dbm = p.to(units.decibel_milliwatt)
        print(f"  {p.quantity:8.0e} W = {dbm.quantity:7.1f} dBm  ({description})")

    print()

    # Inverse: dBm to watts
    print("Converting dBm back to watts:")
    for dbm_val in [-30, 0, 10, 20, 30]:
        dbm = units.decibel_milliwatt(dbm_val)
        watts = dbm.to(units.watt)
        print(f"  {dbm_val:4} dBm = {watts.quantity:.2e} W")


def demo_power_dbw():
    """Power in dBW (decibel-watts)."""
    section("Power: Watts to dBW")

    # dBW is relative to 1 watt
    # dBW = 10 * log10(P / 1W)
    # dBW = dBm - 30
    print("dBW vs dBm comparison:")

    for watts in [0.001, 0.1, 1.0, 10.0, 1000.0]:
        p = units.watt(watts)
        dbw = p.to(units.decibel_watt)
        dbm = p.to(units.decibel_milliwatt)
        print(f"  {watts:7.3f} W = {dbw.quantity:6.1f} dBW = {dbm.quantity:6.1f} dBm")


def demo_voltage_dbv():
    """Voltage in dBV (decibel-volts)."""
    section("Voltage: Volts to dBV")

    # dBV uses 20*log10 (amplitude, not power)
    # dBV = 20 * log10(V / 1V)
    print("Voltage levels in dBV:")
    print("(Note: 20*log10 scale for amplitude quantities)")
    print()

    voltages = [
        (0.001, "1 mV"),
        (0.1, "100 mV"),
        (1.0, "1 V (0 dBV reference)"),
        (10.0, "10 V"),
    ]

    for volts, label in voltages:
        v = units.volt(volts)
        dbv = v.to(units.decibel_volt)
        print(f"  {label:10} = {dbv.quantity:6.1f} dBV")

    print()

    # Round-trip demonstration
    print("Round-trip verification:")
    original = units.volt(3.5)
    dbv = original.to(units.decibel_volt)
    back = dbv.to(units.volt)
    print(f"  {original} -> {dbv} -> {back}")


def demo_acoustics_dbspl():
    """Sound pressure in dBSPL."""
    section("Acoustics: Pascals to dBSPL")

    # dBSPL reference is 20 µPa (threshold of hearing)
    # dBSPL = 20 * log10(P / 20µPa)
    print("Sound pressure levels:")
    print("Reference: 20 µPa (threshold of human hearing)")
    print()

    sounds = [
        (20e-6, "Threshold of hearing"),
        (2e-4, "Quiet whisper"),
        (2e-3, "Normal conversation"),
        (0.2, "Heavy traffic"),
        (2.0, "Jackhammer"),
        (20.0, "Jet engine (pain threshold)"),
    ]

    for pascals, description in sounds:
        p = units.pascal(pascals)
        dbspl = p.to(units.decibel_spl)
        print(f"  {pascals:8.2e} Pa = {dbspl.quantity:5.0f} dBSPL  ({description})")


def demo_ph():
    """pH (hydrogen ion concentration)."""
    section("Chemistry: Concentration to pH")

    # pH = -log10([H+] / 1 mol/L)
    print("Hydrogen ion concentration to pH:")
    print("pH = -log10([H+])")
    print()

    solutions = [
        (1.0, "1 M HCl (strongly acidic)"),
        (1e-3, "Vinegar (~pH 3)"),
        (1e-7, "Pure water (neutral)"),
        (1e-10, "Baking soda solution"),
        (1e-14, "1 M NaOH (strongly basic)"),
    ]

    mol_per_liter = units.mole / units.liter

    for concentration, description in solutions:
        conc = mol_per_liter(concentration)
        ph = conc.to(units.pH)
        print(f"  [H+] = {concentration:.0e} mol/L  ->  pH {ph.quantity:5.1f}  ({description})")

    print()

    # Inverse: pH to concentration
    print("Converting pH back to concentration:")
    for ph_val in [1, 4, 7, 10, 14]:
        ph = units.pH(ph_val)
        conc = ph.to(mol_per_liter)
        print(f"  pH {ph_val:2} = [H+] {conc.quantity:.0e} mol/L")


def demo_sre_nines():
    """SRE availability in nines notation."""
    section("SRE: Availability in Nines")

    # Nines: -log10(1 - availability)
    # 99.9% = 3 nines, 99.99% = 4 nines, etc.
    print("Availability percentage to nines:")
    print("nines = -log10(1 - availability)")
    print()

    availabilities = [
        (0.9, "90% (1 nine)"),
        (0.99, "99% (2 nines)"),
        (0.999, "99.9% (3 nines)"),
        (0.9999, "99.99% (4 nines)"),
        (0.99999, "99.999% (5 nines)"),
    ]

    for frac, description in availabilities:
        avail = units.fraction(frac)
        nines = avail.to(units.nines)
        pct = avail.to(units.percent)
        print(f"  {pct.quantity:7.3f}% = {nines.quantity:.1f} nines  ({description})")

    print()

    # What does each nine mean in terms of downtime?
    print("Downtime per year for each availability level:")
    import math
    for nines_val in [2, 3, 4, 5]:
        # Calculate fraction from nines: frac = 1 - 10^(-nines)
        availability = 1 - 10**(-nines_val)
        downtime_fraction = 1 - availability
        # Seconds in a year
        seconds_per_year = 365.25 * 24 * 60 * 60
        downtime_seconds = downtime_fraction * seconds_per_year

        if downtime_seconds >= 3600:
            downtime_str = f"{downtime_seconds / 3600:.1f} hours"
        elif downtime_seconds >= 60:
            downtime_str = f"{downtime_seconds / 60:.1f} minutes"
        else:
            downtime_str = f"{downtime_seconds:.1f} seconds"

        print(f"  {nines_val} nines ({availability * 100:.4f}%): ~{downtime_str}/year")


def demo_round_trips():
    """Demonstrate round-trip conversions preserve values."""
    section("Round-Trip Verification")

    print("All logarithmic conversions should round-trip correctly:")
    print()

    test_cases = [
        ("watt", units.watt(0.5), units.decibel_milliwatt),
        ("volt", units.volt(3.5), units.decibel_volt),
        ("pascal", units.pascal(0.1), units.decibel_spl),
        ("mol/L", (units.mole / units.liter)(3.16e-5), units.pH),
        ("fraction", units.fraction(0.9999), units.nines),
    ]

    for name, original, log_unit in test_cases:
        log_val = original.to(log_unit)
        back = log_val.to(original.unit)

        # Check relative error
        rel_error = abs(back.quantity - original.quantity) / original.quantity

        status = "PASS" if rel_error < 1e-10 else "FAIL"
        print(f"  [{status}] {name}: {original} -> {log_unit.name} -> {back}")


def main():
    print("=" * 60)
    print("  ucon Logarithmic Units Demo")
    print("=" * 60)

    demo_ratio_conversions()
    demo_power_dbm()
    demo_power_dbw()
    demo_voltage_dbv()
    demo_acoustics_dbspl()
    demo_ph()
    demo_sre_nines()
    demo_round_trips()

    print()
    print("Demo complete!")


if __name__ == "__main__":
    main()

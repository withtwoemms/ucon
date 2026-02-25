#!/usr/bin/env python
# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Example: Parsing Human-Readable Quantity Strings

Demonstrates the parse() function for converting strings like "60 mi/h"
or "1.234 ± 0.005 m" into Number objects.
"""

from ucon import parse


def main():
    # -------------------------------------------------------------------------
    # Basic Quantities
    # -------------------------------------------------------------------------
    print("=== Basic Quantities ===")
    print(f"parse('9.81 m/s^2')     = {parse('9.81 m/s^2')}")
    print(f"parse('1.5 kg')         = {parse('1.5 kg')}")
    print(f"parse('60 mi/h')        = {parse('60 mi/h')}")
    print(f"parse('500 mL')         = {parse('500 mL')}")

    # -------------------------------------------------------------------------
    # Dimensionless Numbers
    # -------------------------------------------------------------------------
    print("\n=== Dimensionless ===")
    print(f"parse('100')            = {parse('100')}")
    print(f"parse('3.14159')        = {parse('3.14159')}")

    # -------------------------------------------------------------------------
    # Scientific Notation
    # -------------------------------------------------------------------------
    print("\n=== Scientific Notation ===")
    print(f"parse('1.5e3 m')        = {parse('1.5e3 m')}")
    print(f"parse('6.022e23')       = {parse('6.022e23')}")
    print(f"parse('1e-9 s')         = {parse('1e-9 s')}")

    # -------------------------------------------------------------------------
    # Negative Values
    # -------------------------------------------------------------------------
    print("\n=== Negative Values ===")
    print(f"parse('-273.15 degC')   = {parse('-273.15 degC')}")
    print(f"parse('-9.8 m/s^2')     = {parse('-9.8 m/s^2')}")

    # -------------------------------------------------------------------------
    # Uncertainty with ± Notation
    # -------------------------------------------------------------------------
    print("\n=== Uncertainty (±) ===")
    print(f"parse('1.234 ± 0.005 m')     = {parse('1.234 ± 0.005 m')}")
    print(f"parse('100 +/- 5 kg')        = {parse('100 +/- 5 kg')}")
    print(f"parse('9.81 ± 0.01 m/s^2')   = {parse('9.81 ± 0.01 m/s^2')}")

    # -------------------------------------------------------------------------
    # Parenthetical Uncertainty (Metrology Convention)
    #
    # The number in parentheses represents uncertainty in the last digit(s):
    #   1.234(5)  means 1.234 ± 0.005
    #   1.234(56) means 1.234 ± 0.056
    # -------------------------------------------------------------------------
    print("\n=== Parenthetical Uncertainty ===")
    print(f"parse('1.234(5) m')     = {parse('1.234(5) m')}  # means 1.234 ± 0.005")
    print(f"parse('1.234(56) m')    = {parse('1.234(56) m')}  # means 1.234 ± 0.056")
    print(f"parse('9.81(2) m/s^2')  = {parse('9.81(2) m/s^2')}  # means 9.81 ± 0.02")

    # -------------------------------------------------------------------------
    # Uncertainty with Repeated Unit
    # -------------------------------------------------------------------------
    print("\n=== Uncertainty With Unit ===")
    print(f"parse('1.234 m ± 0.005 m') = {parse('1.234 m ± 0.005 m')}")

    # -------------------------------------------------------------------------
    # Unicode Support
    # -------------------------------------------------------------------------
    print("\n=== Unicode Support ===")
    print(f"parse('9.81 m/s²')      = {parse('9.81 m/s²')}")
    print(f"parse('100 cm³')        = {parse('100 cm³')}")

    # -------------------------------------------------------------------------
    # Accessing Parsed Values
    # -------------------------------------------------------------------------
    print("\n=== Accessing Parsed Values ===")
    n = parse("1.234 ± 0.005 m")
    print(f"n = parse('1.234 ± 0.005 m')")
    print(f"  n.value       = {n.value}")
    print(f"  n.uncertainty = {n.uncertainty}")
    print(f"  n.unit        = {n.unit}")

    # -------------------------------------------------------------------------
    # Arithmetic with Parsed Values
    # -------------------------------------------------------------------------
    print("\n=== Arithmetic with Parsed Values ===")
    distance = parse("100 m")
    time = parse("10 s")
    velocity = distance / time
    print(f"distance = parse('100 m')  = {distance}")
    print(f"time     = parse('10 s')   = {time}")
    print(f"velocity = distance / time = {velocity}")


if __name__ == "__main__":
    main()

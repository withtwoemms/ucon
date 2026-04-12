# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for ucon.expressions — AST expression parser with GUM uncertainty."""

import math
import pytest

from ucon.expressions import ExprResult, evaluate


# ── Fixtures ──────────────────────────────────────────────────────────

CONSTANTS = {
    "c": ExprResult(299_792_458.0, 0.0),            # exact
    "h": ExprResult(6.62607015e-34, 0.0),            # exact
    "Eh": ExprResult(4.3597447222060e-18, 1.1e-12),  # measured
    "mP": ExprResult(2.176434e-8, 1.1e-5),           # measured
    "G": ExprResult(6.67430e-11, 2.2e-5),            # measured
}


# ── 1. Numeric literal ────────────────────────────────────────────────

class TestNumericLiteral:
    def test_integer(self):
        result = evaluate("42", {})
        assert result.value == 42.0
        assert result.rel_uncertainty == 0.0

    def test_float(self):
        result = evaluate("3.14", {})
        assert result.value == pytest.approx(3.14)

    def test_scientific_notation(self):
        result = evaluate("1e-10", {})
        assert result.value == 1e-10


# ── 2. Constant reference ────────────────────────────────────────────

class TestConstantReference:
    def test_exact_constant(self):
        result = evaluate("c", CONSTANTS)
        assert result.value == 299_792_458.0
        assert result.rel_uncertainty == 0.0

    def test_measured_constant(self):
        result = evaluate("Eh", CONSTANTS)
        assert result.value == 4.3597447222060e-18
        assert result.rel_uncertainty == 1.1e-12


# ── 3. Division ──────────────────────────────────────────────────────

class TestDivision:
    def test_reciprocal_of_measured(self):
        result = evaluate("1 / Eh", CONSTANTS)
        expected = 1.0 / 4.3597447222060e-18
        assert result.value == pytest.approx(expected)
        # rel_uncertainty passes through: sqrt(0² + rel²) = rel
        assert result.rel_uncertainty == pytest.approx(1.1e-12)

    def test_division_by_zero(self):
        with pytest.raises(ValueError, match="Division by zero"):
            evaluate("1 / 0", {})


# ── 4. Multiplication ───────────────────────────────────────────────

class TestMultiplication:
    def test_exact_times_exact(self):
        result = evaluate("h * c", CONSTANTS)
        expected = 6.62607015e-34 * 299_792_458.0
        assert result.value == pytest.approx(expected)
        assert result.rel_uncertainty == 0.0

    def test_measured_times_exact(self):
        result = evaluate("Eh * c", CONSTANTS)
        assert result.rel_uncertainty == pytest.approx(1.1e-12)

    def test_measured_times_measured(self):
        result = evaluate("Eh * G", CONSTANTS)
        expected_rel = math.hypot(1.1e-12, 2.2e-5)
        assert result.rel_uncertainty == pytest.approx(expected_rel)


# ── 5. Power ─────────────────────────────────────────────────────────

class TestPower:
    def test_exact_squared(self):
        result = evaluate("c**2", CONSTANTS)
        assert result.value == pytest.approx(299_792_458.0 ** 2)
        assert result.rel_uncertainty == 0.0

    def test_measured_squared(self):
        result = evaluate("mP**2", CONSTANTS)
        assert result.value == pytest.approx(2.176434e-8 ** 2)
        # rel = |n| * rel(base)
        assert result.rel_uncertainty == pytest.approx(2 * 1.1e-5)

    def test_uncertain_exponent_rejected(self):
        with pytest.raises(ValueError, match="Exponent must be an exact"):
            evaluate("c**G", CONSTANTS)


# ── 6. Compound expression ──────────────────────────────────────────

class TestCompound:
    def test_planck_energy(self):
        # E_P = mP * c²
        result = evaluate("mP * c**2", CONSTANTS)
        expected = 2.176434e-8 * (299_792_458.0 ** 2)
        assert result.value == pytest.approx(expected)
        # c is exact, so rel = rel(mP)
        assert result.rel_uncertainty == pytest.approx(1.1e-5)

    def test_parenthesized(self):
        result = evaluate("(h * c) / Eh", CONSTANTS)
        expected = (6.62607015e-34 * 299_792_458.0) / 4.3597447222060e-18
        assert result.value == pytest.approx(expected)


# ── 7. Unknown symbol ───────────────────────────────────────────────

class TestUnknownSymbol:
    def test_raises(self):
        with pytest.raises(ValueError, match="Unknown symbol"):
            evaluate("x", {})


# ── 8. Unsupported syntax ───────────────────────────────────────────

class TestUnsupportedSyntax:
    def test_function_call(self):
        with pytest.raises(ValueError, match="Unsupported"):
            evaluate("sin(1)", CONSTANTS)

    def test_attribute_access(self):
        with pytest.raises(ValueError, match="Unsupported"):
            evaluate("c.value", CONSTANTS)

    def test_invalid_syntax(self):
        with pytest.raises(ValueError, match="Invalid expression"):
            evaluate("1 +", {})


# ── Unary operators ──────────────────────────────────────────────────

class TestUnaryOps:
    def test_negative(self):
        result = evaluate("-42", {})
        assert result.value == -42.0

    def test_negative_constant(self):
        result = evaluate("-Eh", CONSTANTS)
        assert result.value == pytest.approx(-4.3597447222060e-18)
        assert result.rel_uncertainty == 1.1e-12

    def test_positive(self):
        result = evaluate("+c", CONSTANTS)
        assert result.value == 299_792_458.0

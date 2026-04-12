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

    def test_unsupported_unary_operator(self):
        """Bitwise NOT (~) is parsed as ast.Invert — not supported."""
        with pytest.raises(ValueError, match="Unsupported unary operator"):
            evaluate("~42", {})


# ── 9. Addition ────────────────────────────────────────────────────────

class TestAddition:
    def test_exact_plus_exact(self):
        result = evaluate("1 + 2", {})
        assert result.value == 3.0
        assert result.rel_uncertainty == 0.0

    def test_measured_plus_exact(self):
        result = evaluate("Eh + 1", CONSTANTS)
        expected_val = 4.3597447222060e-18 + 1.0
        abs_unc = abs(4.3597447222060e-18) * 1.1e-12
        expected_rel = abs_unc / abs(expected_val)
        assert result.value == pytest.approx(expected_val)
        assert result.rel_uncertainty == pytest.approx(expected_rel)

    def test_measured_plus_measured(self):
        result = evaluate("Eh + G", CONSTANTS)
        eh_val = 4.3597447222060e-18
        g_val = 6.67430e-11
        expected_val = eh_val + g_val
        abs_eh = abs(eh_val) * 1.1e-12
        abs_g = abs(g_val) * 2.2e-5
        expected_rel = math.hypot(abs_eh, abs_g) / abs(expected_val)
        assert result.value == pytest.approx(expected_val)
        assert result.rel_uncertainty == pytest.approx(expected_rel)

    def test_add_to_zero(self):
        """When the sum is zero, rel_uncertainty falls back to 0.0."""
        consts = {
            "a": ExprResult(5.0, 0.01),
            "b": ExprResult(-5.0, 0.01),
        }
        result = evaluate("a + b", consts)
        assert result.value == 0.0
        assert result.rel_uncertainty == 0.0


# ── 10. Subtraction ───────────────────────────────────────────────────

class TestSubtraction:
    def test_exact_minus_exact(self):
        result = evaluate("10 - 3", {})
        assert result.value == 7.0
        assert result.rel_uncertainty == 0.0

    def test_measured_minus_exact(self):
        result = evaluate("Eh - 0", CONSTANTS)
        assert result.value == pytest.approx(4.3597447222060e-18)
        assert result.rel_uncertainty == pytest.approx(1.1e-12)

    def test_measured_minus_measured(self):
        """Subtraction of two measured values propagates via quadrature."""
        result = evaluate("G - Eh", CONSTANTS)
        g_val = 6.67430e-11
        eh_val = 4.3597447222060e-18
        expected_val = g_val - eh_val
        abs_g = abs(g_val) * 2.2e-5
        abs_eh = abs(eh_val) * 1.1e-12
        expected_rel = math.hypot(abs_g, abs_eh) / abs(expected_val)
        assert result.value == pytest.approx(expected_val)
        assert result.rel_uncertainty == pytest.approx(expected_rel)

    def test_subtract_to_zero(self):
        """When the difference is zero, rel_uncertainty falls back to 0.0."""
        consts = {"x": ExprResult(3.0, 0.02)}
        result = evaluate("x - x", consts)
        assert result.value == 0.0
        assert result.rel_uncertainty == 0.0


# ── 11. Unsupported binary operator ───────────────────────────────────

class TestUnsupportedBinOp:
    def test_modulo(self):
        with pytest.raises(ValueError, match="Unsupported binary operator"):
            evaluate("7 % 3", {})

    def test_floor_division(self):
        with pytest.raises(ValueError, match="Unsupported binary operator"):
            evaluate("7 // 3", {})


# ── 12. Unicode symbol normalization ──────────────────────────────────

class TestNormalizeSymbols:
    def test_non_identifier_symbol_replaced(self):
        """Symbols like 'a₀' that fail isidentifier() get safe placeholders."""
        consts = {"a₀": ExprResult(5.29177210544e-11, 1.5e-10)}
        result = evaluate("1 / a₀", consts)
        assert result.value == pytest.approx(1.0 / 5.29177210544e-11)
        assert result.rel_uncertainty == pytest.approx(1.5e-10)

    def test_non_identifier_symbol_not_in_expr(self):
        """Non-identifier symbols that don't appear in expr are left alone."""
        consts = {
            "a₀": ExprResult(5.29177210544e-11, 1.5e-10),
            "c": ExprResult(299_792_458.0, 0.0),
        }
        result = evaluate("c", consts)
        assert result.value == 299_792_458.0

    def test_multiple_non_identifier_symbols(self):
        """Multiple non-identifier symbols each get unique placeholders."""
        consts = {
            "a₀": ExprResult(5.29177210544e-11, 1.5e-10),
            "μ₀": ExprResult(1.25663706127e-6, 1.6e-10),
        }
        result = evaluate("μ₀ * a₀", consts)
        expected = 1.25663706127e-6 * 5.29177210544e-11
        assert result.value == pytest.approx(expected)

    def test_identifier_symbol_with_nfkc_form_in_table(self):
        """Symbols whose NFKC form is a valid identifier (e.g. gₙ → gn)
        are NOT handled by _normalize_symbols — callers must register the
        NFKC form in the constants table separately (as serialization.py does).
        """
        import unicodedata
        # gₙ NFKC-normalizes to 'gn', which IS a valid identifier
        assert "gₙ".isidentifier()
        nfkc = unicodedata.normalize("NFKC", "gₙ")
        consts = {
            "gₙ": ExprResult(9.80665, 0.0),
            nfkc: ExprResult(9.80665, 0.0),  # register NFKC form too
        }
        result = evaluate("gₙ", consts)
        assert result.value == pytest.approx(9.80665)

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for MCP constants tools (v0.9.2)."""

import sys
import pytest


# Skip MCP tests on Python < 3.10 (FastMCP requires 3.10+)
pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="MCP requires Python 3.10+",
)


class TestListConstants:
    """Tests for list_constants tool."""

    def test_returns_list(self):
        from ucon.mcp.server import list_constants
        result = list_constants()
        assert isinstance(result, list)
        assert len(result) >= 17  # Built-in constants

    def test_filter_exact(self):
        from ucon.mcp.server import list_constants
        result = list_constants(category="exact")
        assert isinstance(result, list)
        for const in result:
            assert const.is_exact
            assert const.category == "exact"
        assert len(result) == 7

    def test_filter_derived(self):
        from ucon.mcp.server import list_constants
        result = list_constants(category="derived")
        assert isinstance(result, list)
        for const in result:
            assert const.category == "derived"
        assert len(result) == 3

    def test_filter_measured(self):
        from ucon.mcp.server import list_constants
        result = list_constants(category="measured")
        assert isinstance(result, list)
        for const in result:
            assert not const.is_exact
            assert const.category == "measured"
        assert len(result) == 7

    def test_filter_session_empty_initially(self):
        from ucon.mcp.server import list_constants, reset_session
        reset_session()
        result = list_constants(category="session")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_filter_invalid_category(self):
        from ucon.mcp.server import list_constants, ConstantError
        result = list_constants(category="invalid")
        assert isinstance(result, ConstantError)
        assert result.error_type == "invalid_input"

    def test_includes_speed_of_light(self):
        from ucon.mcp.server import list_constants
        result = list_constants()
        symbols = [c.symbol for c in result]
        assert "c" in symbols

    def test_includes_gravitational_constant(self):
        from ucon.mcp.server import list_constants
        result = list_constants()
        symbols = [c.symbol for c in result]
        assert "G" in symbols

    def test_constant_info_has_all_fields(self):
        from ucon.mcp.server import list_constants
        result = list_constants()
        const = result[0]
        assert hasattr(const, 'symbol')
        assert hasattr(const, 'name')
        assert hasattr(const, 'value')
        assert hasattr(const, 'unit')
        assert hasattr(const, 'dimension')
        assert hasattr(const, 'uncertainty')
        assert hasattr(const, 'is_exact')
        assert hasattr(const, 'source')
        assert hasattr(const, 'category')


class TestDefineConstant:
    """Tests for define_constant tool."""

    def test_define_success(self):
        from ucon.mcp.server import define_constant, reset_session, ConstantDefinitionResult
        reset_session()
        result = define_constant(
            symbol="test_vs",
            name="speed of sound",
            value=343,
            unit="m/s",
        )
        assert isinstance(result, ConstantDefinitionResult)
        assert result.success
        assert result.symbol == "test_vs"

    def test_duplicate_builtin_symbol_fails(self):
        from ucon.mcp.server import define_constant, ConstantError
        result = define_constant(
            symbol="c",
            name="my speed",
            value=300000000,
            unit="m/s",
        )
        assert isinstance(result, ConstantError)
        assert result.error_type == "duplicate_symbol"

    def test_duplicate_session_symbol_fails(self):
        from ucon.mcp.server import define_constant, reset_session, ConstantError
        reset_session()
        # Define first time
        define_constant(
            symbol="test_dup",
            name="first",
            value=1,
            unit="m",
        )
        # Try to define again
        result = define_constant(
            symbol="test_dup",
            name="second",
            value=2,
            unit="m",
        )
        assert isinstance(result, ConstantError)
        assert result.error_type == "duplicate_symbol"

    def test_invalid_unit_fails(self):
        from ucon.mcp.server import define_constant, reset_session, ConstantError
        reset_session()
        result = define_constant(
            symbol="test_Y",
            name="Y",
            value=1,
            unit="invalid_unit_xyz",
        )
        assert isinstance(result, ConstantError)
        assert result.error_type == "invalid_unit"

    def test_nan_value_fails(self):
        import math
        from ucon.mcp.server import define_constant, reset_session, ConstantError
        reset_session()
        result = define_constant(
            symbol="test_nan",
            name="NaN constant",
            value=math.nan,
            unit="m",
        )
        assert isinstance(result, ConstantError)
        assert result.error_type == "invalid_value"

    def test_inf_value_fails(self):
        import math
        from ucon.mcp.server import define_constant, reset_session, ConstantError
        reset_session()
        result = define_constant(
            symbol="test_inf",
            name="Inf constant",
            value=math.inf,
            unit="m",
        )
        assert isinstance(result, ConstantError)
        assert result.error_type == "invalid_value"

    def test_negative_uncertainty_fails(self):
        from ucon.mcp.server import define_constant, reset_session, ConstantError
        reset_session()
        result = define_constant(
            symbol="test_neg_unc",
            name="negative uncertainty",
            value=1.0,
            unit="m",
            uncertainty=-0.1,
        )
        assert isinstance(result, ConstantError)
        assert result.error_type == "invalid_value"

    def test_with_uncertainty(self):
        from ucon.mcp.server import define_constant, reset_session, ConstantDefinitionResult
        reset_session()
        result = define_constant(
            symbol="test_unc",
            name="with uncertainty",
            value=1.0,
            unit="m",
            uncertainty=0.01,
        )
        assert isinstance(result, ConstantDefinitionResult)
        assert result.success
        assert result.uncertainty == 0.01

    def test_defined_constant_appears_in_session_list(self):
        from ucon.mcp.server import define_constant, list_constants, reset_session
        reset_session()
        define_constant(
            symbol="test_sess",
            name="session constant",
            value=42,
            unit="kg",
        )
        result = list_constants(category="session")
        assert len(result) == 1
        assert result[0].symbol == "test_sess"
        assert result[0].category == "session"


class TestResetSession:
    """Tests for reset_session clearing constants."""

    def test_reset_clears_session_constants(self):
        from ucon.mcp.server import define_constant, list_constants, reset_session
        reset_session()
        # Define a constant
        define_constant(
            symbol="test_clear",
            name="to be cleared",
            value=1,
            unit="m",
        )
        # Verify it exists
        result = list_constants(category="session")
        assert len(result) == 1

        # Reset
        reset_session()

        # Verify it's gone
        result = list_constants(category="session")
        assert len(result) == 0


class TestConstantsCategoryCounts:
    """Tests for correct counts of constants by category."""

    def test_total_builtin_constants(self):
        from ucon.mcp.server import list_constants
        exact = list_constants(category="exact")
        derived = list_constants(category="derived")
        measured = list_constants(category="measured")
        total = len(exact) + len(derived) + len(measured)
        assert total == 17

    def test_exact_constants_are_exact(self):
        from ucon.mcp.server import list_constants
        exact = list_constants(category="exact")
        for const in exact:
            assert const.uncertainty is None
            assert const.is_exact is True

    def test_measured_constants_have_uncertainty(self):
        from ucon.mcp.server import list_constants
        measured = list_constants(category="measured")
        for const in measured:
            assert const.uncertainty is not None
            assert const.is_exact is False

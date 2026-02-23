# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for formula registry and schema introspection."""

import pytest

from ucon import Number, Dimension, enforce_dimensions
from ucon.mcp.formulas import (
    FormulaInfo,
    register_formula,
    list_formulas,
    get_formula,
    clear_formulas,
)
from ucon.mcp.schema import extract_dimension_constraints


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear formula registry before and after each test."""
    clear_formulas()
    yield
    clear_formulas()


# -----------------------------------------------------------------------------
# Schema Introspection Tests
# -----------------------------------------------------------------------------


class TestExtractDimensionConstraints:
    """Tests for extract_dimension_constraints()."""

    def test_extracts_single_constraint(self):
        @enforce_dimensions
        def measure(length: Number[Dimension.length]) -> Number:
            return length

        constraints = extract_dimension_constraints(measure)
        assert constraints == {'length': 'length'}

    def test_extracts_multiple_constraints(self):
        @enforce_dimensions
        def speed(
            distance: Number[Dimension.length],
            time: Number[Dimension.time],
        ) -> Number:
            return distance / time

        constraints = extract_dimension_constraints(speed)
        assert constraints == {'distance': 'length', 'time': 'time'}

    def test_unconstrained_params_are_none(self):
        @enforce_dimensions
        def mixed(
            mass: Number[Dimension.mass],
            factor: Number,  # No dimension constraint
        ) -> Number:
            return mass * factor

        constraints = extract_dimension_constraints(mixed)
        assert constraints == {'mass': 'mass', 'factor': None}

    def test_handles_unwrapped_function(self):
        """Works on functions without @enforce_dimensions."""
        def bare(distance: Number[Dimension.length]) -> Number:
            return distance

        constraints = extract_dimension_constraints(bare)
        assert constraints == {'distance': 'length'}

    def test_handles_no_annotations(self):
        def untyped(x, y):
            return x + y

        constraints = extract_dimension_constraints(untyped)
        assert constraints == {}

    def test_excludes_return_annotation(self):
        @enforce_dimensions
        def with_return(
            time: Number[Dimension.time],
        ) -> Number[Dimension.time]:
            return time

        constraints = extract_dimension_constraints(with_return)
        assert 'return' not in constraints
        assert constraints == {'time': 'time'}


# -----------------------------------------------------------------------------
# Formula Registry Tests
# -----------------------------------------------------------------------------


class TestRegisterFormula:
    """Tests for @register_formula decorator."""

    def test_registers_formula(self):
        @register_formula("test_formula", description="A test formula")
        @enforce_dimensions
        def test_fn(x: Number[Dimension.length]) -> Number:
            return x

        info = get_formula("test_formula")
        assert info is not None
        assert info.name == "test_formula"
        assert info.description == "A test formula"
        assert info.parameters == {'x': 'length'}
        assert info.fn is test_fn

    def test_returns_original_function(self):
        @register_formula("identity_test")
        def original(x: Number) -> Number:
            return x

        # Decorator should return the function unchanged
        result = original(Number(5))
        assert result.quantity == 5

    def test_duplicate_name_raises(self):
        @register_formula("duplicate")
        def first():
            pass

        with pytest.raises(ValueError, match="already registered"):
            @register_formula("duplicate")
            def second():
                pass

    def test_empty_description_default(self):
        @register_formula("no_desc")
        def nodesc():
            pass

        info = get_formula("no_desc")
        assert info.description == ""


class TestListFormulas:
    """Tests for list_formulas()."""

    def test_empty_registry(self):
        assert list_formulas() == []

    def test_returns_all_formulas(self):
        @register_formula("alpha")
        def a():
            pass

        @register_formula("beta")
        def b():
            pass

        formulas = list_formulas()
        assert len(formulas) == 2
        names = [f.name for f in formulas]
        assert "alpha" in names
        assert "beta" in names

    def test_sorted_by_name(self):
        @register_formula("zebra")
        def z():
            pass

        @register_formula("apple")
        def a():
            pass

        formulas = list_formulas()
        assert formulas[0].name == "apple"
        assert formulas[1].name == "zebra"


class TestGetFormula:
    """Tests for get_formula()."""

    def test_returns_none_if_not_found(self):
        assert get_formula("nonexistent") is None

    def test_returns_formula_info(self):
        @register_formula("findme", description="Find this")
        def find():
            pass

        info = get_formula("findme")
        assert isinstance(info, FormulaInfo)
        assert info.name == "findme"
        assert info.description == "Find this"


class TestClearFormulas:
    """Tests for clear_formulas()."""

    def test_clears_all(self):
        @register_formula("temp")
        def temp():
            pass

        assert len(list_formulas()) == 1
        clear_formulas()
        assert len(list_formulas()) == 0


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------


class TestFormulaIntegration:
    """End-to-end tests for formula registration and introspection."""

    def test_medical_formula(self):
        """Test a realistic medical formula with multiple dimensions."""
        @register_formula("bmi", description="Body Mass Index")
        @enforce_dimensions
        def bmi(
            mass: Number[Dimension.mass],
            height: Number[Dimension.length],
        ) -> Number:
            return mass / (height * height)

        info = get_formula("bmi")
        assert info.parameters == {'mass': 'mass', 'height': 'length'}

    def test_formula_with_mixed_constraints(self):
        """Test formula with both constrained and unconstrained params."""
        @register_formula("dosage", description="Calculate medication dosage")
        @enforce_dimensions
        def dosage(
            patient_mass: Number[Dimension.mass],
            dose_per_kg: Number,  # Unconstrained (could be mg/kg)
            frequency: Number[Dimension.frequency],
        ) -> Number:
            return patient_mass * dose_per_kg * frequency

        info = get_formula("dosage")
        assert info.parameters == {
            'patient_mass': 'mass',
            'dose_per_kg': None,
            'frequency': 'frequency',
        }

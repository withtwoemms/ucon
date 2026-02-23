# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for Basis abstraction (BasisComponent, Basis, Vector)."""

from fractions import Fraction

import pytest

from ucon.basis import Basis, BasisComponent, Vector


# -----------------------------------------------------------------------------
# BasisComponent Tests
# -----------------------------------------------------------------------------


class TestBasisComponent:
    """Tests for BasisComponent."""

    def test_str_returns_name_when_no_symbol(self):
        """GIVEN a component name, WHEN no symbol, THEN str returns name."""
        component = BasisComponent("length")
        assert str(component) == "length"

    def test_str_returns_symbol_when_provided(self):
        """GIVEN a component with symbol, THEN str returns symbol."""
        component = BasisComponent("length", symbol="L")
        assert str(component) == "L"

    def test_equality_same_name_and_symbol(self):
        """GIVEN two components with same name/symbol, THEN they are equal."""
        c1 = BasisComponent("length", "L")
        c2 = BasisComponent("length", "L")
        assert c1 == c2

    def test_equality_different_symbol(self):
        """GIVEN two components with different symbols, THEN not equal."""
        c1 = BasisComponent("length", "L")
        c2 = BasisComponent("length", "X")
        assert c1 != c2

    def test_hashable_for_dict_key(self):
        """GIVEN a BasisComponent, THEN it is hashable."""
        component = BasisComponent("length", "L")
        d = {component: "value"}
        assert d[component] == "value"

    def test_frozen_immutable(self):
        """GIVEN a BasisComponent, THEN it cannot be mutated."""
        component = BasisComponent("length", "L")
        with pytest.raises(AttributeError):
            component.name = "mass"


# -----------------------------------------------------------------------------
# Basis Construction Tests
# -----------------------------------------------------------------------------


class TestBasisConstruction:
    """Tests for Basis construction."""

    def test_construction_from_strings(self):
        """GIVEN a list of strings, THEN Basis is constructed with correct length."""
        basis = Basis("Mechanics", ["length", "mass", "time"])
        assert len(basis) == 3

    def test_construction_from_components(self):
        """GIVEN BasisComponent objects, THEN they are stored as-is."""
        length = BasisComponent("length", "L")
        mass = BasisComponent("mass", "M")
        basis = Basis("Test", [length, mass])
        assert basis[0] is length
        assert basis[1] is mass

    def test_construction_mixed_strings_and_components(self):
        """GIVEN mixed strings and BasisComponents, THEN strings are normalized."""
        mass = BasisComponent("mass", "M")
        basis = Basis("Mixed", ["length", mass])
        assert len(basis) == 2
        assert isinstance(basis[0], BasisComponent)
        assert basis[0].name == "length"
        assert basis[1] is mass

    def test_name_property(self):
        """GIVEN a Basis, THEN name property returns the name."""
        basis = Basis("TestBasis", ["x", "y"])
        assert basis.name == "TestBasis"


# -----------------------------------------------------------------------------
# Collision Detection Tests
# -----------------------------------------------------------------------------


class TestBasisCollisionDetection:
    """Tests for Basis collision detection."""

    def test_duplicate_names_raises(self):
        """GIVEN duplicate component names, THEN ValueError is raised."""
        with pytest.raises(ValueError, match="component name 'length' conflicts"):
            Basis("Bad", ["length", "length"])

    def test_symbol_collides_with_name(self):
        """GIVEN a symbol that collides with an existing name, THEN ValueError."""
        with pytest.raises(ValueError, match="symbol 'L' conflicts"):
            Basis(
                "Bad",
                [BasisComponent("L", "X"), BasisComponent("mass", "L")],
            )

    def test_name_collides_with_symbol(self):
        """GIVEN a name that collides with an existing symbol, THEN ValueError."""
        with pytest.raises(ValueError, match="component name 'M' conflicts"):
            Basis(
                "Bad",
                [BasisComponent("length", "M"), BasisComponent("M")],
            )


# -----------------------------------------------------------------------------
# Index Lookup Tests
# -----------------------------------------------------------------------------


class TestBasisIndexLookup:
    """Tests for Basis index lookup."""

    def test_index_by_name(self):
        """GIVEN a basis, WHEN index(name), THEN position is returned."""
        basis = Basis("Test", [BasisComponent("length", "L"), BasisComponent("mass", "M")])
        assert basis.index("length") == 0
        assert basis.index("mass") == 1

    def test_index_by_symbol(self):
        """GIVEN a basis, WHEN index(symbol), THEN same position is returned."""
        basis = Basis("Test", [BasisComponent("length", "L"), BasisComponent("mass", "M")])
        assert basis.index("L") == 0
        assert basis.index("M") == 1

    def test_index_unknown_raises_keyerror(self):
        """GIVEN a basis without 'foo', THEN index('foo') raises KeyError."""
        basis = Basis("Test", ["length", "mass"])
        with pytest.raises(KeyError, match="'foo' not found in basis 'Test'"):
            basis.index("foo")


# -----------------------------------------------------------------------------
# Containment Tests
# -----------------------------------------------------------------------------


class TestBasisContainment:
    """Tests for Basis containment."""

    def test_contains_by_name(self):
        """GIVEN a basis with 'length', THEN 'length' in basis is True."""
        basis = Basis("Test", ["length", "mass"])
        assert "length" in basis
        assert "mass" in basis

    def test_contains_by_symbol(self):
        """GIVEN a basis with symbol 'L', THEN 'L' in basis is True."""
        basis = Basis("Test", [BasisComponent("length", "L")])
        assert "L" in basis

    def test_not_contains(self):
        """GIVEN a basis without 'foo', THEN 'foo' in basis is False."""
        basis = Basis("Test", ["length", "mass"])
        assert "foo" not in basis


# -----------------------------------------------------------------------------
# Iteration and Properties Tests
# -----------------------------------------------------------------------------


class TestBasisIterationAndProperties:
    """Tests for Basis iteration and properties."""

    def test_iteration_returns_components(self):
        """GIVEN a basis, WHEN iterated, THEN BasisComponent objects are yielded."""
        basis = Basis("Test", ["length", "mass", "time"])
        components = list(basis)
        assert len(components) == 3
        assert all(isinstance(c, BasisComponent) for c in components)

    def test_component_names_property(self):
        """GIVEN a basis, THEN component_names returns tuple of names."""
        basis = Basis("Test", ["length", "mass", "time"])
        assert basis.component_names == ("length", "mass", "time")

    def test_getitem_by_index(self):
        """GIVEN a basis, THEN indexing returns the component."""
        basis = Basis("Test", ["length", "mass"])
        assert basis[0].name == "length"
        assert basis[1].name == "mass"

    def test_repr(self):
        """GIVEN a basis, THEN repr is informative."""
        basis = Basis("Test", ["length", "mass"])
        assert repr(basis) == "Basis('Test', ['length', 'mass'])"


# -----------------------------------------------------------------------------
# Zero Vector Factory Tests
# -----------------------------------------------------------------------------


class TestBasisZeroVector:
    """Tests for Basis.zero_vector()."""

    def test_zero_vector_has_correct_components(self):
        """GIVEN a basis, WHEN zero_vector(), THEN all components are Fraction(0)."""
        basis = Basis("Test", ["length", "mass", "time"])
        zero = basis.zero_vector()
        assert zero.components == (Fraction(0), Fraction(0), Fraction(0))

    def test_zero_vector_has_same_basis(self):
        """GIVEN a basis, WHEN zero_vector(), THEN vector.basis is same object."""
        basis = Basis("Test", ["length", "mass"])
        zero = basis.zero_vector()
        assert zero.basis is basis


# -----------------------------------------------------------------------------
# Basis Immutability Tests
# -----------------------------------------------------------------------------


class TestBasisImmutability:
    """Tests for Basis immutability."""

    def test_name_cannot_be_set(self):
        """GIVEN a Basis, THEN name cannot be reassigned."""
        basis = Basis("Test", ["length"])
        with pytest.raises(AttributeError):
            basis.name = "New"

    def test_components_tuple_is_immutable(self):
        """GIVEN a Basis, THEN _components is a tuple (immutable)."""
        basis = Basis("Test", ["length", "mass"])
        assert isinstance(basis._components, tuple)

    def test_basis_is_hashable(self):
        """GIVEN a Basis, THEN it is hashable."""
        basis = Basis("Test", ["length", "mass"])
        d = {basis: "value"}
        assert d[basis] == "value"

    def test_basis_equality(self):
        """GIVEN two bases with same name and components, THEN they are equal."""
        b1 = Basis("Test", ["length", "mass"])
        b2 = Basis("Test", ["length", "mass"])
        assert b1 == b2

    def test_basis_inequality(self):
        """GIVEN two bases with different components, THEN they are not equal."""
        b1 = Basis("Test", ["length", "mass"])
        b2 = Basis("Test", ["length", "time"])
        assert b1 != b2


# -----------------------------------------------------------------------------
# Vector Tests
# -----------------------------------------------------------------------------


class TestVector:
    """Tests for basis-aware Vector."""

    @pytest.fixture
    def mechanics_basis(self):
        """A simple 3-component mechanics basis."""
        return Basis(
            "Mechanics",
            [
                BasisComponent("length", "L"),
                BasisComponent("mass", "M"),
                BasisComponent("time", "T"),
            ],
        )

    def test_construction(self, mechanics_basis):
        """GIVEN a basis and components, THEN Vector is constructed."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(-2)))
        assert v.basis is mechanics_basis
        assert v.components == (Fraction(1), Fraction(0), Fraction(-2))

    def test_construction_wrong_length_raises(self, mechanics_basis):
        """GIVEN wrong number of components, THEN ValueError is raised."""
        with pytest.raises(ValueError, match="has 2 components but basis.*has 3"):
            Vector(mechanics_basis, (Fraction(1), Fraction(0)))

    def test_getitem_by_index(self, mechanics_basis):
        """GIVEN a Vector, THEN integer indexing works."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(2), Fraction(3)))
        assert v[0] == Fraction(1)
        assert v[1] == Fraction(2)
        assert v[2] == Fraction(3)

    def test_getitem_by_name(self, mechanics_basis):
        """GIVEN a Vector, THEN name lookup works."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(2), Fraction(-1)))
        assert v["length"] == Fraction(1)
        assert v["mass"] == Fraction(2)
        assert v["time"] == Fraction(-1)

    def test_getitem_by_symbol(self, mechanics_basis):
        """GIVEN a Vector, THEN symbol lookup works."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(2), Fraction(-1)))
        assert v["L"] == Fraction(1)
        assert v["M"] == Fraction(2)
        assert v["T"] == Fraction(-1)

    def test_is_dimensionless(self, mechanics_basis):
        """GIVEN a zero vector, THEN is_dimensionless returns True."""
        zero = mechanics_basis.zero_vector()
        assert zero.is_dimensionless()

        nonzero = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(0)))
        assert not nonzero.is_dimensionless()

    def test_multiplication(self, mechanics_basis):
        """GIVEN two vectors, THEN multiplication adds exponents."""
        # length (L^1)
        v1 = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(0)))
        # time^-1 (T^-1)
        v2 = Vector(mechanics_basis, (Fraction(0), Fraction(0), Fraction(-1)))
        # velocity = length / time = L^1 * T^-1
        result = v1 * v2
        assert result.components == (Fraction(1), Fraction(0), Fraction(-1))

    def test_division(self, mechanics_basis):
        """GIVEN two vectors, THEN division subtracts exponents."""
        # length (L^1)
        v1 = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(0)))
        # time (T^1)
        v2 = Vector(mechanics_basis, (Fraction(0), Fraction(0), Fraction(1)))
        # velocity = length / time
        result = v1 / v2
        assert result.components == (Fraction(1), Fraction(0), Fraction(-1))

    def test_power(self, mechanics_basis):
        """GIVEN a vector, THEN power multiplies all exponents."""
        # length (L^1)
        v = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(0)))
        # area = length^2
        result = v**2
        assert result.components == (Fraction(2), Fraction(0), Fraction(0))

    def test_power_fractional(self, mechanics_basis):
        """GIVEN a vector, THEN fractional power works."""
        # area (L^2)
        v = Vector(mechanics_basis, (Fraction(2), Fraction(0), Fraction(0)))
        # sqrt(area) = length
        result = v ** Fraction(1, 2)
        assert result.components == (Fraction(1), Fraction(0), Fraction(0))

    def test_negation(self, mechanics_basis):
        """GIVEN a vector, THEN negation inverts all exponents."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(2), Fraction(-1)))
        result = -v
        assert result.components == (Fraction(-1), Fraction(-2), Fraction(1))

    def test_multiplication_different_bases_raises(self, mechanics_basis):
        """GIVEN vectors from different bases, THEN multiplication raises."""
        other_basis = Basis("Other", ["x", "y", "z"])
        v1 = mechanics_basis.zero_vector()
        v2 = other_basis.zero_vector()
        with pytest.raises(ValueError, match="Cannot multiply vectors from different bases"):
            v1 * v2

    def test_division_different_bases_raises(self, mechanics_basis):
        """GIVEN vectors from different bases, THEN division raises."""
        other_basis = Basis("Other", ["x", "y", "z"])
        v1 = mechanics_basis.zero_vector()
        v2 = other_basis.zero_vector()
        with pytest.raises(ValueError, match="Cannot divide vectors from different bases"):
            v1 / v2

    def test_equality(self, mechanics_basis):
        """GIVEN two equal vectors, THEN they compare equal."""
        v1 = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(-1)))
        v2 = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(-1)))
        assert v1 == v2

    def test_inequality_components(self, mechanics_basis):
        """GIVEN vectors with different components, THEN not equal."""
        v1 = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(0)))
        v2 = Vector(mechanics_basis, (Fraction(0), Fraction(1), Fraction(0)))
        assert v1 != v2

    def test_inequality_basis(self, mechanics_basis):
        """GIVEN vectors from different bases, THEN not equal."""
        other_basis = Basis("Other", ["length", "mass", "time"])
        v1 = mechanics_basis.zero_vector()
        v2 = other_basis.zero_vector()
        assert v1 != v2

    def test_hashable(self, mechanics_basis):
        """GIVEN a Vector, THEN it is hashable."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(-1)))
        d = {v: "velocity"}
        assert d[v] == "velocity"

    def test_repr_nonzero_components(self, mechanics_basis):
        """GIVEN a vector, THEN repr shows non-zero components."""
        v = Vector(mechanics_basis, (Fraction(1), Fraction(0), Fraction(-2)))
        assert "Mechanics" in repr(v)
        assert "length=1" in repr(v)
        assert "time=-2" in repr(v)
        assert "mass" not in repr(v)

    def test_repr_dimensionless(self, mechanics_basis):
        """GIVEN a zero vector, THEN repr indicates dimensionless."""
        v = mechanics_basis.zero_vector()
        assert "dimensionless" in repr(v)

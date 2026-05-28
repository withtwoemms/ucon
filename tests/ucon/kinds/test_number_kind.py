# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Regression suite for ``Number.kind`` (v2.0 §3.4 — slice 1 of KOQ-on-Number).

Pins three invariants from the §3.4 deliverable and the v4/v5/v6
architecture entries:

1. ``Number(kind=...)`` constructs when ``kind.dimension`` matches the
   unit's dimension.
2. Dimension mismatch at construction raises
   :class:`KindDimensionMismatch`.
3. ``Number.to(...)`` carries ``kind`` through every conversion path
   (fast, scale-only, general).

Equality semantics in this slice mirror the existing
``uncertainty``-style treatment: ``kind`` is a tag carried through
conversion but is **not** part of ``__eq__``. Equality refinement will
land with the arithmetic-dispatch slice, when ``kind`` first becomes
semantically active.
"""

from __future__ import annotations

import pytest

from ucon import KindDimensionMismatch, Number
from ucon.dimension import ENERGY, LENGTH
from ucon.kinds import Kind
from ucon.units import joule, meter


KINETIC_ENERGY = Kind("kinetic_energy", dimension=ENERGY)
POTENTIAL_ENERGY = Kind("potential_energy", dimension=ENERGY)
LENGTH_KIND = Kind("length_kind", dimension=LENGTH)


class TestNumberKindConstruction:
    """``Number(kind=...)`` accepts a matching Kind; absence is the default."""

    def test_default_kind_is_none(self) -> None:
        n = Number(500, joule)
        assert n.kind is None

    def test_explicit_matching_kind_is_stored(self) -> None:
        n = Number(500, joule, kind=KINETIC_ENERGY)
        assert n.kind is KINETIC_ENERGY

    def test_kind_attribute_is_reachable(self) -> None:
        n = Number(1, meter, kind=LENGTH_KIND)
        assert hasattr(n, "kind")
        assert n.kind.name == "length_kind"


class TestNumberKindDimensionValidation:
    """``kind.dimension`` must match ``unit.dimension`` (v4/v5/v6 deliverable)."""

    def test_mismatch_raises_kind_dimension_mismatch(self) -> None:
        with pytest.raises(KindDimensionMismatch) as exc_info:
            Number(5, meter, kind=KINETIC_ENERGY)
        exc = exc_info.value
        assert exc.kind is KINETIC_ENERGY
        assert exc.unit is meter

    def test_matching_dimensions_construct_successfully(self) -> None:
        # Should not raise.
        Number(500, joule, kind=KINETIC_ENERGY)
        Number(1, meter, kind=LENGTH_KIND)

    def test_dimensionless_number_with_dimensioned_kind_raises(self) -> None:
        with pytest.raises(KindDimensionMismatch):
            Number(5, kind=KINETIC_ENERGY)


class TestNumberKindEquality:
    """``kind`` is metadata at this slice; existing equality is unchanged."""

    def test_same_magnitude_same_kind_compare_equal(self) -> None:
        a = Number(500, joule, kind=KINETIC_ENERGY)
        b = Number(500, joule, kind=KINETIC_ENERGY)
        assert a == b

    def test_same_magnitude_different_kind_still_compare_equal(self) -> None:
        # Mirrors the uncertainty pattern: __eq__ keys off dimension +
        # canonical magnitude only. Kind-aware equality belongs with the
        # arithmetic-dispatch slice.
        a = Number(500, joule, kind=KINETIC_ENERGY)
        b = Number(500, joule, kind=POTENTIAL_ENERGY)
        assert a == b

    def test_different_magnitude_same_kind_compare_unequal(self) -> None:
        a = Number(500, joule, kind=KINETIC_ENERGY)
        b = Number(501, joule, kind=KINETIC_ENERGY)
        assert a != b


class TestNumberKindConversionPreservation:
    """``Number.to(...)`` carries ``kind`` through every conversion path."""

    def test_scale_only_conversion_preserves_kind(self) -> None:
        n = Number(500, joule, kind=KINETIC_ENERGY)
        m = n.to("kJ")
        assert m.kind is KINETIC_ENERGY

    def test_none_kind_remains_none_through_conversion(self) -> None:
        n = Number(500, joule)
        m = n.to("kJ")
        assert m.kind is None

    def test_general_path_conversion_preserves_kind(self) -> None:
        # Cross-unit conversion at the general path (different unit,
        # same dimension, scale + unit lookup through the graph).
        n = Number(1, meter, kind=LENGTH_KIND)
        m = n.to("cm")
        assert m.kind is LENGTH_KIND

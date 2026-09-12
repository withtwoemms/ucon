# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Deprecation-warning tests for ucon.

The v1.x deprecation tests (``get_unit_by_name``, ``using_graph``,
``set_default_graph``, ``reset_default_graph``, ``set_default_basis_graph``,
``reset_default_basis_graph``, ``UnitSystem.conversions``,
``UnitSystem.from_globals()``, ``UnitSystem(conversions=...)``,
``units.have()``, and the legacy ``_DIM_*_CACHE`` PEP-562 shims)
were retired when those symbols were removed in v2.0.

New deprecation cycles should add parametrized tests here following
the same pattern: verify that the symbol emits ``DeprecationWarning``
with a message citing the migration path.
"""

from __future__ import annotations

import warnings

import pytest

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:  # Python 3.7: stdlib importlib.metadata is 3.8+
    PackageNotFoundError = Exception  # type: ignore[assignment, misc]
    version = None  # type: ignore[assignment]

from ucon.dimension import Dimension, _build_standard_dimensions


def _installed_major() -> "int | None":
    if version is None:
        return None
    try:
        return int(version("ucon").split(".")[0])
    except (PackageNotFoundError, ValueError):
        return None


class TestPseudoDimensionDeprecation:
    """The 2.2.0 rung: pseudo-dimension declarations warn ahead of the
    3.0.0 retirement (kinds are the migration path)."""

    def test_dimension_pseudo_emits_pending_deprecation(self):
        with pytest.warns(PendingDeprecationWarning) as record:
            Dimension.pseudo("flavor", name="deprecation_probe")
        message = str(record[0].message)
        assert "3.0.0" in message          # removal version cited
        assert "Kind" in message           # migration path cited

    def test_builtin_pseudo_dimensions_do_not_warn(self):
        """The builtin four (angle, solid_angle, ratio, count) retire
        with the TOML schema at 3.0.0; declaring them at import time
        must stay silent."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", PendingDeprecationWarning)
            attrs, _ = _build_standard_dimensions()
        assert {"angle", "solid_angle", "ratio", "count"} <= set(attrs)

    def test_pseudo_dimension_rung_expires_at_3_0_0(self):
        """Version-gated expiry: when the installed major reaches 3,
        this test demands the removal actually happened rather than
        letting the rung ride past its cited deadline."""
        major = _installed_major()
        if major is None:
            pytest.skip("ucon distribution metadata unavailable")
        if major >= 3:
            pytest.fail(
                "The pseudo-dimension deprecation cited removal in "
                "3.0.0: remove Dimension.pseudo, the builtin tagged "
                "dimensions, and this rung."
            )
        with pytest.warns(PendingDeprecationWarning):
            Dimension.pseudo("expiry_probe", name="expiry_probe_dim")

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the v1.8 PEP-562 alias from ``ucon.UnitSystem`` to
``ucon.system.BaseUnits``.

The alias preserves backwards compatibility for code that still imports
``UnitSystem`` from the top-level ``ucon`` package. It emits
``PendingDeprecationWarning`` and resolves to :class:`BaseUnits`. The
alias is scheduled for removal in ucon 2.0.
"""

import warnings

import pytest

import ucon
from ucon.system import BaseUnits


def test_alias_emits_pending_deprecation_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cls = ucon.UnitSystem
    assert any(
        issubclass(item.category, PendingDeprecationWarning)
        and "BaseUnits" in str(item.message)
        for item in w
    ), f"expected PendingDeprecationWarning mentioning BaseUnits, got {[str(i.message) for i in w]}"
    assert cls is BaseUnits


def test_alias_resolves_to_baseunits_identity():
    # Two accesses should return the same object
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PendingDeprecationWarning)
        a = ucon.UnitSystem
        b = ucon.UnitSystem
    assert a is b is BaseUnits


def test_unknown_attribute_still_raises():
    with pytest.raises(AttributeError):
        ucon.SomeNameThatDoesNotExist  # noqa: B018

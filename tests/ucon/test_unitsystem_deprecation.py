# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the v2.0 top-level ``ucon.UnitSystem`` export.

In v1.8 ``ucon.UnitSystem`` was a deprecated alias for ``BaseUnits``.
In v2.0 ``UnitSystem`` is the real system type from ``ucon.system``,
exported directly. ``BaseUnits`` remains available under its own name.
"""

import pytest

import ucon
from ucon.system import BaseUnits, UnitSystem


def test_unitsystem_is_the_real_class():
    assert ucon.UnitSystem is UnitSystem


def test_unitsystem_is_not_baseunits():
    assert ucon.UnitSystem is not BaseUnits


def test_baseunits_still_exported():
    assert ucon.BaseUnits is BaseUnits


def test_unknown_attribute_still_raises():
    with pytest.raises(AttributeError):
        ucon.SomeNameThatDoesNotExist  # noqa: B018

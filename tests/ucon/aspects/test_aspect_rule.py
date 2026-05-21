# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the AspectRule enum and its v1.9.0 re-export shims.

`AspectRule` moved from `ucon.formulas.types` to `ucon.aspects.types` in
v1.9.1. `ucon.formulas` and `ucon.formulas.types` re-export the symbol
so existing v1.9.0 import paths continue to resolve to the same class.
"""

from __future__ import annotations

from ucon.aspects import AspectRule as AspectRule_canonical
from ucon.aspects.types import AspectRule as AspectRule_typesmod
from ucon.formulas import AspectRule as AspectRule_formulas
from ucon.formulas.types import AspectRule as AspectRule_formulas_types


def test_aspect_rule_values():
    assert AspectRule_canonical.CONSUME.value == "consume"
    assert AspectRule_canonical.CARRY.value == "carry"


def test_aspect_rule_string_constructor():
    assert AspectRule_canonical("consume") is AspectRule_canonical.CONSUME
    assert AspectRule_canonical("carry") is AspectRule_canonical.CARRY


def test_aspect_rule_reexport_identity_from_formulas_package():
    # `from ucon.formulas import AspectRule` (v1.9.0 path) must resolve
    # to the same class object as the v1.9.1 canonical path.
    assert AspectRule_formulas is AspectRule_canonical


def test_aspect_rule_reexport_identity_from_formulas_types_module():
    # `from ucon.formulas.types import AspectRule` must also resolve to
    # the same class object.
    assert AspectRule_formulas_types is AspectRule_canonical


def test_aspect_rule_canonical_identity_within_aspects_subpackage():
    # `ucon.aspects` and `ucon.aspects.types` expose the same class.
    assert AspectRule_typesmod is AspectRule_canonical


def test_aspect_rule_members_are_shared_across_import_paths():
    # Members must compare equal (and be `is`) across import paths,
    # otherwise downstream `is`-based rule dispatch breaks.
    assert AspectRule_formulas.CONSUME is AspectRule_canonical.CONSUME
    assert AspectRule_formulas.CARRY is AspectRule_canonical.CARRY

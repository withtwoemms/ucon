# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_algebra_laws
=================

Structural laws for the v2.0 ``UnitSystem`` algebra (§3.1 of the v2.0
implementation plan):

- *Identity-like*: self-extend and no-op restrict preserve registries.
- *Associativity*: ``(a.extend(b)).extend(c)`` and
  ``a.extend(b.extend(c))`` produce structurally-equal systems under any
  fixed non-raising conflict policy.
- *Idempotence of self-extend* under both ``prefer-self`` and
  ``prefer-other``.
- *Restrict monotonicity*: ``s.restrict(dimensions=D).subsystem_of(s)``
  for any ``D ⊆ s.dimensions``.

The state space is small: a handful of derived subsystems off the active
system. Each law is checked over named fixtures rather than randomized
inputs — that is sufficient to cover every meaningful configuration here
(see §6 q-rationale in the implementation plan; hypothesis is not used).

Note on equality
----------------
``UnitSystem.__eq__`` compares the mutable registry references by
identity, so two structurally-equal derived systems compare unequal.
The laws below are therefore expressed over *registry contents* via the
``_registries_equal`` helper, not via ``==`` on the systems.
"""

import unittest

import ucon
from ucon.system import ConflictPolicy, UnitSystem


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _active() -> UnitSystem:
    return ucon.active()


def _restrict_to(system: UnitSystem, dim_name: str) -> UnitSystem:
    return system.restrict(dimensions=[system.dimensions[dim_name]])


def _enum_edges(system: UnitSystem) -> dict:
    """Flatten the conversion graph's unit edges to a ``{(src, dst): map}``
    dict keyed by unit name. Mirrors ``_enumerate_unit_edges`` semantics.
    """
    out = {}
    for _dim, srcs in system.conversion_graph._unit_edges.items():
        for src, dsts in srcs.items():
            for dst, m in dsts.items():
                out[(src.name, dst.name)] = m
    return out


def _registries_equal(a: UnitSystem, b: UnitSystem) -> bool:
    """Structural equality on the public registries.

    Compared:
      - ``units`` key set and per-key :class:`Unit` equality
      - ``dimensions`` key set and per-key :class:`Dimension` equality
      - ``base_units`` (dimension → unit) by name
      - conversion-graph unit edges by ``(src_name, dst_name) → Map``

    Not compared: ``basis``, ``basis_graph``, ``contexts``, ``constants``
    (none of these are mutated by ``extend``/``restrict`` in the cases
    under test).
    """
    if set(a.units.keys()) != set(b.units.keys()):
        return False
    for name, unit in a.units.items():
        if b.units[name] != unit:
            return False

    if set(a.dimensions.keys()) != set(b.dimensions.keys()):
        return False
    for name, dim in a.dimensions.items():
        if b.dimensions[name] != dim:
            return False

    a_base = {d.name: u.name for d, u in a.base_units.bases.items()}
    b_base = {d.name: u.name for d, u in b.base_units.bases.items()}
    if a_base != b_base:
        return False

    return _enum_edges(a) == _enum_edges(b)


# ---------------------------------------------------------------------------
# Identity-like laws
# ---------------------------------------------------------------------------


class TestIdentityLaws(unittest.TestCase):

    def test_self_extend_prefer_self_preserves_registries(self):
        s = _active()
        out = s.extend(s, on_conflict=ConflictPolicy.PREFER_SELF)
        self.assertTrue(_registries_equal(out, s))

    def test_self_extend_prefer_other_preserves_registries(self):
        s = _active()
        out = s.extend(s, on_conflict=ConflictPolicy.PREFER_OTHER)
        self.assertTrue(_registries_equal(out, s))

    def test_unfiltered_restrict_preserves_registries(self):
        s = _active()
        out = s.restrict()
        self.assertTrue(_registries_equal(out, s))


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


class TestSelfExtendIdempotence(unittest.TestCase):

    def test_double_self_extend_prefer_self_equals_single(self):
        s = _active()
        once = s.extend(s, on_conflict=ConflictPolicy.PREFER_SELF)
        twice = once.extend(s, on_conflict=ConflictPolicy.PREFER_SELF)
        self.assertTrue(_registries_equal(once, twice))

    def test_double_self_extend_prefer_other_equals_single(self):
        s = _active()
        once = s.extend(s, on_conflict=ConflictPolicy.PREFER_OTHER)
        twice = once.extend(s, on_conflict=ConflictPolicy.PREFER_OTHER)
        self.assertTrue(_registries_equal(once, twice))


# ---------------------------------------------------------------------------
# Associativity
# ---------------------------------------------------------------------------


class TestExtendAssociativity(unittest.TestCase):
    """For disjoint subsystems, ``(a.extend(b)).extend(c)`` and
    ``a.extend(b.extend(c))`` must agree as registry contents.

    Disjointness is ensured by restricting to disjoint dimensions; that
    keeps the proof simple (no conflicts on units / base_units), so the
    associativity check is independent of the conflict policy.
    """

    def test_associativity_under_prefer_self_on_disjoint_subsystems(self):
        s = _active()
        a = _restrict_to(s, "length")
        b = _restrict_to(s, "mass")
        c = _restrict_to(s, "time")
        left = a.extend(b, on_conflict=ConflictPolicy.PREFER_SELF).extend(
            c, on_conflict=ConflictPolicy.PREFER_SELF
        )
        right = a.extend(
            b.extend(c, on_conflict=ConflictPolicy.PREFER_SELF),
            on_conflict=ConflictPolicy.PREFER_SELF,
        )
        self.assertTrue(_registries_equal(left, right))

    def test_associativity_under_prefer_other_on_disjoint_subsystems(self):
        s = _active()
        a = _restrict_to(s, "length")
        b = _restrict_to(s, "mass")
        c = _restrict_to(s, "time")
        left = a.extend(b, on_conflict=ConflictPolicy.PREFER_OTHER).extend(
            c, on_conflict=ConflictPolicy.PREFER_OTHER
        )
        right = a.extend(
            b.extend(c, on_conflict=ConflictPolicy.PREFER_OTHER),
            on_conflict=ConflictPolicy.PREFER_OTHER,
        )
        self.assertTrue(_registries_equal(left, right))


# ---------------------------------------------------------------------------
# Restrict monotonicity
# ---------------------------------------------------------------------------


class TestRestrictMonotonicity(unittest.TestCase):
    """``s.restrict(dimensions=D).subsystem_of(s)`` for any ``D ⊆ s.dimensions``."""

    def test_single_dimension_restriction_is_subsystem(self):
        s = _active()
        for name in ("length", "mass", "time"):
            with self.subTest(dimension=name):
                r = _restrict_to(s, name)
                self.assertTrue(r.subsystem_of(s))

    def test_pairwise_dimension_restriction_is_subsystem(self):
        s = _active()
        pairs = [("length", "mass"), ("length", "time"), ("mass", "time")]
        for left, right in pairs:
            with self.subTest(dimensions=(left, right)):
                r = s.restrict(
                    dimensions=[s.dimensions[left], s.dimensions[right]]
                )
                self.assertTrue(r.subsystem_of(s))

    def test_unfiltered_restrict_is_subsystem(self):
        s = _active()
        self.assertTrue(s.restrict().subsystem_of(s))

    def test_unit_filter_restriction_is_subsystem(self):
        s = _active()
        r = s.restrict(units=["meter"])
        self.assertTrue(r.subsystem_of(s))


# ---------------------------------------------------------------------------
# Restrict / extend round-trip on disjoint partition
# ---------------------------------------------------------------------------


class TestRestrictExtendPartition(unittest.TestCase):
    """Restricting on a disjoint pair of dimensions and re-extending must
    recover (at least) the unit and base-unit contributions of both
    halves. This is the closest practical analogue of an identity element
    in v1.x ``BaseUnits``, which forbids an empty bases mapping.
    """

    def test_length_mass_partition_recovers_both(self):
        s = _active()
        length_only = _restrict_to(s, "length")
        mass_only = _restrict_to(s, "mass")

        merged = length_only.extend(mass_only, on_conflict=ConflictPolicy.PREFER_SELF)

        # Unit names from both halves are present.
        self.assertTrue(
            set(length_only.units.keys()) <= set(merged.units.keys())
        )
        self.assertTrue(
            set(mass_only.units.keys()) <= set(merged.units.keys())
        )
        # Dimensions from both halves are present.
        self.assertIn("length", merged.dimensions)
        self.assertIn("mass", merged.dimensions)
        # base_units covers both dimensions.
        merged_base_dims = {d.name for d in merged.base_units.bases.keys()}
        self.assertIn("length", merged_base_dims)
        self.assertIn("mass", merged_base_dims)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Composable Unit Systems
=======================

``UnitSystem`` is an immutable value. Every algebraic operation returns
a new ``UnitSystem``; the input survives. ``use(system)`` makes one
active for a scope via a single ``ContextVar`` payload — no module
globals, no locks.

This walkthrough covers, in order:

  1. ``active_system()`` and ``use(...)`` — scoped activation
  2. ``extend`` with ``ConflictPolicy``        — union with policy
  3. ``restrict``                              — filter down
  4. ``merge`` with a callable resolver        — collision-by-callback
  5. ``with_unit`` / ``with_conversion``       — incremental construction
  6. ``subsystem_of`` / ``compatible_with`` / ``diff`` — relations
  7. ``adopt``                                 — synonym-bind values
  8. ``Bridge``                                — when names diverge
  9. Algebraic laws as ``assert`` statements

Run:

    python composition.py
"""

from __future__ import annotations

import ucon
from ucon import (
    Bridge,
    ContextEdge,
    Number,
    Unit,
    use,
)
from ucon.maps import LinearMap
from ucon.system import ConflictPolicy, ExtendConflict


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------------------
# 1. active_system() and use(...) — scoped activation
# ---------------------------------------------------------------------------

def demo_active_and_use() -> None:
    section("1. active_system() and use(...)")

    base = ucon.active_system()
    print(f"active system has {len(base.units)} units and "
          f"{len(base.dimensions)} dimensions")

    # use(system) pushes a frozen ActiveContext onto a ContextVar and
    # restores the previous one on exit. Nothing leaks past the block.
    inner = base.restrict(units=["meter", "second"])
    with use(inner):
        print(f"  inside use(inner): {len(ucon.active_system().units)} units")
    print(f"  outside:           {len(ucon.active_system().units)} units")


# ---------------------------------------------------------------------------
# 2. extend with ConflictPolicy
# ---------------------------------------------------------------------------

def demo_extend() -> None:
    section("2. extend(other, on_conflict=...)")

    base = ucon.active_system()

    # extend unions every registry. Identical entries on both sides are
    # accepted silently. Non-equal entries on the same key are governed
    # by `on_conflict`.
    same = base.extend(base)
    assert same.subsystem_of(base) and base.subsystem_of(same)
    print("  base.extend(base) == base (subsystem in both directions)")

    # Conflict scenario: an "alternative" system that disagrees on the
    # definition of meter. Unit equality keys on (name + aliases +
    # dimension), so a different alias tuple is enough to force a
    # genuine non-equal collision.
    foreign_meter = Unit(
        name="meter",
        dimension=base.units["meter"].dimension,
        aliases=("m_alt",),
    )
    foreign_meter._set_base_form(base.units["meter"].base_form)
    alt = base.restrict(units=["second"]).with_unit(foreign_meter)

    try:
        base.extend(alt, on_conflict=ConflictPolicy.RAISE)
    except ExtendConflict as e:
        print(f"  RAISE       → ExtendConflict on {e.registry!r}/{e.key!r}")

    prefer_self = base.extend(alt, on_conflict=ConflictPolicy.PREFER_SELF)
    print(f"  PREFER_SELF → meter aliases = {prefer_self.units['meter'].aliases}")

    prefer_other = base.extend(alt, on_conflict=ConflictPolicy.PREFER_OTHER)
    print(f"  PREFER_OTHER→ meter aliases = {prefer_other.units['meter'].aliases}")


# ---------------------------------------------------------------------------
# 3. restrict — filter down
# ---------------------------------------------------------------------------

def demo_restrict() -> None:
    section("3. restrict(dimensions=..., units=...)")

    base = ucon.active_system()
    length = base.dimensions["length"]
    mass = base.dimensions["mass"]

    # Either filter may be None. Both filters compose: a unit survives
    # only if both admit it.
    physics_starter = base.restrict(
        dimensions=[length, mass],
        units=["meter", "kilogram", "foot"],
    )
    kept = sorted(physics_starter.units.keys())
    print(f"  starter system kept: {kept}")

    # The conversion graph is filtered to edges whose endpoints survive.
    n = Number(1.0, physics_starter.units["meter"])
    with use(physics_starter):
        print(f"  1 m as ft: {n.to('foot').quantity:.5f}")


# ---------------------------------------------------------------------------
# 4. merge with a callable resolver
# ---------------------------------------------------------------------------

def demo_merge() -> None:
    section("4. merge(other, resolver)")

    base = ucon.active_system()

    # Construct two systems that disagree on a single unit name, then
    # let the resolver decide.
    rhs_meter = Unit(
        name="meter",
        dimension=base.units["meter"].dimension,
        aliases=("m_rhs",),
    )
    rhs_meter._set_base_form(base.units["meter"].base_form)
    rhs = base.restrict(units=["second"]).with_unit(rhs_meter)

    calls: list[tuple[Unit, Unit]] = []

    def prefer_more_aliases(a: Unit, b: Unit) -> Unit:
        calls.append((a, b))
        return a if len(a.aliases) >= len(b.aliases) else b

    merged = base.merge(rhs, prefer_more_aliases)
    print(f"  resolver invoked {len(calls)} time(s)")
    print(f"  result: meter aliases = {merged.units['meter'].aliases}")


# ---------------------------------------------------------------------------
# 5. with_unit / with_conversion — incremental construction
# ---------------------------------------------------------------------------

def demo_with_unit_and_conversion() -> None:
    section("5. with_unit / with_conversion")

    base = ucon.active_system()
    meter = base.units["meter"]

    # Synonym Unit: same dimension, same base_form. Useful for naming
    # conventions ("metre" vs "meter").
    metre = Unit(name="metre", dimension=meter.dimension)
    metre._set_base_form(meter.base_form)

    extended = base.with_unit(metre)
    print(f"  metre is now defined: {'metre' in extended.units}")

    # with_conversion adds an edge to the conversion graph. The inverse
    # is registered automatically.
    edge = ContextEdge(
        src=metre,
        dst=meter,
        map=LinearMap(a=1.0),
    )
    with_edge = extended.with_conversion(edge)
    n = Number(1.0, with_edge.units["metre"])
    with use(with_edge):
        print(f"  1 metre -> meter = {n.to('meter').quantity}")


# ---------------------------------------------------------------------------
# 6. Relations: subsystem_of / compatible_with / diff
# ---------------------------------------------------------------------------

def demo_relations() -> None:
    section("6. Relations: subsystem_of / compatible_with / diff")

    base = ucon.active_system()
    sub = base.restrict(units=["meter", "second"])

    print(f"  sub.subsystem_of(base) = {sub.subsystem_of(base)}")
    print(f"  base.subsystem_of(sub) = {base.subsystem_of(sub)}")
    print(f"  base.compatible_with(sub) = {base.compatible_with(sub)}")

    d = base.diff(sub)
    print(f"  base->sub diff: {len(d.units.removed)} units removed, "
          f"{len(d.units.added)} added, "
          f"{len(d.units.redefined)} redefined")


# ---------------------------------------------------------------------------
# 7. adopt — synonym-bind values
# ---------------------------------------------------------------------------

def demo_adopt() -> None:
    section("7. system.adopt(n)")

    base = ucon.active_system()
    sub = base.restrict(units=["meter"])

    # adopt rebinds n.unit to point at sub's Unit object. It performs
    # no conversion math; the quantity is unchanged.
    n = Number(5.0, base.units["meter"])
    moved = sub.adopt(n)
    print(f"  n.unit is base.units['meter']: {n.unit is base.units['meter']}")
    print(f"  moved.unit is sub.units['meter']: {moved.unit is sub.units['meter']}")
    print(f"  moved.quantity unchanged: {moved.quantity}")


# ---------------------------------------------------------------------------
# 8. Bridge — when names diverge (or bases differ)
# ---------------------------------------------------------------------------

def demo_bridge() -> None:
    section("8. Bridge(src, dst, rename=...)")

    base = ucon.active_system()
    meter = base.units["meter"]

    # Build a destination system that has "metre" as a synonym.
    metre = Unit(name="metre", dimension=meter.dimension)
    metre._set_base_form(meter.base_form)
    dst = base.with_unit(metre)

    # rename is synonym-only: both endpoints must agree on dimension
    # and base_form. Definitional differences must go through a
    # basis_transform or a custom conversion edge.
    bridge = Bridge(src=base, dst=dst, rename={"meter": "metre"})

    n = Number(5.0, base.units["meter"])
    moved = bridge.apply(n)
    print(f"  applied: {moved.quantity} {moved.unit.name}")
    print(f"  result.unit is dst.units['metre']: "
          f"{moved.unit is dst.units['metre']}")

    # Bridges compose with the @ operator; inverse() returns dst → src.
    round_trip = (bridge.inverse() @ bridge).apply(n)
    print(f"  inverse(bridge) @ bridge applied to n: "
          f"{round_trip.quantity} {round_trip.unit.name}")


# ---------------------------------------------------------------------------
# 9. Algebraic laws
# ---------------------------------------------------------------------------

def demo_laws() -> None:
    section("9. Algebraic laws")

    base = ucon.active_system()
    length = base.dimensions["length"]
    length_meters = base.restrict(units=["meter"])
    length_feet = base.restrict(units=["foot"])
    length_inches = base.restrict(units=["inch"])

    # Idempotence (up to subsystem-equivalence of registries).
    assert base.extend(base).subsystem_of(base)
    assert base.subsystem_of(base.extend(base))
    print("  extend is idempotent up to ==")

    # Associativity, demonstrated on length-only subsystems.
    left = length_meters.extend(length_feet).extend(length_inches)
    right = length_meters.extend(length_feet.extend(length_inches))
    assert left.subsystem_of(right) and right.subsystem_of(left)
    print("  extend is associative")

    # Restrict commutes with extend on the kept names.
    names = frozenset({"meter", "foot"})
    length_only = base.restrict(dimensions=[length])
    lhs = length_only.extend(length_feet).restrict(units=names)
    rhs = length_only.restrict(units=names).extend(length_feet.restrict(units=names))
    assert sorted(lhs.units) == sorted(rhs.units)
    print("  restrict(extend(a, b)) == extend(restrict(a), restrict(b)) on shared names")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    demo_active_and_use()
    demo_extend()
    demo_restrict()
    demo_merge()
    demo_with_unit_and_conversion()
    demo_relations()
    demo_adopt()
    demo_bridge()
    demo_laws()


if __name__ == "__main__":
    main()

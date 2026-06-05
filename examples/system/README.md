# Composable Unit Systems

A runnable walkthrough of the v2.0 `UnitSystem` algebra: composition,
restriction, merging, incremental construction, relations, and explicit
cross-system value movement.

## Overview

`UnitSystem` is an immutable value. Every algebraic operation returns a new
`UnitSystem`; the input survives. `use(system)` activates one for a scope via
a single `ContextVar` payload — no module-global state, no locks.

This example shows:

1. **Scoped activation** — `active_system()` / `use(...)`
2. **Union with policy** — `extend(other, on_conflict=ConflictPolicy.*)`
3. **Filter down** — `restrict(dimensions=..., units=...)`
4. **Callable conflict resolution** — `merge(other, resolver)`
5. **Incremental construction** — `with_unit(...)` / `with_conversion(...)`
6. **Relations** — `subsystem_of`, `compatible_with`, `diff`
7. **Synonym-bind values across systems** — `system.adopt(n)`
8. **Sanctioned divergence** — `Bridge(src, dst, rename=..., basis_transform=...)`
9. **Algebraic laws** — idempotence, associativity, restrict/extend factoring

## Files

- `composition.py` — Single self-contained script; each demo is its own
  function and prints a banner before running.

## Usage

```bash
python composition.py
```

No external configuration. The script derives every demo system from
`ucon.active_system()`.

## Example Output

```
========================================================================
1. active_system() and use(...)
========================================================================
active system has 234 units and 92 dimensions
  inside use(inner): 2 units
  outside:           234 units

========================================================================
2. extend(other, on_conflict=...)
========================================================================
  base.extend(base) == base (subsystem in both directions)
  RAISE       → ExtendConflict on 'units'/'meter'
  PREFER_SELF → meter aliases = ('m', 'meters', 'metres', 'metre')
  PREFER_OTHER→ meter aliases = ('m_alt',)

...

========================================================================
9. Algebraic laws
========================================================================
  extend is idempotent up to ==
  extend is associative
  restrict(extend(a, b)) == extend(restrict(a), restrict(b)) on shared names
```

## Key Patterns

### Scoped activation

```python
with use(ucon.active_system().extend(medical_package)):
    dose = parse("5 mg/kg")  # medical units active here only
```

### Compose

```python
combined = base.extend(medical).extend(thermo)                  # raises on conflict
relaxed  = base.extend(other, on_conflict=ConflictPolicy.PREFER_OTHER)
custom   = base.merge(other, resolver=lambda a, b: pick(a, b))  # callback decides
```

### Restrict

```python
physics_101 = base.restrict(
    dimensions=[LENGTH, TIME, MASS],
    units=["meter", "second", "kilogram", "foot", "inch"],
)
```

A unit survives only if **both** filters admit it. The conversion graph is
filtered to edges whose endpoints survive.

### Move values across systems

```python
# Same names, structurally compatible — identity rebind, no math:
moved = sub.adopt(n)

# Names diverge or basis differs — explicit bridge:
b = Bridge(src=base, dst=other, rename={"meter": "metre"})
moved = b.apply(n)
round_trip = (b.inverse() @ b).apply(n)
```

`rename` is **synonym-only**: both endpoints must share dimension and base form.
Definitional differences must go through a `basis_transform` or a custom
conversion edge — those cases are rejected at `Bridge` construction with
`InvalidRename`.

### Algebraic laws

```python
# Idempotence:
base.extend(base) == base

# Associativity:
a.extend(b).extend(c) == a.extend(b.extend(c))

# Restrict / extend commute on the kept names:
extend(a, b).restrict(names) == extend(a.restrict(names), b.restrict(names))
```

## See Also

- [`docs/guides/`](https://docs.ucon.dev/guides/) — broader v2.0 guides
- [`ROADMAP.md`](../../ROADMAP.md) — v2.0 milestone entry
- `tests/ucon/system/test_algebra*.py`, `test_relations.py`,
  `test_adopt.py`, `test_bridge.py` — regression suite

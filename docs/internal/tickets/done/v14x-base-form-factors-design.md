# Ticket: v1.4.x `BaseForm.factors` reference model

**Status:** Open (design question, no implementation)
**Raised in:** v1.3.0 session, 2026-04-08
**Relates to:** v1.4.0 "TOML-as-truth" shift; retirement of `scripts/generate_base_forms.py` BFS oracle

---

## Context

v1.3.0 added TOML serialization of `Unit.base_form` via a two-pass deserializer
(`ucon/serialization.py`) that relies on `Unit._set_base_form`, a sanctioned
post-construction mutation point added to `ucon/core.py`.

`_set_base_form` currently has **two** callers:

1. **`ucon/units.py:89-96` — SI bootstrap**
   Eight self-referential calls for the coherent SI base units
   (`kilogram`, `meter`, `second`, `ampere`, `kelvin`, `candela`, `mole`,
   `bit`). These exist because a coherent base unit's `base_form` is
   the fixed point `1 U ≡ 1.0 × U^1`, and `BaseForm.factors` stores
   `Unit` references — so the Unit must exist before its own
   `BaseForm` can be constructed. The `base_form=` constructor kwarg
   literally cannot express the self-reference.

2. **`ucon/serialization.py` — pass-2 deserializer**
   Resolves forward references in `[[units.base_form.factors]]` entries
   after all units have been constructed in pass 1.

During the v1.3.0 session the 8 bootstrap lines were flagged as a code
smell: `units.py` reads like a definitional manifest, and having 8 lines
of post-construction mutation at the top forces readers to stop and ask
"why are we mutating a frozen dataclass here?"

## The v1.4.0 observation

The v1.4.0 roadmap includes shifting to **TOML-as-truth**: the default
unit registry will be loaded from a TOML file (likely
`examples/units/comprehensive.ucon.toml` promoted to a first-class
asset), and `ucon/units.py` will shrink to a loader shim. When that
happens, caller (1) disappears entirely — the 8 SI bases are declared
in TOML alongside everything else, and the deserializer handles their
self-reference via the same pass-1/pass-2 machinery it already uses for
forward references.

**BUT:** caller (2) does **not** disappear. The self-reference problem
isn't "Python literals can't express fixed points" — it's "any
serialization format where units are defined in order and
`BaseForm.factors` stores `Unit` references has the same
construction-order problem." Moving the source of truth from Python
to TOML relocates the 8 calls into a loop inside the deserializer; it
does not eliminate `_set_base_form`.

After the TOML-as-truth shift, `_set_base_form` becomes a **private
implementation detail of `ucon.serialization`**, invisible to anyone
reading `ucon/units.py` — the actual smell vanishes even though the
method survives.

## The open design question

**Should `BaseForm.factors` continue to store `Unit` references, or
should it store names (strings) + a resolver?**

This is the only change that would eliminate `_set_base_form` entirely
(including from the deserializer). It is orthogonal to TOML-as-truth
— either change can be made without the other — but v1.4.0 is a
natural time to decide, since we're already revisiting how units are
loaded.

### Option A — Keep Unit references (status quo + deserializer-only `_set_base_form`)

```python
@dataclass(frozen=True)
class BaseForm:
    factors: tuple[tuple[Unit, float], ...]
    prefactor: float = 1.0
```

**Pros:**
- Object identity: `bf.factors[0][0] is kilogram` holds for anyone
  walking the graph.
- Zero lookup cost in hot paths (`graph.convert`, `Number.to`,
  drift-check walks).
- Minimal churn: v1.3.0 machinery carries forward unchanged;
  `_set_base_form` stays as a single-caller private helper.

**Cons:**
- `_set_base_form` survives (but confined to the deserializer).
- Two-pass deserialization is still required.
- Any future serialization format has to carry the same two-pass baggage.

### Option B — Store names + resolver

```python
@dataclass(frozen=True)
class BaseForm:
    factors: tuple[tuple[str, float], ...]
    prefactor: float = 1.0

    def resolve(self, registry) -> tuple[tuple[Unit, float], ...]:
        return tuple((registry[name], exp) for name, exp in self.factors)
```

**Pros:**
- `_set_base_form` can be deleted entirely.
- `BaseForm` becomes truly immutable with no back-door mutation path.
- Single-pass deserialization; construction order becomes irrelevant.
- `BaseForm` is fully serializable on its own without a Unit graph.

**Cons:**
- Loses object identity on factor lookup: every access must go through
  a registry (global, passed-in, or stored on `BaseForm`).
- Adds a resolution step to every factor walk — potential hot-path
  cost in `graph.convert`, `Number.to`, `UnitProduct` decomposition.
- Requires a resolver context everywhere factors are used; threading
  a registry through the call graph is non-trivial.
- Changes `BaseForm` equality and hashing semantics (name-based vs
  identity-based).
- Ripples into any code that does `for u, exp in bf.factors:` expecting
  `u` to be a `Unit` — non-trivial audit.
- Pickling / inter-process sharing becomes subtly harder (which
  registry does a given `BaseForm` resolve against?).

### Option C — Hybrid: store references, allow lazy resolution from names

`BaseForm.factors` stores `Unit | str`, lazily resolved on first access
via `__post_init__` or a cached property. Gets worst of both worlds
(mutation at first access + still need resolver context). **Not
recommended** — listed for completeness.

## Recommendation (tentative, for v1.4.0 discussion)

**Option A** — keep Unit references. The cost of Option B is ripple
through the graph walker and `Number.to` hot path; the benefit is
deleting one private helper that, post TOML-as-truth, nobody outside
`ucon.serialization` ever sees. Not worth the churn unless a second
motivation surfaces (e.g., cross-process BaseForm sharing, pure-data
BaseForm use cases).

If this recommendation stands, the v1.4.0 work is:

1. Promote `comprehensive.ucon.toml` (or equivalent) to the default
   registry source.
2. Delete `ucon/units.py:81-96` (the 8 SI bootstrap lines + comment
   block).
3. Delete the `_self_base` helper.
4. Add a docstring to `Unit._set_base_form` clarifying it is now
   called only from the deserializer.
5. Retire `scripts/generate_base_forms.py` (already planned) — once
   TOML is the source of truth, there is nothing to drift against.
6. Remove the `base_forms` CI job from `.github/workflows/tests.yaml`
   (added in v1.3.0, scheduled for retirement alongside the drift
   script).

If Option B wins instead, add to the above:

7. Change `BaseForm.factors` type signature to `tuple[tuple[str, float], ...]`.
8. Audit every `bf.factors` consumer (`graph.py`, `quantity.py`,
   `serialization.py`, `units.py`, tests) for identity assumptions.
9. Decide on the registry-threading mechanism (global, context-manager,
   explicit parameter).
10. Delete `Unit._set_base_form` and the pass-2 block in the deserializer.

## Decision

**Deferred to v1.4.0 planning.** This ticket captures the question so
it isn't lost between releases. No implementation work should happen
on v1.3.x against this ticket.

## References

- v1.3.0 CHANGELOG entries for `Unit._set_base_form` and TOML
  `base_form` serialization
- `ucon/core.py` — `Unit._set_base_form` implementation
- `ucon/units.py:81-96` — the 8 bootstrap lines
- `ucon/serialization.py` — pass-2 deserializer (`FORMAT_VERSION = "1.3"`)
- `scripts/generate_base_forms.py` — BFS oracle drift checker, scheduled
  for retirement in v1.4.0

---

## Closure Note (2026-07-12)

**Closed: decided by events — Option A (keep Unit references).** The
TOML-as-truth shift shipped: `ucon/comprehensive.ucon.toml` is the
authoritative catalog (see v2.0.0 CHANGELOG, "TOML authoritative for
Dimensions" / cache-first loading). `_set_base_form` survives confined to
`ucon/serialization.py` and `ucon/_cache.py` (plus its definition in
`ucon/core/_types.py`) — exactly the outcome this ticket's tentative
recommendation described: the smell vanished from the definitional manifest
while the private helper remains a deserializer implementation detail. No
second motivation for Option B (names + resolver) has surfaced.

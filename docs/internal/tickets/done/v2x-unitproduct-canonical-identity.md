# Ticket: UnitProduct Canonical Identity

**Priority:** High
**Theme:** Unit algebra / v2 structural cleanup
**Version:** v2.0
**Status:** Open
**Source:** `docs/internal/DESIGN_NOTE_residual-scale-machinery.md`; related: `docs/internal/unitsafe_100_blockers.md` (item 1)
**Branch target:** post-merge of `number-declares-kind`

---

## Summary

Give the Units group its multiplicative identity element by treating `UnitProduct(factors={}, canonical_scale=s)` as a first-class canonical form rather than an edge case the algebra works around. Retire the `_residual_scale_factor` side-channel and the `_none` sentinel. Introduce no module-level globals, no singletons, no `is`-checks. The constructor is the canonicalizer; idempotence is structural.

Unblocks UnitSafe item 1 (the orphan `ea` placeholder in MCP server output, downstream of `ucon-tools` swapping `"ea"` for the canonical identity). Sets up the Kind layer to carry provenance distinctions that the Unit layer currently smuggles through `_none`.

---

## Motivation

The codebase compensates for the absence of a proper multiplicative identity across roughly 23 callsites and ~1,850 lines. The compensation has three architectural costs:

1. **Information loss masquerading as algebra.** `UnitProduct.__init__` filters out factors whose dimension is `NONE` (`_types.py:945`), then reintroduces the lost scale via a side-channel field `_residual_scale_factor`. The two halves of the dual representation must be kept in sync at every arithmetic site, which they have not always been (see `v07x-scaled-unit-cancellation-bug.md`).

2. **Provenance leakage between layers.** The `_none = Unit()` sentinel at `_types.py:1379` serves both as "user passed no unit" and "units cancelled to dimensionless." The first concern belongs at the Kind layer (per `ARCHITECTURE_number-kind-v6.md` P8: one discrimination mechanism per distinction); conflating them blocks the apples-vs-oranges discrimination work.

3. **Special-case branching that obscures intent.** Empty `UnitProduct`s trigger fallbacks (`or "1"`) and gated rendering (`if self.unit.dimension:`) at every point where the algebra produces or inspects them. None of these branches would exist if the empty product were a legitimate canonical form with explicit semantics.

The full inventory is documented in `DESIGN_NOTE_residual-scale-machinery.md`. This ticket implements the structural fix that retires the compensations.

---

## Non-goals

- **No `one` object.** The empty `UnitProduct` is the identity. Introducing a separately-named `one` `Unit` would add a module-level singleton for no algebraic benefit and would violate v2's no-new-globals directive.
- **No public API additions.** Nothing new is exported from `ucon/__init__.py`. The empty `UnitProduct` is already constructible by anyone who wants it.
- **No kind-layer changes.** The apples-vs-oranges discrimination is a separate slice. This ticket only clears the path for it.
- **No conversion-graph changes.** The graph operates on canonical UnitProducts post-construction; behavior is preserved.

---

## Canonical form contract

A `UnitProduct` is canonical when:

1. `factors` contains no factor with `dimension == NONE`.
2. `factors` contains no factor with exponent `0`.
3. `factors` contains at most one entry per `(unit_name, dimension)` group. Multiple-scale variants are resolved via existing Step 4 logic; absorbed scale contributions compose into `canonical_scale`.
4. `canonical_scale` is `1.0` whenever `factors` is non-empty. Non-1.0 `canonical_scale` is permitted only on fully-cancelled dimensionless products.

The constructor `UnitProduct.__init__` is the canonicalizer. Idempotence is structural: `UnitProduct(u.factors, u.canonical_scale) == u` for every canonical `u`.

Equality is structural over `(factors, canonical_scale)`. No `is`-checks, no singletons, no identity dispatch.

---

## Implementation phases

Each phase is a single independently-bisectable commit.

### Phase 1 — Rename `_residual_scale_factor` to `canonical_scale`

**Scope:** mechanical rename across the 23 sites inventoried in `DESIGN_NOTE_residual-scale-machinery.md §3`.

- `ucon/core/_types.py`: 5 direct assignments + 10 compound mutations (§3.1).
- `ucon/parsing/units.py`: 2 propagation sites (§3.1).
- `getattr(..., '_residual_scale_factor', 1.0)` → direct field access. Default stays `1.0`.
- Tests: any test that references `_residual_scale_factor` updates to `canonical_scale`.

**Behavior change:** none. Pure rename.

**Acceptance:** full test suite passes unchanged; `grep -r _residual_scale_factor` returns no hits.

### Phase 2 — Tighten the canonical contract

**Scope:** enforce the §"Canonical form contract" invariants in `UnitProduct.__init__`.

- Add the four canonical-form invariants as assertions (or quiet enforcement) inside `__init__`.
- Replace the `NONE`-dimension filter at `_types.py:945` with absorption: dimensionless factors compose into `canonical_scale` and are removed from `factors`. Same effect as today, but framed as canonicalization rather than discarding.
- Add an idempotence property test: for a sampling of arithmetically-constructed `UnitProduct`s `u`, assert `UnitProduct(u.factors, u.canonical_scale) == u` and that the §"Canonical form contract" invariants hold on the result.
- Add the algebraic identity tests: `u * UnitProduct({}) == u` and `u / u == UnitProduct(factors={}, canonical_scale=1.0)` for representative units.

**Behavior change:** none observable. The contract becomes explicit; the existing implementation already satisfies it (modulo §6.4 sentinel removal in Phase 3).

**Acceptance:** all property tests pass; existing test suite passes.

### Phase 3 — Retire the `_none` sentinel

**Scope:** delete the masquerade.

- Remove `_none = Unit()` at `_types.py:1379`.
- Remove the re-export from `ucon/quantity.py:10`.
- Update `Number.__post_init__` (`_types.py:1432`): if `unit is None`, normalize to `UnitProduct(factors={})`. If `unit` is a `Unit`, leave as-is (Unit can stay as the elementary type; only the empty-as-sentinel role disappears).
- Update `Number.__repr__` (`_types.py:2156-2157`): replace the dimension-truthiness gate with an explicit canonical-form check ("render `self.unit.shorthand` unless the canonical form is `UnitProduct(factors={}, canonical_scale=1.0)`").
- Update `Number.__truediv__` Case 1 (`_types.py:2089-2092`): return `Number(quantity=result, unit=UnitProduct({}), ...)` instead of `_none`.
- Update `Ratio.evaluate` Case 1 (`_types.py:2199`): same substitution.
- Update `ucon/integrations/pydantic.py:120, 136`: the fallback `... if n.unit else Dimension.none` becomes unnecessary because `unit` is always a canonical value after Phase 1+2.

**Behavior change:** observable only at the level of `unit is _none` checks in downstream code. No such checks exist inside `ucon`; external callers using `from ucon.quantity import _none` will need to migrate to `unit == UnitProduct({})` (structural) or test `n.unit.factors == {} and n.unit.canonical_scale == 1.0` (explicit).

**Acceptance:** full test suite passes; the audit at `tests/ucon/test_no_cross_module_injection.py` continues to pass; no public symbol is added or removed.

### Phase 4 — Retire compensation sites

**Scope:** the special-case branches that exist because empty `UnitProduct` was anomalous.

- `UnitProduct.shorthand` (`_types.py:1056-1075`): replace `numerator or "1"` with an explicit check for the canonical empty form; render `"1"` once, in one place.
- `_ScaleDescriptor.__repr__` (`_types.py:200`): same.
- Legacy `_ucon/core.py:353` (if still active): same.
- `parsing/units.py:173-177`: delete the bare-`"1"` parser branch; `"1"` resolves to `UnitProduct({})` through normal construction.
- `parsing/units.py:213-216, 237-241`: collapse the conditional propagation tail (`if left_residual != 1.0 or right_residual != 1.0: ...`) to unconditional composition, since `canonical_scale` is always present.

**Behavior change:** none observable. Implementation simplification.

**Acceptance:** test suite passes; line count in affected modules decreases by ~40–60.

---

## Acceptance criteria (whole ticket)

The ticket lands when:

1. All four phases pass `make test` independently.
2. `make stubs-check` and `make base-forms-check` pass after each phase.
3. The following property tests exist and pass:
   - **Identity:** for representative `Unit` instances `u`, `Unit(u) * UnitProduct({}) == Unit(u)`.
   - **Self-cancellation:** for the same `u`, `Unit(u) / Unit(u) == UnitProduct(factors={}, canonical_scale=1.0)`.
   - **Idempotence:** for arithmetically-constructed `UnitProduct`s `p`, `UnitProduct(p.factors, p.canonical_scale) == p`.
   - **Canonical-form invariants:** for any `p` returned by `__init__`, the four conditions in §"Canonical form contract" hold.
4. The regression suite from `v07x-scaled-unit-cancellation-bug.md` (nursing dosage, `mg/kg` cancellation) continues to produce correct numeric results.
5. `grep -r _residual_scale_factor ucon/ tests/` returns no hits.
6. `grep -r '_none' ucon/ tests/` returns no hits (excluding `_canonical_*` or other unrelated identifiers).
7. No new module-level bindings introduced. The static AST audit at `tests/ucon/test_no_cross_module_injection.py` passes unchanged.
8. `ucon/__init__.py` exports are unchanged.

---

## Risk and mitigation

| Risk | Mitigation |
|---|---|
| External callers depend on `from ucon.quantity import _none` | CHANGELOG entry under "Removed"; cite the migration path (`UnitProduct({})` or `n.unit.factors == {}`). Phase 3 lands the rename first, the removal second, so deprecation can interleave if needed. |
| Hidden `_residual_scale_factor` reads outside the inventoried 23 sites | Phase 1's `grep` acceptance criterion catches them. Phase 1 is pure rename; any miss surfaces as a test failure with a clear name resolution error. |
| The empty-product equality semantic differs subtly from `_none` equality today | Existing tests pin the user-visible behavior. Phase 3's `Number.__eq__` paths should produce identical truth tables; any divergence is itself a bug worth catching. |
| Phase 2's stricter invariants reject UnitProducts that today are tolerated | Run Phase 2 as quiet enforcement (no assertion error, just normalization) for one release; convert to assertions in v2.1. Alternatively land assertions immediately and accept the failure surface as part of the v2 contract narrowing. Recommended: assertions immediately, since v2 is the contract-narrowing release. |
| Pydantic/Polars/Numpy integrations break on Phase 3 | Each integration's dimensionless-fallback logic (`pydantic.py:120, 136` confirmed; check polars and numpy adapters during Phase 3) updates as part of the same commit. CI runs against all integrations. |
| Stub regeneration mismatches | `make stubs` after each phase; commit regenerated stubs in the same commit per the CLAUDE.md convention. |

---

## What this ticket explicitly does *not* address

- **The `_residual_scale_factor` algebra itself.** The numeric tracking is correct as designed; only the *representation* and the *contract* change. The mechanism for composing scales during cancellation (Step 4A and 4C) is preserved.
- **Pseudo-dimension handling.** `ANGLE`, `RATIO`, `COUNT`, `SOLID_ANGLE` branching in `Dimension.__mul__`/`__truediv__`/`__pow__`/`__bool__` is orthogonal and untouched.
- **Kind-aware arithmetic.** `Number.__add__`/`__sub__`/`__mul__`/`__truediv__` continue to drop `kind` to `None`. The apples-vs-oranges discrimination slice depends on this ticket landing but is its own work.
- **Conversion graph changes.** The graph consumes canonical `UnitProduct`s; its behavior is preserved.
- **`ucon-tools` placeholder swap.** Once this ticket ships, `ucon-tools/server.py:2249, 2342, 2348` can replace the `"ea"` literals with `"1"` (which parses to the canonical empty `UnitProduct`). That swap is a separate trivial commit in the downstream repo.

---

## References

- `docs/internal/DESIGN_NOTE_residual-scale-machinery.md` — full inventory and contract specification.
- `docs/internal/unitsafe_100_blockers.md` — item 1 motivation.
- `docs/internal/ARCHITECTURE_number-kind-v6.md` — Principle P8 (one discrimination mechanism per distinction); justifies moving provenance to the Kind layer.
- `docs/internal/tickets/done/v07x-scaled-unit-cancellation-bug.md` — the bug whose fix introduced `_residual_scale_factor`; the regression suite to preserve.
- `docs/internal/proposals/cancelled-unit-identity.md` — a separate proposal for recovering cancelled-unit identity; orthogonal to this ticket and may build on it.
- `CLAUDE.md` — "No new module-level mutable globals" directive; honored by this ticket.

---

## Closure Note (2026-07-12)

**Closed: landed in v2.0.0.** Verified against the codebase and CHANGELOG:
- Phase 1: `canonical_scale` rename shipped (`grep _residual_scale_factor
  ucon/` returns no hits; CHANGELOG entry "renamed from
  `_residual_scale_factor` ... public contract-bearing field").
- Phase 2: constructor absorbs dimensionless-factor scales and accepts the
  `canonical_scale` argument for idempotent reconstruction (CHANGELOG);
  covered by `tests/ucon/core/test_unitproduct_canonical.py`.
- Phase 3: `_none` sentinel removed (CHANGELOG "Removed: `_none` sentinel.
  Use `UnitProduct({})` instead"); `ucon/quantity.py` no longer re-exports it.
- Phase 4: compensation-site cleanup absorbed into the v2.0 core
  restructuring.

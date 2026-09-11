# Ticket: v1.3.1 ucon-tools foundation follow-ups

**Status:** Open
**Raised in:** v1.3.0 session, 2026-04-08
**Relates to:** ucon-tools downstream consumer; v1.3.0 reflection-API additions
(`Number.in_base_form`, `Number.same_dimension_as`, `*.base_signature`,
`ConversionGraph.add_edge` public-API promotion)

---

## Context

The v1.3.0 release shipped four foundation items (items 4–7 of an 8-item
audit) that move ucon toward a stable downstream surface for
**ucon-tools**:

* `Number.in_base_form` (predicate)
* `Number.same_dimension_as` (graph-free dimensional compatibility)
* `Unit.base_signature` / `UnitProduct.base_signature` /
  `Number.base_signature` (hashable sorted projection of `base_form.factors`)
* `ConversionGraph.add_edge` documented and marked semver-stable

The remaining four items were deferred so v1.3.0 could ship a focused
release; they are documented here so any subsequent session can pick
them up cold.

None of these items depend on each other. They can be implemented in
any order, or in parallel, in the same v1.3.1 release.

---

## Items

### Item 1 — Audit and add missing CGS↔SI cross-basis edges

**Tier:** data / catalog
**Estimated risk:** low (additive only)
**Files of interest:**
- `ucon/graph.py:1725-1788` — current cross-basis registrations
  (`graph.connect_systems(...)` blocks for CGS_TO_SI, SI_TO_CGS_ESU,
  SI_TO_CGS_EMU, SI_TO_NATURAL)
- `ucon/units.py` — CGS units (search for `dyne`, `erg`, `barye`,
  `poise`, `stokes`, `galileo`, `kayser`, `langley`, `phot`, `stilb`,
  `lambert`, `nit`, `gauss`, `maxwell`, `oersted`, etc.)

**Background.** ucon-tools failed conversion attempts during evals
indicated that several CGS units exist as `Unit` instances in
`ucon/units.py` but lack a registered cross-basis edge to their SI
counterpart. The exact list was not captured at the time the deferral
was made; it must be re-derived.

**How to find the gaps.** Two complementary approaches:

1. **Audit-by-construction.** For every `Unit` in `ucon/units.py`
   whose `dimension.vector.basis` is `Basis.CGS` (or CGS_ESU / CGS_EMU),
   check whether it appears as a `src` or `dst` in the
   `connect_systems(...)` blocks at `ucon/graph.py:1725-1788`. Anything
   missing is a candidate gap.
2. **Audit-by-eval.** Run the ucon-tools test suite (or
   `evals/scibench-koq-eval-derivation.md`-style chemeng / nursing
   evals) and collect every `ConversionNotFound` whose `src.basis !=
   dst.basis`. Each unique pair is a gap.

**Acceptance criteria:**
- [ ] GIVEN every CGS / CGS-ESU / CGS-EMU unit in `ucon/units.py`,
      WHEN `default_graph.convert(src=cgs_unit, dst=si_counterpart)` is
      called THEN it must succeed (or, for units without a defined
      SI counterpart, the gap must be explicitly justified in a
      comment).
- [ ] All new edges are registered inside the existing
      `connect_systems(...)` blocks at `ucon/graph.py:1730-1772`,
      keeping the per-basis grouping intact.
- [ ] Each new edge has a test in
      `tests/ucon/test_default_graph_conversions.py` (or a new
      `TestCgsToSiCoverage` class therein) that converts a sample
      quantity and asserts the canonical magnitude.
- [ ] `make base-forms-check` continues to pass.

### Item 2 — Verify the reyn → pascal_second edge

**Tier:** data / catalog
**Estimated risk:** trivial (verification only, may already be done)
**Files of interest:**
- `ucon/graph.py:1652` — `graph.add_edge(src=units.reyn, dst=units.pascal_second, map=LinearMap(6894.757))`
- `ucon/units.py:316` — `reyn = Unit(... base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -1.0)), prefactor=6894.757))`

**Background.** The original v1.3.0 audit listed "reyn → Pa·s edge" as
a Tier-1 gap. Subsequent inspection found the edge already exists at
`ucon/graph.py:1652`. This item is retained in case ucon-tools is
still seeing a `ConversionNotFound` for `reyn → pascal_second` despite
the registration — possibly due to an indirect routing problem
(`reyn → pascal_second → pascal*second`) or an alias-resolution issue.

**Acceptance criteria:**
- [ ] GIVEN `units.reyn(1).to(units.pascal_second)` THEN the result
      must equal `Number(6894.757, units.pascal_second)`.
- [ ] GIVEN `units.reyn(1).to(units.pascal * units.second)` THEN the
      result must equal `Number(6894.757, units.pascal * units.second)`
      (i.e., the indirect route via `pascal_second ↔ pascal*second`
      identity edge at `ucon/graph.py:1514` resolves correctly).
- [ ] If the conversion already works, close this item with a one-line
      note in the v1.3.1 CHANGELOG ("Verified `reyn → pascal_second`
      and `reyn → pascal*second` routing.") and remove the item from
      this ticket.

### Item 3 — Improved `ConversionNotFound` payload

**Tier:** diagnostics
**Estimated risk:** low (new fields, no behavioral change)
**Files of interest:**
- `ucon/graph.py:73-75` — current definition:

  ```python
  class ConversionNotFound(Exception):
      """Raised when no conversion path exists between units."""
      pass
  ```

- All `raise ConversionNotFound(...)` sites in `ucon/graph.py` (find
  with `Grep` for `raise ConversionNotFound`)

**Background.** ucon-tools and other downstream consumers catch
`ConversionNotFound` and need to surface helpful diagnostics to users
(or to LLM-driven retry loops). The current exception carries only a
free-form message string, so consumers must regex it to extract
src/dst/dimension/basis information.

**Proposed shape (preserving backwards compatibility):**

```python
@dataclass
class ConversionNotFound(Exception):
    src: Unit | UnitProduct
    dst: Unit | UnitProduct
    src_dimension: Dimension | None = None
    dst_dimension: Dimension | None = None
    src_basis: Basis | None = None
    dst_basis: Basis | None = None
    reason: str = ""              # human-readable; what was attempted
    nearest_path: tuple | None = None  # optional: shortest partial path

    def __str__(self) -> str:
        # Formatted message for backwards-compatible callers
        ...
```

The dataclass form must remain `Exception`-compatible (subclass via
`class ConversionNotFound(Exception)` and assign fields in
`__init__`) so existing `try: ... except ConversionNotFound as e:`
sites continue to work and `str(e)` continues to produce a useful
message.

**Acceptance criteria:**
- [ ] `ConversionNotFound` exposes `.src`, `.dst`, `.src_dimension`,
      `.dst_dimension`, `.src_basis`, `.dst_basis`, `.reason` as public
      attributes.
- [ ] Every `raise ConversionNotFound(...)` site in `ucon/graph.py` is
      updated to populate at least `src`, `dst`, and `reason`.
- [ ] `str(ConversionNotFound(src=..., dst=...))` continues to produce
      a single-line, informative message (regression-tested against
      the existing message format where reasonable).
- [ ] At least one test in `tests/ucon/test_graph_resolution.py`
      catches the exception and asserts on its structured fields
      (not on `str(e)`).
- [ ] No public API removed; the existing constructor signature
      `ConversionNotFound("message string")` continues to work for
      backwards compatibility (with `src`/`dst` defaulting to `None`).

**Open question.** Whether to compute `nearest_path` (BFS from `src`
truncated at the failure point). This is genuinely useful for
diagnostics but adds non-trivial cost on the failure path. **Default:**
omit `nearest_path` from v1.3.1; revisit if a downstream consumer asks
for it.

### Item 8 — Document `to_base` / `canonical_magnitude` as formula-author API

**Tier:** docs / public API stability
**Estimated risk:** trivial (doc-only)
**Files of interest:**
- `ucon/core.py:1473-1494` — `Number.canonical_magnitude` docstring
  (already informative; needs cross-reference and a "When to use" note)
- `ucon/core.py:1496-1597` — `Number.to_base` docstring (already
  informative; same)
- `docs/reference/api.md` (or equivalent mkdocs page) — needs a new
  section
- `docs/explainers/` — candidate location for a "Writing dimensionally
  safe formulas with ucon" guide

**Background.** v1.3.0 added `Number.to_base()` and
`Number.canonical_magnitude` as the two primary tools for formula
authors who want to write graph-free, dimensionally validated
calculations. The docstrings on each method are good in isolation
but there is no narrative documentation explaining:

1. *When to reach for `to_base()` vs `canonical_magnitude`*. Short
   answer: `to_base()` returns a `Number` (unit-safe composition);
   `canonical_magnitude` returns a `float` (interop boundary). The
   docstrings mention this but it's buried.
2. *The `n.to_base().quantity == n.canonical_magnitude` invariance*.
   Already documented per-method but not surfaced as a top-level
   property of the formula-author API.
3. *Interaction with `base_signature`* (also new in v1.3.0) for
   formula dispatch and pre-validation.
4. *Why neither method touches the conversion graph*. This is the key
   architectural property that makes them safe to use inside
   formula bodies that may run before the default graph is built
   (cold-start, subprocess isolation, etc.) — see
   `tests/ucon/test_base_form.py::TestNoGraphInit::test_cold_start_subprocess`.

**Acceptance criteria:**
- [ ] A new section in `docs/reference/api.md` (or a new page under
      `docs/explainers/`) titled "Writing formulas with ucon" or
      similar, that walks through the formula-author API surface
      with at least three worked examples (BMI, kinetic energy, drug
      dosing).
- [ ] Each of `Number.to_base`, `Number.canonical_magnitude`, and
      `Number.base_signature` carries a `See Also` block in its
      docstring linking to the new docs page.
- [ ] The docstring of `Number.to_base` includes an explicit
      "Stability" note matching the one added to
      `ConversionGraph.add_edge` in v1.3.0 (semver-stable as of
      v1.3.0, signature frozen).
- [ ] `mkdocs build --strict` continues to pass.
- [ ] No code changes (this is a doc-only item). If a code change is
      tempting (e.g., a `formula_safe` decorator), split it into a
      new ticket and leave this one doc-only.

---

## Why these were deferred

Items 4–7 were chosen for v1.3.0 because they all touch the same code
neighborhood (`ucon/core.py` `Unit` / `UnitProduct` / `Number`) and
ship together as a coherent reflection / introspection layer. Items
1–3 and 8 are independent of each other and of the v1.3.0 changes,
so deferring them costs nothing in terms of merge conflicts or
review surface. They were dropped purely to keep v1.3.0 focused.

## Out of scope for v1.3.1

The following are *not* part of this ticket and should be filed
separately if pursued:

* The `BaseForm.factors` reference-vs-name design question — see
  `docs/internal/tickets/v14x-base-form-factors-design.md`.
* Retirement of `scripts/generate_base_forms.py` and the
  `base_forms` CI job — already scheduled for v1.4.0 alongside the
  TOML-as-truth shift.
* A `formula_safe` decorator or any other code-level formula-author
  ergonomics — file as a new ticket if proposed.

## References

- `ucon/core.py` — `Unit.base_signature`, `Number.in_base_form`,
  `Number.same_dimension_as`, `Number.to_base`,
  `Number.canonical_magnitude` (all v1.3.0)
- `ucon/graph.py:73` — current `ConversionNotFound` definition
- `ucon/graph.py:1725-1788` — current cross-basis edge registrations
- `ucon/graph.py:1652` — current `reyn → pascal_second` edge
- `ucon/units.py:316` — `reyn` Unit definition with `base_form`
- `tests/ucon/test_default_graph_conversions.py` — natural home for
  Item 1 tests
- `tests/ucon/test_graph_resolution.py` — natural home for Item 3 tests
- `CHANGELOG.md` v1.3.0 entries — context for what just shipped

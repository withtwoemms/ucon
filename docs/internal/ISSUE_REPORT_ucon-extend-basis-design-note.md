# Design Note: `extend_basis` Phase 1 Disconnect

**Status:** discovered in field use · proposed for Phase 2
**Filed by:** sovereign potential demo build (econophysics study no. 1, no. 2)
**Date:** 2026-04-30
**Component:** `ucon.basis`, `ucon.dimensions`, `ucon.units`

## Summary

`extend_basis` succeeds at creating a session-scoped extended basis with new
fundamental components, but those components are not visible to either
`define_unit` or the dimension parser used by `define_quantity_kind`. This
forced the sovereign-potential demo to use `mass` (kilograms) as a stand-in
for currency throughout, producing a working but semantically dishonest
artifact. The workaround propagates through every flow, every σ, every
KOQ disambiguation warning — and obscures exactly the type of distinction
ucon is supposed to surface.

This note documents the concrete failure trace, the cost of the workaround,
and a Phase 2 design that wires extended-basis components through to the
parser and unit registry. A small set of adjacent parser papercuts are also
documented for triage.

---

## The disconnect, traced

### Step 1: extend the basis (succeeds)

```
extend_basis(
    name="economic",
    base="SI",
    additional_components=[
        {"name": "currency", "symbol": "$",
         "description": "Monetary value, treated as a fundamental dimension."}
    ]
)
```

Returns:

```json
{
    "success": true,
    "name": "economic",
    "base": "SI",
    "components": [
        "M (mass)", "L (length)", "T (time)", "I (current)",
        "Θ (temperature)", "N (amount)", "J (luminosity)",
        "$ (currency)"
    ],
    "message": "Extended basis 'economic' created with 8 components.
                (Phase 1: informational only)"
}
```

The basis exists in session state. `list_extended_bases()` returns it.
Everything looks promising.

### Step 2: register a unit in that dimension (fails)

```
define_unit(
    name="us_dollar",
    dimension="currency",
    aliases=["USD", "$"]
)
```

Returns:

```json
{
    "error": "Unknown dimension: 'currency'",
    "error_type": "unknown_unit",
    "likely_fix": "current"
}
```

The parser doesn't see `currency` as a dimension. It even helpfully suggests
`current` (electrical current, dimension I) as a typo correction — which is
the wrong direction entirely. The extended basis exists in one part of the
session; the dimension parser reads from a different table that wasn't
notified.

### Step 3: register a quantity kind in that dimension (also fails)

```
define_quantity_kind(name="capital_flow", dimension="currency/time")
```

Same failure mode. The dimension parser is the bottleneck for both unit
registration and quantity-kind registration, and it queries the canonical
SI dimension set, not the active session basis.

### What this means in practice

Phase 1 `extend_basis` is currently advisory metadata. It records intent
("this session intends to reason over a basis that includes currency") but
no downstream tool consumes that intent. From a user's perspective the call
appears to have done nothing useful — every subsequent attempt to *use* the
new dimension fails with "Unknown dimension."

---

## The workaround (and what it costs)

The sovereign-potential demo proceeded by registering everything in SI mass
and time:

```
define_quantity_kind(name="capital_flow",     dimension="M·T⁻¹")
define_quantity_kind(name="capital_mobility", dimension="M·T⁻¹")
define_quantity_kind(name="gdp",              dimension="M·T⁻¹")
define_quantity_kind(name="debt_stock",       dimension="mass")
```

`compute` runs in `kg/year`. Numbers come back in kilograms per year. The
narrative reframes them as "$B/year" by convention. The dimensional checks
all pass; the algebra is sound.

But three things break in ways that a careful reviewer would catch:

**1. Semantic dishonesty in the trace.** Every `compute` step prints `kg/yr`
in its dimensional trace. A reader inspecting the artifact's "ucon
validation" panel sees the math is right, but the units are visibly wrong
for the domain. For a demo whose entire premise is "rigorous dimensional
analysis applied to economics," advertising kilograms in the validation
output is corrosive to the pitch.

**2. KOQ collisions are forced rather than informative.** When
`capital_flow`, `capital_mobility`, and `gdp` are all registered as M·T⁻¹,
the KOQ system warns that they share a dimension. That warning is *correct*
in the workaround world, but it obscures what the warning *should* be in a
proper basis: `capital_flow` and `capital_mobility` would share dimension
($·T⁻¹), but `gdp` would be a *different* dimension ($·T⁻¹ as well, in this
trivial extension, but distinguishable in a richer basis where production
is separated from transfer). The demo can't make that distinction. KOQ in
the workaround world is doing less work than it could.

**3. The mass-as-currency convention doesn't compose.** A second concept
that genuinely needs mass — say, commodity flows in tonnes — would now
collide with the currency stand-in. Multi-domain models (oil-for-dollars,
gold reserves, agricultural exports) become impossible to type-check
because the same dimensional bucket holds physically distinct quantities.
The ergonomic upper bound on the workaround is: one domain at a time, no
cross-domain models, no joint reasoning over goods and money.

For a demo, all of this is acceptable. For a v2 that aspires to handle
balance-of-payments accounting (where `goods_flow [tonnes/yr]` and
`capital_flow [$/yr]` must coexist and connect through prices), the
workaround is a dead end.

---

## Proposed Phase 2 design

The fix is mechanical: route the dimension parser and unit registry through
the active basis, not the canonical SI table.

### Required changes

**`ucon.dimensions.parse_dimension(spec, basis=None)`**

Currently parses against the SI dimension set. Should accept an optional
`basis` argument; when omitted, defaults to the session's active basis (or
SI if none active). Component lookup queries the basis's component list,
not a hardcoded set. `parse_dimension("currency", basis=economic_basis)`
returns a dimension vector with the new component lit up.

**`ucon.units.define_unit(name, dimension, ...)`**

Currently looks up `dimension` against the SI table. Should resolve through
`parse_dimension` with the active basis. After Phase 2:

```
extend_basis(name="economic", additional_components=[
    {"name": "currency", "symbol": "$"}
])
define_unit(name="us_dollar", dimension="currency", aliases=["USD"])
# → succeeds, registers USD with dimension vector [0,0,0,0,0,0,0,1]
```

**`ucon.koq.define_quantity_kind(name, dimension, ...)`**

Same change: dimension parsing through the active basis.

```
define_quantity_kind(name="capital_flow", dimension="currency/time")
# → succeeds, registers with vector [0,0,-1,0,0,0,0,1]
```

**`ucon.conversion.define_conversion(src, dst, factor, ...)`**

Already unit-to-unit, so no parser change needed — but the conversion
graph must accept edges between units in extended dimensions. After
Phase 2:

```
define_conversion(src="USD", dst="EUR", factor=0.92)
define_conversion(src="EUR", dst="JPY", factor=170.0)
# → BRL → USD → EUR → JPY chains via existing graph traversal
```

This is the killer feature. ucon's ConversionGraph already handles
multi-hop chains for SI units; extending it to user-defined dimensions
turns FX, commodity prices, energy markets, and any other domain-specific
quantity into first-class graph traversal.

### Backward compatibility

Existing calls with no active extended basis continue to resolve against
SI. No breaking changes for the medical-dosage and physics-conversion use
cases that ucon already handles. Phase 2 is purely additive.

### Test cases for verification

```
# After extend_basis(name="economic", additional_components=[currency]):
assert parse_dimension("currency").is_valid
assert parse_dimension("currency/time").is_valid
assert parse_dimension("currency*length") == parse_dimension("length*currency")

# Unit registration:
define_unit(name="us_dollar", dimension="currency", aliases=["USD"])
define_unit(name="euro",      dimension="currency", aliases=["EUR"])
define_conversion(src="USD", dst="EUR", factor=0.92)
assert convert(100, "USD", "EUR").value == 92.0

# Multi-hop FX:
define_conversion(src="EUR", dst="JPY", factor=170.0)
assert convert(100, "USD", "JPY").value == 100 * 0.92 * 170.0

# Dimensional checking on cross-domain:
define_quantity_kind(name="oil_flow",     dimension="mass/time")
define_quantity_kind(name="capital_flow", dimension="currency/time")
# These should now have *distinct* dimensions, not both M·T⁻¹.

# Compose: oil price has dimension currency/mass.
define_quantity_kind(name="oil_price", dimension="currency/mass")
# Then oil_price * oil_flow → capital_flow. Type-checked composition.
```

That last block is the payoff. Without Phase 2, ucon cannot express
"oil flow times oil price equals capital flow" as a dimensionally-checked
relationship — because oil flow and capital flow are forced to share the
same M·T⁻¹ bucket. With Phase 2, the relationship is mechanically verified
and the user can't accidentally substitute one for the other.

### Phase 3 (later): namespace isolation

If two sessions extend SI with conflicting `currency` dimensions (one
registers BRL, another registers tokens-as-currency), they should not
silently merge. Bases should be namespaced: `economic.currency` ≠
`compute.tokens`, with explicit imports for composition. This becomes
important once ucon is the substrate for an agent ecosystem where each
agent declares its domain basis as part of its spec (Slater AgentSpec
analog). Out of scope for Phase 2; flagged here for the roadmap.

---

## Adjacent parser papercuts (separate triage)

Discovered while building the demo. Smaller in scope but each one cost
real time and produces confusing error messages.

### 1. `define_quantity_kind(dimension="mass/time")` rejected

The error hints advertise both vector notation (`M·T⁻¹`) and
human-readable form (`energy/amount_of_substance`). The vector form
parses; the human-readable form is rejected for compound expressions
involving slashes, even though the docstring example uses exactly that
shape.

```
define_quantity_kind(name="gdp", dimension="mass/time")
# → error: Could not parse dimension: 'mass/time'

define_quantity_kind(name="gdp", dimension="M·T⁻¹")
# → succeeds
```

The parser appears to accept `mass` standalone but not `mass/time`. Either
the human-readable parser doesn't handle the binary `/` operator, or the
two forms are routed through different parsers and only the vector path
is complete. Either way the docstring promise isn't fulfilled.

### 2. Bare component letters rejected

```
define_quantity_kind(dimension="M")    # → error
define_quantity_kind(dimension="M¹")   # → error
define_quantity_kind(dimension="mass") # → succeeds
```

A single dimension component should be parseable as a degenerate compound.
Right now there's a bifurcation between "use the long word" (works) and
"use the symbol" (fails for compounds, fails for single).

### 3. No mechanism for declaring a dimensionless quantity kind

```
define_quantity_kind(dimension="1")            # → error
define_quantity_kind(dimension="M⁰")           # → error
define_quantity_kind(dimension="amount/amount") # → error
```

This is a real gap. Many quantities are dimensionless but semantically
distinct: openness indices, ratios, log-yields, probabilities, exchange
rates (technically currency/currency, but the dimensions cancel),
correlation coefficients, debt-to-GDP fractions. KOQ disambiguation would
shine here — distinguishing a probability from a fractional ratio when
both are dimensionless — but currently you cannot register either, because
the parser has no notation for "the empty dimension."

Suggested fix: accept `""` (empty string), `"dimensionless"`, or
`"1"` as the dimensionless dimension. Any of these is fine; the absence of
a notation is the issue.

### 4. `validate_result` regex-on-prose false positive

```
validate_result(
    value=4083,
    unit="kg/year",
    reasoning="...0.85 * sqrt(GDP_a * GDP_b) * 1.10 EM-to-DM multiplier..."
)
```

Returns:

```
"semantic_warnings": [
    "Reasoning mentions 'Ea' which is associated with
     'activation_energy', but declared kind is 'capital_flow'"
]
```

The substring `Ea` in `EM-to-DM` triggered a match against the
`activation_energy` symbol. The check appears to do a case-insensitive
substring scan over reasoning text against known symbol names. Three
options, in increasing order of effort:

- **Cheap fix:** require word boundaries (`\bEa\b`) so `EM-to-DM` doesn't
  match. Catches most false positives.
- **Better fix:** tokenize the reasoning text and only match whole tokens.
- **Best fix:** drop the regex approach entirely and use embedding
  similarity over the reasoning text vs. quantity-kind descriptions. This
  was explored earlier (Jina) and concluded against for the *factor
  decomposition* path, but for *post-hoc semantic check on prose* it's
  arguably the right tool — short text, qualitative comparison, no need
  for exactness.

The current behavior degrades user trust in the validation output: any
demo that names "EM" emerging markets, "He" for a person, "In" for India,
"Ar" for Argentina, etc. will trip false positives.

### 5. Session state appears to drop across calls in some contexts

When the demo session was suspended and resumed (across a tool turn
boundary), `declare_computation(quantity_kind="capital_flow")` returned
"Unknown quantity kind: 'capital_flow'" despite a successful registration
earlier in the same conversation. Re-registering worked. Worth a closer
look at session lifetime and persistence — the interaction with MCP
session boundaries may be different from what the in-process tests
exercise.

---

## Bigger picture: what Phase 2 unlocks for positioning

The current pitch — *"type safety for SI calculations"* — is real but
narrow. Phase 2 is the move from "ucon is a rigorous SI calculator" to
"ucon is the substrate for any quantitative domain ontology, with audit
trails." That second framing is materially larger TAM and structurally
hard for Pint or QUDT to follow, because they're SI-shaped down to the
bone.

The demo case is sovereign potential, but the same machinery applies to:

- **Pharmacology with drug-specific units:** mg-active-ingredient vs.
  mg-salt-form; international units (IU) for biologics.
- **Information theory:** bits, nats, hartleys as registered units of
  information; bandwidth as bits/time; channel capacity as a typed kind
  distinct from raw rate.
- **Compute economics:** tokens, GPU-hours, FLOPs as first-class units;
  cost-per-token as currency/tokens; latency as time/request.
- **Climate accounting:** tonnes-CO2-equivalent vs. tonnes-CO2 (via
  GWP factors as conversion edges); social cost of carbon as
  currency/mass-CO2.
- **Epidemiology:** infections, R₀ as dimensionless reproduction number,
  serial intervals, vaccine efficacy as a typed dimensionless quantity
  (distinct from openness indices in the same dimension).

Each of these is a domain where dimensional sloppiness is currently
endemic and where a typed ontology with conversion graphs would catch
real errors. Phase 2 makes ucon the only Python tool that handles all of
them through one consistent interface.

The conference talk version writes itself: *"Dimensional analysis was a
20th-century discipline for physics. ucon makes it a 21st-century
discipline for any quantitative domain an agent operates in — including
the ones we haven't built yet."*

---

## Action items

1. **[P1] Wire `extend_basis` through to dimension parser and unit
   registry.** This is the headline. Phase 2 design above.
2. **[P2] Fix human-readable compound dimension parsing
   (`mass/time`).** Single-line parser bug; should be a small fix.
3. **[P2] Add notation for dimensionless quantity kinds.** API decision
   on whether `""`, `"dimensionless"`, or `"1"` is canonical, then
   implement.
4. **[P3] Replace `validate_result`'s substring scan with token-boundary
   match.** Cheap fix; bigger embedding-based approach can come later.
5. **[P3] Investigate session-lifetime drops across MCP boundaries.**
   May be configuration; may be a real bug. Worth a quick repro.
6. **[P4] Phase 3 namespace isolation for extended bases.** Roadmap
   item; not blocking Phase 2.

---

## Appendix: what the artifact would look like with Phase 2

For reference, the sovereign-potential demo's algebra panel currently
displays:

```
F_AB = σ_AB · ΔΦ
[M·T⁻¹] = [M·T⁻¹] · [1]
```

With Phase 2 it would display:

```
F_AB = σ_AB · ΔΦ
[$·T⁻¹] = [$·T⁻¹] · [1]
```

Small textual change. Large semantic change: every reader now
understands the demo is *literally* doing economics, not borrowing
mass for kilograms-as-dollars. The ucon validation trace would print
`USD/year` instead of `kg/year`. The KOQ disambiguation would
distinguish `gdp [$·T⁻¹]` from `oil_flow [M·T⁻¹]` cleanly, with no
forced collision. The conversion graph would handle FX as a
first-class operation. The artifact's claim — "rigorous dimensional
analysis applied to econophysics" — would be true without quotation
marks around "rigorous."

That's the Phase 2 deliverable, scoped end to end.

---

*Filed against `radiativity-co/ucon`. Cross-references: SciPy 2026
talk outline; Slater AgentSpec dimensional-binding design; econophysics
study no. 1 (sovereign potential, global) and no. 2 (sovereign potential,
Africa).*

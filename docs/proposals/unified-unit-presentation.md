# Unified Unit Presentation in `ucon`

## 1. Introduction: _From Strings to Structured Algebra_

Early in `ucon`’s development, composite units such as `"joule_per_kelvin"` and `"webers_per_meter"` were defined explicitly in the `ucon.units` module.
These string-based compositions solved an immediate need — a way to express derived quantities — but they blurred the conceptual boundary between *algebraic derivation* and *nomenclature*.

The underscore convention (e.g., `"meter_per_second"`) originated as a pragmatic way to represent composite dimensions without implementing a formal derivation system.
It effectively flattened algebraic relationships into string tokens — easy to serialize but inconsistent with `ucon`’s foundational principle: **that dimensions and units should be composable algebraic objects**.

The proposed direction removes such ad-hoc composites. Instead, *composite units are derived dynamically* from the algebraic combination of base units and their associated dimensions.
This reduces redundancy, aligns representation with mathematical semantics, and makes later integration with the `ConversionGraph` (or other registry-based systems) trivial.

---

## 2. The Dimension Basis as Unifying Schema

Every dimension in `ucon` derives from a canonical **basis vector** in a seven-dimensional vector space:

| Basis Dimension        | Symbol | Vector Representation      |
|------------------------|--------|----------------------------|
| Time                   | T      | (1, 0, 0, 0, 0, 0, 0)      |
| Length                 | L      | (0, 1, 0, 0, 0, 0, 0)      |
| Mass                   | M      | (0, 0, 1, 0, 0, 0, 0)      |
| Current                | I      | (0, 0, 0, 1, 0, 0, 0)      |
| Temperature            | Θ      | (0, 0, 0, 0, 1, 0, 0)      |
| Luminous Intensity     | J      | (0, 0, 0, 0, 0, 1, 0)      |
| Amount of Substance    | N      | (0, 0, 0, 0, 0, 0, 1)      |

### 2.1 Algebraic Operators on Dimensions

Rather than treating dimensions as inert enum members, the proposal codifies full algebraic operators:

- Multiplication (`*`) _adds_ vectors, enabling `length * time` → `derived(Vector(T=1, L=1,…))`.
- Division (`/`) _subtracts_ vectors, so `length / time` yields velocity.
- Exponentiation (`**`) _scales_ vectors component-wise, allowing `area = length ** 2`, `frequency = time ** -1`, and higher-order constructs like `jerk = length * time ** -3`.

When an operation lands on a vector not present in the official basis, the dimension resolver synthesizes a virtual enum member named--e.g., `derived(Vector(T=-2, L=1, M=1, ...))`.
Such closure keeps dynamically formed dimensions hashable, comparable, and printable without bloating the static enum.

### 2.2 Canonical Maps Between Dimensions and Units

En route to a full conversion graph, explicit registries mapping each dimension to its default can be used to track aliases.
For example, given the SI basis, relations with non-standard units can be declared:

```python
DIMENSION_ALIASES = {
    Dimension.time: "second",
    Dimension.length: "meter",
    Dimension.mass: "gram",
    Dimension.current: "ampere",
    Dimension.temperature: "kelvin",
    Dimension.luminous_intensity: "candela",
    Dimension.amount_of_substance: "mole",
}
UNIT_RELATIONS = {
    "length": {
        "meter": {"inch": 39.37, "foot": 3.28084, "mile": 0.000621371}
    },
    "mass": {
        "gram": {"pound": 0.00220462}
    },
    "time": {
        "second": {"minute": 1/60, "hour": 1/3600}
    },
}
```
Together, these config serve as a "proto" conversion graph.
The alias map pins each dimension to its canonical base unit (anchoring the nodes), while the relations dictionary lists direct conversion edges between those base units and their alternates.

To convert: (1) a quantity’s dimension → base unit is resolved via DIMENSION_ALIASES; (2) its current unit is looked up in UNIT_RELATIONS to fetch the factor to or from the base; (3) factors composed if chaining through multiple alternates.

Composite units are never hard-coded in such config.
Instead, any time units are multiplied or divided, the resulting dimension is resolved through the vector algebra, and the unit metadata system fabricates the factor along with the corresponding name, shorthand, and display string.

### 2.3 Deterministic Shorthands and Derived Names

The schema reserves a consistent naming convention for derived units.
For example, `meter / second` becomes `m/s`, while `gram * meter / second ** 2` produces `g·m/s²`.
These shorthands are generated from the metadata described in the next section, but the dimension basis guarantees we always know the order and orientation of factors.

Because every unit ultimately decomposes into the seven base dimensions, we can deterministically sort numerator factors (positive exponents) and denominator factors (negative exponents) and preserve their powers.
That’s why the shorthand builder never has to guess whether `second` belongs upstairs or downstairs.

---

## 3. Unified Configuration Schema

The proposed configuration is now split into three cooperating structures:

1. **Scale definitions** — prefix magnitudes baked into the code as exponents.
2. **Unit metadata** — aliases, canonical name, and default dimension.
3. **Conversion relations** — graph entries from one unit to another.

No scale lives in configuration anymore; prefixes act as algebraic decorators on
units. A prospective shape for `Scale`:

```python
class Scale(Enum):
    mega  = Exponent(10, 6),  "M", "mega"
    kilo  = Exponent(10, 3),  "k", "kilo"
    one   = Exponent(10, 0),  "",  ""
    centi = Exponent(10, -2), "c", "centi"
    milli = Exponent(10, -3), "m", "milli"

    def __init__(self, exponent, shorthand, alias):
        self._value_ = exponent
        self.shorthand = shorthand
        self.alias = alias
```

Coupling `Scale` and `Unit` gives us composable prefixes:

```python
Scale.milli * units.liter   # → Unit with name 'liter', shorthand 'mL'
Scale.kilo * units.gram     # → Unit with name 'gram', shorthand 'kg'
```

No external registry is necessary—the algebraic model handles magnitude,
representation, and cancellation.

---

## 4. Resolution Rules and Lookup Semantics

Resolving `"3 km"` goes through a predictable pipeline:

1. **Parse prefix** → `Scale.kilo`.
2. **Apply to unit** → `Scale.kilo * Unit("meter")`.
3. **Resolve dimension** → `Dimension.length`.
4. **Optionally convert** via registered conversion factors.

Because dimensions are algebraically validated, invalid combinations (e.g.,
adding meters to seconds) are caught early. Composite expressions like
`"3 m/s"` simply evaluate to the corresponding derived dimensio (`velocity`)
without manual string logic.

---

## 5. Dynamic Derivation and Display

The proposal includes a `CompositeUnit` type that stores constituent units and exponents, merges duplicates, removes dimensionless factors, and exposes a canonical shorthand. This ensures expressions such as:
```python
density = units.gram / (Scale.milli * units.liter)
accel   = units.meter / (units.second ** 2)
momentum = density * units.meter ** 3 * units.second
```

render cleanly while remaining algebraically precise.

---

## 6. Toward the ConversionGraph

The conversion layer progresses from simple maps to a graph in which units are typed by their dimension, edges carry factors (or callables), and traversal produces composite conversions.
Because every unit has a canonical identifier and dimension, the graph can enforce dimensional invariants automatically.

---

## 7. Summary

- **Dimensions** form a vector space that supports multiplication, division, and exponentiation.
- **Scales** act directly on units; prefix math will no longer be bolted onto quantities.
- **Composite units** are derived dynamically, yielding canonical shorthands.
- **Conversion** logic can evolve into a graph structure with dimension-aware validation.

With these pieces in place, the unified representation vision becomes both
coherent and practical: `ucon` can present SI-aligned, algebraically consistent quantities to users without relying on fragile string conventions.

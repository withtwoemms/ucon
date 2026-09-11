# Ticket: v0.10.0 Scientific Computing

**Status:** Complete

---

## User Stories

### NumPy Arrays

**As a** scientist working with experimental data,
**I want to** create arrays of dimensioned quantities and perform vectorized operations,
**So that** I can process large datasets efficiently without losing unit safety.

#### Acceptance Criteria

- [x] `NumberArray` class stores quantities, unit, and optional uncertainty
- [x] `units.meter([1, 2, 3])` returns `NumberArray` (callable syntax)
- [x] `.to(target)` converts entire array to different unit
- [x] Arithmetic (`+`, `-`, `*`, `/`) works with scalars, Numbers, and NumberArrays
- [x] Uncertainty propagates through arithmetic using quadrature rules
- [x] Indexing: scalar index returns `Number`, slice returns `NumberArray`
- [x] Iteration yields `Number` instances
- [x] Reduction operations: `sum()`, `mean()`, `std()`, `min()`, `max()`
- [x] Comparison operators (`>`, `<`, `>=`, `<=`, `==`, `!=`) return boolean arrays
- [x] N-D arrays and broadcasting supported
- [x] `numpy` is optional: `pip install ucon[numpy]`
- [x] Clear `ImportError` when numpy not installed

---

### Pandas Integration

**As a** data analyst,
**I want to** attach units to DataFrame columns and convert between units,
**So that** I can work with tabular data while maintaining dimensional correctness.

#### Acceptance Criteria

- [x] `NumberSeries` wraps `pd.Series` with unit metadata
- [x] `df['col'].ucon.with_unit(units.meter)` accessor pattern
- [x] `.to(target)` returns new `NumberSeries` with converted values
- [x] Arithmetic between `NumberSeries` preserves unit semantics
- [x] `pandas` is optional: `pip install ucon[pandas]`

---

### Polars Integration

**As a** data engineer using Polars for performance,
**I want to** work with unit-aware columns,
**So that** I can perform high-performance data transformations with unit safety.

#### Acceptance Criteria

- [x] `NumberColumn` wraps `pl.Series` with unit metadata
- [x] `.to(target)` converts column to different unit
- [x] Arithmetic operations work with unit tracking
- [x] `polars` is optional: `pip install ucon[polars]`

---

### Performance

**As a** library user processing large datasets,
**I want** ucon array operations to be competitive with pint,
**So that** I don't sacrifice performance for unit safety.

#### Acceptance Criteria

- [x] Conversion path caching in `ConversionGraph`
- [x] Scale factor caching for repeated unit pairs
- [x] Unit multiplication/division result caching
- [x] Benchmark suite: `make benchmark`, `make benchmark-pint`
- [x] Creation 10x+ faster than pint
- [x] Conversion and arithmetic within 2x of pint

---

### Documentation

**As a** new user,
**I want** clear documentation and examples,
**So that** I can quickly learn to use the scientific computing features.

#### Acceptance Criteria

- [x] `docs/guides/numpy-arrays.md` with performance tips
- [x] `docs/guides/pandas-integration.md`
- [x] `docs/guides/polars-integration.md`
- [x] `examples/scientific_computing.ipynb` Jupyter notebook
- [x] README updated with installation extras and quick examples

---

## Bug Fixes

- [x] `Unit * Unit` with same unit now produces correct exponent (`meter * meter` → `m²`)

---

## Implementation Notes

### Caching Strategy

Lazy caching approximates pint's fixed global registry without startup cost:
- Conversion paths cached after first graph traversal
- Scale factors cached for repeated unit pairs
- Unit products cached to avoid expensive `UnitProduct.__init__`

### Files

| File | Purpose |
|------|---------|
| `ucon/numpy.py` | `NumberArray` class |
| `ucon/pandas.py` | `NumberSeries`, `UconSeriesAccessor` |
| `ucon/polars.py` | `NumberColumn` |
| `ucon/core.py` | Callable syntax, `Unit * Unit` fix, caching |
| `ucon/graph.py` | Conversion path caching |
| `benchmarks/array_operations.py` | Performance benchmarks |

---

## References

- Implementation plan: `docs/internal/IMPLEMENTATION_PLAN_v0.10.0-scientific-computing.md`
- ROADMAP: v0.10.0 section

---

## Closure Note (2026-07-12)

**Closed: done.** Ticket body already marked Complete with all acceptance
criteria checked. Shipped in v0.10.0; integrations now live at
`ucon/integrations/{numpy,pandas,polars}.py` after the v2.0 restructuring.

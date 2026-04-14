# Performance

Benchmarks for ucon scalar and array operations.

---

## Methodology

All benchmarks use `time.perf_counter_ns` for wall-clock timing. Each scenario runs one warm-up call followed by N timed iterations. Results report the **median**, **p5** (5th percentile), and **p95** (95th percentile) of the iteration timings.

Caveats:

- Single-threaded, CPython only
- GC is **not** disabled — timings reflect realistic usage
- Results vary by hardware, Python version, and system load
- Array benchmarks require NumPy

---

## Scalar Operations

Five scenarios covering the core scalar API:

| # | Scenario | What it measures |
|---|----------|-----------------|
| 1 | **Unit creation** | `units.meter(5.0)` — Number construction from a Unit call |
| 2 | **Scale-only conversion** | `km_val.to(units.meter)` — prefix scaling without graph lookup |
| 3 | **Graph conversion** | `m_val.to(units.foot)` — BFS path finding + Map application |
| 4 | **Temperature conversion** | `c_val.to(units.fahrenheit)` — AffineMap with offset |
| 5 | **Unit algebra** | `units.meter / units.second` — UnitProduct construction |

Run with:

```bash
make benchmark
```

### Results

Measured on CPython 3.12, macOS (Apple Silicon), 50 iterations per scenario.

| Scenario | ucon | pint 0.25 | Speedup |
|----------|------|-----------|---------|
| Unit creation | 1.2 us | 26.8 us | 22.0x |
| Scale-only conversion | 6.0 us | 23.0 us | 3.9x |
| Graph conversion | 4.5 us | 22.7 us | 5.1x |
| Temperature conversion | 4.5 us | 39.8 us | 8.8x |
| Unit algebra | 9.6 us | 11.7 us | 1.2x |

---

## Array Operations

Two scenarios at varying array sizes (n=10 through n=1,000,000):

| # | Scenario | What it measures |
|---|----------|-----------------|
| 6 | **Array creation** | `units.meter(np.arange(N))` — NumberArray construction |
| 7 | **Array conversion** | `arr.to(units.foot)` — vectorized Map application |

Array creation wraps an existing NumPy array without copying — cost is constant regardless of size. Array conversion applies the Map's scale factor across the entire array in a single vectorized operation, so the work is dominated by NumPy at large N.

### Results

Measured on CPython 3.12, macOS (Apple Silicon), 50 iterations per scenario.

| Scenario | ucon | pint 0.25 | Speedup |
|----------|------|-----------|---------|
| Array creation (n=10) | 1.2 us | 70.0 us | 60.0x |
| Array conversion (n=10) | 11.7 us | 33.0 us | 2.8x |
| Array creation (n=100) | 1.2 us | 68.9 us | 55.3x |
| Array conversion (n=100) | 11.9 us | 33.3 us | 2.8x |
| Array creation (n=1,000) | 1.3 us | 70.7 us | 56.4x |
| Array conversion (n=1,000) | 12.9 us | 35.7 us | 2.8x |
| Array creation (n=10,000) | 1.2 us | 79.2 us | 64.2x |
| Array conversion (n=10,000) | 19.3 us | 43.0 us | 2.2x |
| Array creation (n=100,000) | 1.3 us | 128.3 us | 99.1x |
| Array conversion (n=100,000) | 68.6 us | 93.5 us | 1.4x |
| Array creation (n=1,000,000) | 1.5 us | 1.5 ms | 1043.7x |
| Array conversion (n=1,000,000) | 1.5 ms | 1.5 ms | 1.0x |

Array creation maintains constant ~1.2 us regardless of size (zero-copy wrapping), while pint's cost grows with N — reaching 1000x slower at one million elements. Array conversion shows ucon's overhead is a fixed ~12 us of dispatch; as N grows, both libraries converge to the same NumPy-bound cost, reaching parity at n=1,000,000.

---

## Comparison with Pint

To run benchmarks with [pint](https://pint.readthedocs.io/) comparison:

```bash
make benchmark-pint
```

This installs pint into the project virtualenv, runs the same scenarios using pint's API, and reports a **speedup ratio** (pint median / ucon median) for each scenario.

Equivalent pint operations:

| ucon | pint |
|------|------|
| `units.meter(5.0)` | `5.0 * ureg.meter` |
| `km_val.to(units.meter)` | `km_val.to(ureg.meter)` |
| `m_val.to(units.foot)` | `m_val.to(ureg.foot)` |
| `c_val.to(units.fahrenheit)` | `c_val.to(ureg.degF)` |
| `units.meter / units.second` | `ureg.meter / ureg.second` |
| `units.meter(np.arange(N))` | `np.arange(N) * ureg.meter` |
| `arr.to(units.foot)` | `arr.to(ureg.foot)` |

---

## Reproducing

### Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- NumPy (installed as an optional dependency)

### Commands

```bash
# Standard benchmarks
make benchmark

# With pint comparison (installs pint automatically)
make benchmark-pint

# Custom sizes and iterations
make benchmark BENCH_SIZES="100 1000 10000" BENCH_ITERATIONS=100
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BENCH_SIZES` | `1000 10000 100000` | Space-separated array sizes |
| `BENCH_ITERATIONS` | `50` | Iterations per scenario |

---

## Performance Tips

- **Scale-only conversions are fastest** — converting between prefixed variants of the same unit (km → m, mg → g) skips graph traversal entirely.
- **Graph conversions are cached** — repeated conversions between the same pair of units reuse the cached path and scale factor.
- **Array operations scale with NumPy** — `NumberArray.to()` applies a single vectorized multiplication, so large arrays convert nearly as fast as small ones per element.
- **Avoid repeated unit algebra in loops** — construct `UnitProduct` objects once and reuse them.

For more on array usage, see the [NumPy Arrays](../guides/numpy-arrays.md) guide.

#!/usr/bin/env python3
"""Performance benchmarks for ucon scalar and array operations.

Usage:
    python benchmarks/array_operations.py --sizes 1000 10000 100000 --iterations 50
    python benchmarks/array_operations.py --sizes 1000 10000 100000 --iterations 50 --with-pint
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
import time
from typing import Any, Callable


def _median_ns(timings_ns: list[int]) -> float:
    return statistics.median(timings_ns)


def _p5_ns(timings_ns: list[int]) -> float:
    sorted_t = sorted(timings_ns)
    idx = max(0, int(len(sorted_t) * 0.05) - 1)
    return float(sorted_t[idx])


def _p95_ns(timings_ns: list[int]) -> float:
    sorted_t = sorted(timings_ns)
    idx = min(len(sorted_t) - 1, int(len(sorted_t) * 0.95))
    return float(sorted_t[idx])


def _fmt_time(ns: float) -> str:
    """Format nanoseconds into a human-friendly string."""
    if ns < 1_000:
        return f"{ns:.0f} ns"
    elif ns < 1_000_000:
        return f"{ns / 1_000:.1f} us"
    elif ns < 1_000_000_000:
        return f"{ns / 1_000_000:.1f} ms"
    else:
        return f"{ns / 1_000_000_000:.2f} s"


def _bench(func: Callable[[], Any], iterations: int) -> dict[str, float]:
    """Run func iterations times, return timing stats in nanoseconds."""
    # warm-up
    func()

    timings: list[int] = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        func()
        t1 = time.perf_counter_ns()
        timings.append(t1 - t0)

    return {
        "median": _median_ns(timings),
        "p5": _p5_ns(timings),
        "p95": _p95_ns(timings),
    }


# ---------------------------------------------------------------------------
# Load-time benchmarks (subprocess-isolated)
# ---------------------------------------------------------------------------

_LOAD_SNIPPET = """\
import time
t0 = time.perf_counter_ns()
import ucon
t1 = time.perf_counter_ns()
print(t1 - t0)
"""


def _subprocess_import_ns(*, env_extra: dict[str, str] | None = None, runs: int = 10) -> list[int]:
    """Measure `import ucon` wall time in a fresh subprocess, *runs* times."""
    import os

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    timings: list[int] = []
    for _ in range(runs):
        result = subprocess.run(
            [sys.executable, "-c", _LOAD_SNIPPET],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Subprocess failed: {result.stderr.strip()}")
        timings.append(int(result.stdout.strip()))
    return timings


def bench_load_time(runs: int) -> dict[str, dict[str, float]]:
    """Return timing stats for cache-hit and TOML-fallback import paths."""
    # Cache-hit path (default)
    cache_timings = _subprocess_import_ns(runs=runs)
    cache_stats = {
        "median": _median_ns(cache_timings),
        "p5": _p5_ns(cache_timings),
        "p95": _p95_ns(cache_timings),
    }

    # TOML-fallback path (cache disabled)
    toml_timings = _subprocess_import_ns(env_extra={"UCON_NO_CACHE": "1"}, runs=runs)
    toml_stats = {
        "median": _median_ns(toml_timings),
        "p5": _p5_ns(toml_timings),
        "p95": _p95_ns(toml_timings),
    }

    return {"cache": cache_stats, "toml": toml_stats}


_GRAPH_LOAD_SNIPPET = """\
import time, statistics, json
from pathlib import Path

toml_path = Path("ucon/comprehensive.ucon.toml")
iterations = {iterations}

def bench(func):
    func()  # warmup
    timings = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        func()
        t1 = time.perf_counter_ns()
        timings.append(t1 - t0)
    return timings

from ucon.serialization import from_toml
toml_timings = bench(lambda: from_toml(toml_path))

from ucon._cache import load_cached_graph
cache_timings = bench(lambda: load_cached_graph(toml_path))

print(json.dumps({{"toml": toml_timings, "cache": cache_timings}}))
"""


def bench_graph_load(iterations: int) -> dict[str, dict[str, float]]:
    """Measure isolated graph-load time in a subprocess (no memory contamination)."""
    import json

    snippet = _GRAPH_LOAD_SNIPPET.format(iterations=iterations)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Graph load benchmark failed: {result.stderr.strip()}")

    data = json.loads(result.stdout.strip())
    toml_stats = {
        "median": _median_ns(data["toml"]),
        "p5": _p5_ns(data["toml"]),
        "p95": _p95_ns(data["toml"]),
    }
    cache_stats = {
        "median": _median_ns(data["cache"]),
        "p5": _p5_ns(data["cache"]),
        "p95": _p95_ns(data["cache"]),
    }

    return {"cache": cache_stats, "toml": toml_stats}


def _print_load_table(results: dict[str, dict[str, float]]) -> None:
    header = f"{'Path':<28} {'median':>12} {'p5':>12} {'p95':>12}"
    print(header)
    print("-" * len(header))

    for label, key in [("Marshal cache", "cache"), ("TOML (no cache)", "toml")]:
        s = results[key]
        print(
            f"{label:<28} "
            f"{_fmt_time(s['median']):>12} "
            f"{_fmt_time(s['p5']):>12} "
            f"{_fmt_time(s['p95']):>12}"
        )

    cache_med = results["cache"]["median"]
    toml_med = results["toml"]["median"]
    if cache_med > 0:
        speedup = toml_med / cache_med
        print(f"\n  Speedup (median): {speedup:.1f}x")


# ---------------------------------------------------------------------------
# ucon benchmarks
# ---------------------------------------------------------------------------

def bench_ucon_scalar(iterations: int) -> list[dict]:
    from ucon import units, Scale

    km = Scale.kilo * units.meter
    celsius_100 = units.celsius(100)

    scenarios = []

    # 1. Unit creation
    stats = _bench(lambda: units.meter(5.0), iterations)
    scenarios.append({"name": "Unit creation", "stats": stats})

    # 2. Scale-only conversion (km -> m, no graph traversal)
    km_val = km(5.0)
    stats = _bench(lambda: km_val.to(units.meter), iterations)
    scenarios.append({"name": "Scale-only conversion", "stats": stats})

    # 3. Graph conversion (m -> ft, BFS + Map)
    m_val = units.meter(5.0)
    stats = _bench(lambda: m_val.to(units.foot), iterations)
    scenarios.append({"name": "Graph conversion", "stats": stats})

    # 4. Temperature conversion (C -> F, AffineMap)
    stats = _bench(lambda: celsius_100.to(units.fahrenheit), iterations)
    scenarios.append({"name": "Temperature conversion", "stats": stats})

    # 5. Unit algebra (m / s)
    stats = _bench(lambda: units.meter / units.second, iterations)
    scenarios.append({"name": "Unit algebra", "stats": stats})

    return scenarios


def bench_ucon_array(iterations: int, sizes: list[int]) -> list[dict]:
    import numpy as np
    from ucon import units

    scenarios = []
    for size in sizes:
        data = np.arange(size, dtype=float)

        # 6. Array creation
        stats = _bench(lambda: units.meter(data), iterations)
        scenarios.append({
            "name": f"Array creation (n={size:,})",
            "stats": stats,
        })

        # 7. Array conversion
        arr = units.meter(data)
        stats = _bench(lambda: arr.to(units.foot), iterations)
        scenarios.append({
            "name": f"Array conversion (n={size:,})",
            "stats": stats,
        })

    return scenarios


# ---------------------------------------------------------------------------
# pint benchmarks
# ---------------------------------------------------------------------------

def bench_pint_scalar(iterations: int) -> list[dict]:
    import pint  # type: ignore[import-untyped]
    ureg = pint.UnitRegistry()

    scenarios = []

    # 1. Unit creation
    stats = _bench(lambda: 5.0 * ureg.meter, iterations)
    scenarios.append({"name": "Unit creation", "stats": stats})

    # 2. Scale-only conversion (km -> m)
    km_val = 5.0 * ureg.kilometer
    stats = _bench(lambda: km_val.to(ureg.meter), iterations)
    scenarios.append({"name": "Scale-only conversion", "stats": stats})

    # 3. Graph conversion (m -> ft)
    m_val = 5.0 * ureg.meter
    stats = _bench(lambda: m_val.to(ureg.foot), iterations)
    scenarios.append({"name": "Graph conversion", "stats": stats})

    # 4. Temperature conversion (C -> F)
    c_val = ureg.Quantity(100, ureg.degC)
    stats = _bench(lambda: c_val.to(ureg.degF), iterations)
    scenarios.append({"name": "Temperature conversion", "stats": stats})

    # 5. Unit algebra (m / s)
    stats = _bench(lambda: ureg.meter / ureg.second, iterations)
    scenarios.append({"name": "Unit algebra", "stats": stats})

    return scenarios


def bench_pint_array(iterations: int, sizes: list[int]) -> list[dict]:
    import numpy as np
    import pint  # type: ignore[import-untyped]
    ureg = pint.UnitRegistry()

    scenarios = []
    for size in sizes:
        data = np.arange(size, dtype=float)

        # 6. Array creation
        stats = _bench(lambda: data * ureg.meter, iterations)
        scenarios.append({
            "name": f"Array creation (n={size:,})",
            "stats": stats,
        })

        # 7. Array conversion
        arr = data * ureg.meter
        stats = _bench(lambda: arr.to(ureg.foot), iterations)
        scenarios.append({
            "name": f"Array conversion (n={size:,})",
            "stats": stats,
        })

    return scenarios


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _print_scalar_table(
    ucon_results: list[dict],
    pint_results: list[dict] | None = None,
) -> None:
    if pint_results:
        header = f"{'Scenario':<28} {'ucon (median)':>14} {'pint (median)':>14} {'speedup':>10}"
        print(header)
        print("-" * len(header))
        for u, p in zip(ucon_results, pint_results):
            speedup = p["stats"]["median"] / u["stats"]["median"] if u["stats"]["median"] > 0 else float("inf")
            print(
                f"{u['name']:<28} "
                f"{_fmt_time(u['stats']['median']):>14} "
                f"{_fmt_time(p['stats']['median']):>14} "
                f"{speedup:>9.1f}x"
            )
    else:
        header = f"{'Scenario':<28} {'median':>12} {'p5':>12} {'p95':>12}"
        print(header)
        print("-" * len(header))
        for s in ucon_results:
            print(
                f"{s['name']:<28} "
                f"{_fmt_time(s['stats']['median']):>12} "
                f"{_fmt_time(s['stats']['p5']):>12} "
                f"{_fmt_time(s['stats']['p95']):>12}"
            )


def _print_array_table(
    ucon_results: list[dict],
    pint_results: list[dict] | None = None,
) -> None:
    if pint_results:
        header = f"{'Scenario':<34} {'ucon (median)':>14} {'pint (median)':>14} {'speedup':>10}"
        print(header)
        print("-" * len(header))
        for u, p in zip(ucon_results, pint_results):
            speedup = p["stats"]["median"] / u["stats"]["median"] if u["stats"]["median"] > 0 else float("inf")
            print(
                f"{u['name']:<34} "
                f"{_fmt_time(u['stats']['median']):>14} "
                f"{_fmt_time(p['stats']['median']):>14} "
                f"{speedup:>9.1f}x"
            )
    else:
        header = f"{'Scenario':<34} {'median':>12} {'p5':>12} {'p95':>12}"
        print(header)
        print("-" * len(header))
        for s in ucon_results:
            print(
                f"{s['name']:<34} "
                f"{_fmt_time(s['stats']['median']):>12} "
                f"{_fmt_time(s['stats']['p5']):>12} "
                f"{_fmt_time(s['stats']['p95']):>12}"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="ucon performance benchmarks")
    parser.add_argument(
        "--sizes", nargs="+", type=int, default=[1_000, 10_000, 100_000],
        help="Array sizes to benchmark (default: 1000 10000 100000)",
    )
    parser.add_argument(
        "--iterations", type=int, default=50,
        help="Number of iterations per scenario (default: 50)",
    )
    parser.add_argument(
        "--with-pint", action="store_true",
        help="Include pint comparison benchmarks",
    )
    args = parser.parse_args()

    print(f"Benchmarking with {args.iterations} iterations, array sizes: {args.sizes}")
    print(f"Python {sys.version.split()[0]}")

    # --- Graph load (isolated, in-process) ---
    _print_header("Graph Load (isolated)")
    graph_results = bench_graph_load(args.iterations)
    _print_load_table(graph_results)

    # --- Import time (subprocess-isolated) ---
    load_runs = min(args.iterations, 10)
    _print_header(f"Import Time (subprocess-isolated, {load_runs} runs)")
    import_results = bench_load_time(runs=load_runs)
    _print_load_table(import_results)

    # --- Scalar benchmarks ---
    _print_header("Scalar Operations")
    ucon_scalar = bench_ucon_scalar(args.iterations)

    pint_scalar = None
    if args.with_pint:
        try:
            pint_scalar = bench_pint_scalar(args.iterations)
        except ImportError:
            print("WARNING: pint not installed, skipping comparison")

    _print_scalar_table(ucon_scalar, pint_scalar)

    # --- Array benchmarks ---
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        print("\nNumPy not installed, skipping array benchmarks.")
        return

    _print_header("Array Operations")
    ucon_array = bench_ucon_array(args.iterations, args.sizes)

    pint_array = None
    if args.with_pint:
        try:
            pint_array = bench_pint_array(args.iterations, args.sizes)
        except ImportError:
            print("WARNING: pint not installed, skipping comparison")

    _print_array_table(ucon_array, pint_array)


if __name__ == "__main__":
    main()

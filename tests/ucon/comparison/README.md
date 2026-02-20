# Thread Safety and State Isolation: Pint vs ucon

**Date:** 2026-02-18
**Context:** Architectural comparison for MCP server and multi-agent deployments
**Test suites:** `test_pint_registry_isolation.py` (14 tests) · `test_ucon_graph_isolation.py` (16 tests) · All 30 passing

---

## The Core Problem

Unit conversion libraries hold state: which units exist, how they relate, what aliases are registered.
The question is how that state is scoped.

Pint scopes state to a `UnitRegistry` object. Quantities are bound to the registry that created them, and the library provides a process-global `application_registry` singleton for convenience.
This design works well for single-user scripts and notebooks.
It does not work for concurrent, multi-tenant, or multi-domain scenarios — precisely the scenarios that MCP servers and AI agent infrastructure demand.

ucon scopes state to a `ConversionGraph` value, managed via Python's `ContextVar` mechanism. Graphs are copied, extended immutably with `with_package()`, and scoped to execution contexts via `using_graph()`.
This design makes isolation the default and sharing the explicit choice.

This document describes the concrete scenarios where Pint's architecture creates correctness hazards that ucon's architecture avoids.

---

## Finding 1: Cross-Registry Quantity Incompatibility

Pint quantities carry a reference to the registry that created them.
Quantities from different registries cannot be added, subtracted, or compared even when they represent the same physical dimension with the same unit name.

```python
ureg1 = pint.UnitRegistry()
ureg2 = pint.UnitRegistry()

q1 = ureg1.Quantity(50, "meter")
q2 = ureg2.Quantity(50, "meter")

q1 + q2  # ValueError: Cannot operate with Quantity of different registries
q1 > q2  # ValueError
```

This is not a bug, but rather a design decision to prevent accidental mixing of incompatible unit systems.
It creates a fundamental tension: _you can either share_ a registry (risking mutation hazards) _or isolate_ registries (losing interoperability).
There is no middle ground.

**ucon's approach:** Conversion graphs produce plain numeric results via `Map` objects.
There is no `Quantity` type that carries a registry reference, so there is no cross-graph incompatibility problem.
Two graphs can produce results that are directly comparable because the results are numbers, not registry-bound objects.

---

## Finding 2: The Application Registry Singleton

Pint provides `pint.set_application_registry()`, a function that switches the process-global default registry.
Any code using `pint.Quantity` (as opposed to `ureg.Quantity`) is affected.

```python
ureg1 = pint.UnitRegistry()
ureg1.define("smoot = 1.7018 * meter")
pint.set_application_registry(ureg1)

pint.Quantity(1, "smoot")  # works

ureg2 = pint.UnitRegistry()
pint.set_application_registry(ureg2)

pint.Quantity(1, "smoot")  # UndefinedUnitError: smoot no longer exists
```

This is action at a distance.
Library A calls `set_application_registry()` and Library B's code breaks, with no call stack connecting the cause to the effect.

**ucon's approach:** `set_default_graph()` exists but only affects contexts that haven't explicitly called `using_graph()`.
An explicit `using_graph(base)` context is immune to default changes, providing defense in depth.

---

## Finding 3: Silent Redefinition

Pint's `define()` method can be called multiple times with the same unit name. The second call silently overwrites the first.
In Pint 0.25, the internal `_units` dictionary updates, but the conversion cache may retain stale values — producing an internally inconsistent state.

```python
ureg = pint.UnitRegistry()
ureg.define("widget = 100 * gram")
ureg._units["widget"].converter.scale  # 100

ureg.define("widget = 200 * gram")
ureg._units["widget"].converter.scale  # 200 (updated)

ureg.Quantity(1, "widget").to("gram")  # 100 gram (stale cache!)
```

The internal definition says 200g. The conversion returns 100g.
There is no error, no warning in the return value, and no mechanism for downstream code to detect that a redefinition occurred.

**ucon's approach:** `with_package()` returns a new graph.
The original graph is never mutated.
There is no redefinition, there is only a different graph that happens to have a different definition. Old and new coexist _without_ interference.

---

## Scenario Analysis: Where Thread Safety Matters

### Scenario 1: MCP Server Handling Concurrent Tool Calls

An MCP server is a long-running process serving multiple AI agents simultaneously.
Agent A requests a nursing dosage calculation (needs `gtt`, `dose`, `IU`).
Agent B requests an aerospace conversion (needs `slug`, `lbf`, `knot`).
Both requests arrive at the same time on different threads.

**With Pint**, two options exist:

- **Shared registry:** Agent A's `define("IU = 1e-6 * gram")` races with Agent B's unrelated `define()`.
Agent B's later requests might resolve nursing units it shouldn't see.
The `define()` calls are not atomic with respect to cache state.
- **Separate registries:** Each request pays the ~50ms startup cost of `UnitRegistry()`.
Results from Agent A and Agent B are incompatible `Quantity` objects that cannot be combined if a supervisory agent needs to compare them.

**With ucon**, the server holds one base `ConversionGraph`, calls `with_package()` per agent configuration (a cheap copy + extension), and scopes it via `using_graph()`.
The ContextVar mechanism provides per-thread isolation without synchronization overhead.
The test suite demonstrates this with 10 concurrent threads, each with a unique custom unit, verifying zero cross-contamination.

### Scenario 2: Test Parallelism (pytest-xdist)

pytest-xdist runs tests concurrently across workers.
`test_nursing.py` defines custom units on a shared registry.
`test_aerospace.py` defines different custom units.
When tests run in parallel, thread scheduling determines which `define()` call executes first.

**With Pint**, this produces intermittent failures.
Monday's CI passes, Tuesday's fails because thread scheduling changed the execution order of `define()` calls.
Each test passes in isolation; the failure only manifests under concurrent execution.

**With ucon**, each test uses `with ucon.using_graph(test_graph)` and the ContextVar scoping guarantees no test can observe another test's graph mutations.
The test suite verifies this by running 10 concurrent workers with a `threading.Barrier` to synchronize their start times.

### Scenario 3: Jupyter Notebook with Multiple Contexts

A researcher has two notebook cells: one for chemistry (needs `M` as molarity, mol/L), another for electrical engineering (needs `M` as mega prefix).
Both cells share one Python kernel and one Pint registry.

**With Pint**, defining `M` in the chemistry cell and running the EE cell afterward produces a naming collision.
Rerunning cells in different orders produces different results, because `define()` overwrites are order-dependent.

**With ucon**, each cell can use `with using_graph(chemistry_graph)` and `with using_graph(ee_graph)` independently.
Cell execution order is irrelevant because graph scoping is explicit.

---

## Architectural Summary

| Property | Pint | ucon |
|----------|------|------|
| State container | `UnitRegistry` (mutable) | `ConversionGraph` (copy-on-extend) |
| Global singleton | `application_registry` (process-wide) | None (ContextVar-scoped default) |
| Extension mechanism | `define()` (mutates in place) | `with_package()` (returns new graph) |
| Context scoping | None (manual registry passing) | `using_graph()` via ContextVar |
| Thread isolation | Requires separate registries | Built-in via ContextVar |
| Cross-context interop | Blocked (different-registry error) | Native (results are plain numbers) |
| Redefinition behavior | Silent overwrite + stale cache | Not possible (immutable extension) |
| Cache consistency | Can become inconsistent after `define()` | No cache — graph traversal is the conversion |

---

## The Tradeoff Pint Forces

Pint forces users to choose between two failure modes:

1. **Share a registry** → risk mutation, redefinition, name collision, thread races, and stale caches.
2. **Separate registries** → lose interoperability between quantities from different registries.

ucon eliminates this dilemma.
Graphs are values, not shared mutable objects.
You copy them, extend them, scope them to contexts, and discard them — the same way you work with immutable data structures in any concurrent system.

This is not hypothetical.
The test suites accompanying this document execute every scenario described above and verify the claimed behaviors against Pint 0.25.2 and ucon 0.7.4.

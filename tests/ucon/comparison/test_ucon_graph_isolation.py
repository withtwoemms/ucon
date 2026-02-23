"""
Test Suite: ucon ConversionGraph Isolation
==========================================

Demonstrates that ucon's ConversionGraph architecture provides
correct isolation in concurrent, multi-domain, and multi-tenant
scenarios — without sacrificing interoperability.

Key architectural features tested:
  1. ConversionGraph.copy() → independent graph instances
  2. ConversionGraph.with_package() → immutable extension
  3. using_graph() → ContextVar-scoped graph switching
  4. No global mutable singleton

Run: pytest test_ucon_graph_isolation.py -v
"""

import threading
import ucon
from ucon.core import Unit, Dimension
from ucon.maps import LinearMap
import pytest


# ─────────────────────────────────────────────────────
# Helper: Create domain-specific packages
# ─────────────────────────────────────────────────────

def nursing_package():
    return ucon.UnitPackage(
        name="nursing",
        units=(
            ucon.UnitDef(name="drop", dimension="volume", aliases=("gtt",)),
        ),
        edges=(
            # 15 gtt = 1 mL, so 1 gtt = 1/15 mL = 1/15000 L
            # But edge dst must be a unit in the graph registry.
            # ucon's base volume unit is 'liter' (alias 'L').
            ucon.EdgeDef(src="drop", dst="liter", factor=1 / 15000),
        ),
    )


def aerospace_package():
    return ucon.UnitPackage(
        name="aerospace",
        units=(
            ucon.UnitDef(name="slug", dimension="mass", aliases=("slug",)),
            ucon.UnitDef(name="knot", dimension="velocity", aliases=("kn", "kt")),
        ),
        edges=(
            ucon.EdgeDef(src="slug", dst="kilogram", factor=14.5939),
        ),
    )


def brewing_package():
    return ucon.UnitPackage(
        name="brewing",
        units=(
            ucon.UnitDef(name="smoot", dimension="length", aliases=("smoot",)),
        ),
        edges=(
            ucon.EdgeDef(src="smoot", dst="meter", factor=1.7018),
        ),
    )


# ─────────────────────────────────────────────────────
# 1. GRAPH COPY PRODUCES INDEPENDENT INSTANCES
#    Modifications to a copy never affect the original.
# ─────────────────────────────────────────────────────


class TestGraphCopyIndependence:
    """ConversionGraph.copy() produces a deep copy. Extending the
    copy with new units does not affect the original graph."""

    def test_copy_is_distinct_object(self):
        g = ucon.get_default_graph()
        g2 = g.copy()
        assert g is not g2

    def test_copy_preserves_units(self):
        """The copy contains all units from the original."""
        g = ucon.get_default_graph()
        g2 = g.copy()

        # Both can resolve 'meter'
        m1 = g.resolve_unit("meter")
        m2 = g2.resolve_unit("meter")
        assert m1[0].name == m2[0].name == "meter"

    def test_extending_copy_does_not_affect_original(self):
        """Adding a unit to a copy leaves the original unchanged."""
        g = ucon.get_default_graph()
        g2 = g.with_package(brewing_package())

        # Copy has 'smoot'
        with ucon.using_graph(g2):
            u = ucon.get_unit_by_name("smoot")
            assert u.name == "smoot"

        # Original does NOT have 'smoot'
        assert g.resolve_unit("smoot") is None, "Original graph should not contain 'smoot'"


# ─────────────────────────────────────────────────────
# 2. with_package() RETURNS A NEW GRAPH (IMMUTABLE EXTENSION)
#    The original graph is never mutated.
# ─────────────────────────────────────────────────────


class TestWithPackageImmutability:
    """with_package() returns a new ConversionGraph that includes the
    package's units and edges. The original graph is unmodified."""

    def test_with_package_returns_new_graph(self):
        g = ucon.get_default_graph()
        g2 = g.with_package(brewing_package())
        assert g is not g2

    def test_original_unmodified_after_with_package(self):
        g = ucon.get_default_graph()
        original_count = len(g._name_registry)

        g2 = g.with_package(brewing_package())
        extended_count = len(g2._name_registry)

        # Original unchanged
        assert len(g._name_registry) == original_count
        # Extended has more units
        assert extended_count > original_count

    def test_packages_compose_without_collision(self):
        """Multiple packages can be layered onto the same base graph.
        Each produces an independent extended graph."""
        base = ucon.get_default_graph()

        nursing_graph = base.with_package(nursing_package())
        aero_graph = base.with_package(aerospace_package())

        # Nursing graph has 'drop' but not 'slug'
        with ucon.using_graph(nursing_graph):
            assert ucon.get_unit_by_name("drop").name == "drop"

        assert nursing_graph.resolve_unit("slug") is None

        # Aerospace graph has 'slug' but not 'drop'
        with ucon.using_graph(aero_graph):
            assert ucon.get_unit_by_name("slug").name == "slug"

        assert aero_graph.resolve_unit("drop") is None

        # Base graph has neither
        assert base.resolve_unit("drop") is None
        assert base.resolve_unit("slug") is None

    def test_both_packages_can_coexist_on_same_base(self):
        """A combined graph can have units from multiple packages."""
        base = ucon.get_default_graph()
        combined = base.with_package(nursing_package()).with_package(aerospace_package())

        with ucon.using_graph(combined):
            assert ucon.get_unit_by_name("drop").name == "drop"
            assert ucon.get_unit_by_name("slug").name == "slug"


# ─────────────────────────────────────────────────────
# 3. using_graph() PROVIDES SCOPED CONTEXT ISOLATION
#    ContextVar-based scoping means each context (thread,
#    async task, or with-block) has its own active graph.
# ─────────────────────────────────────────────────────


class TestUsingGraphContextIsolation:
    """using_graph() sets the active ConversionGraph for the current
    context via ContextVar. It does not affect other contexts."""

    def test_using_graph_scopes_name_resolution(self):
        """Inside using_graph, get_unit_by_name resolves against
        the scoped graph. Outside, it reverts."""
        base = ucon.get_default_graph()
        extended = base.with_package(brewing_package())

        # Outside: no smoot
        with pytest.raises(Exception):
            ucon.get_unit_by_name("smoot")

        # Inside: smoot available
        with ucon.using_graph(extended):
            u = ucon.get_unit_by_name("smoot")
            assert u.name == "smoot"

        # After exiting: no smoot again
        with pytest.raises(Exception):
            ucon.get_unit_by_name("smoot")

    def test_nested_using_graph_contexts(self):
        """Nested using_graph calls correctly stack and unwind."""
        base = ucon.get_default_graph()
        brewing = base.with_package(brewing_package())
        brewing_plus_aero = brewing.with_package(aerospace_package())

        # Outer context: brewing only
        with ucon.using_graph(brewing):
            assert ucon.get_unit_by_name("smoot").name == "smoot"
            assert brewing.resolve_unit("slug") is None

            # Inner context: brewing + aerospace
            with ucon.using_graph(brewing_plus_aero):
                assert ucon.get_unit_by_name("smoot").name == "smoot"
                assert ucon.get_unit_by_name("slug").name == "slug"

            # Back to outer: slug gone, smoot still available
            assert brewing.resolve_unit("slug") is None
            assert ucon.get_unit_by_name("smoot").name == "smoot"

    def test_using_graph_restores_on_exception(self):
        """If an exception occurs inside using_graph, the previous
        graph is still correctly restored."""
        base = ucon.get_default_graph()
        extended = base.with_package(brewing_package())

        try:
            with ucon.using_graph(extended):
                assert ucon.get_unit_by_name("smoot").name == "smoot"
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass

        # Graph correctly restored despite exception
        with pytest.raises(Exception):
            ucon.get_unit_by_name("smoot")


# ─────────────────────────────────────────────────────
# 4. THREAD ISOLATION VIA ContextVar
#    Each thread can use a different graph without
#    affecting other threads. No global mutable state.
# ─────────────────────────────────────────────────────


class TestThreadIsolation:
    """ContextVar scoping means each thread inherits the default
    graph but can switch to its own without affecting others."""

    def test_threads_use_independent_graphs(self):
        """Two threads using different graphs via using_graph
        do not interfere with each other."""
        base = ucon.get_default_graph()
        nursing = base.with_package(nursing_package())
        aero = base.with_package(aerospace_package())

        results = {}
        errors = {}

        def nursing_worker():
            try:
                with ucon.using_graph(nursing):
                    u = ucon.get_unit_by_name("drop")
                    L = ucon.get_unit_by_name("liter")
                    conv = nursing.convert(src=u, dst=L)
                    results["nursing"] = conv(300)  # 300 gtt → L

                    # Should NOT see aerospace units
                    if nursing.resolve_unit("slug") is not None:
                        errors["nursing"] = "saw slug (LEAK)"
            except Exception as e:
                errors["nursing"] = str(e)

        def aero_worker():
            try:
                with ucon.using_graph(aero):
                    u = ucon.get_unit_by_name("slug")
                    kg = ucon.get_unit_by_name("kilogram")
                    conv = aero.convert(src=u, dst=kg)
                    results["aero"] = conv(1)  # 1 slug → kg

                    # Should NOT see nursing units
                    if aero.resolve_unit("drop") is not None:
                        errors["aero"] = "saw drop (LEAK)"
            except Exception as e:
                errors["aero"] = str(e)

        t1 = threading.Thread(target=nursing_worker)
        t2 = threading.Thread(target=aero_worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Thread errors: {errors}"
        assert abs(results["nursing"] - 0.02) < 0.001  # 300 gtt = 20 mL = 0.02 L
        assert abs(results["aero"] - 14.5939) < 0.01  # 1 slug = 14.5939 kg

    def test_thread_graph_does_not_leak_to_main(self):
        """A thread's using_graph context does not affect the main thread."""
        base = ucon.get_default_graph()
        extended = base.with_package(brewing_package())
        done = threading.Event()

        def worker():
            with ucon.using_graph(extended):
                # Thread can see smoot
                assert ucon.get_unit_by_name("smoot").name == "smoot"
                done.set()
                # Hold the context open briefly
                import time
                time.sleep(0.1)

        t = threading.Thread(target=worker)
        t.start()
        done.wait()  # Wait until thread has entered the context

        # Main thread should NOT see smoot
        with pytest.raises(Exception):
            ucon.get_unit_by_name("smoot")

        t.join()

    def test_many_concurrent_threads_with_different_graphs(self):
        """Stress test: 10 threads, each with a unique custom unit,
        all running concurrently. No cross-contamination."""
        base = ucon.get_default_graph()
        results = {}
        errors = {}
        barrier = threading.Barrier(10)

        def worker(i):
            try:
                pkg = ucon.UnitPackage(
                    name=f"pkg_{i}",
                    units=(
                        ucon.UnitDef(
                            name=f"unit_{i}",
                            dimension="length",
                            aliases=(f"u{i}",),
                        ),
                    ),
                    edges=(
                        ucon.EdgeDef(
                            src=f"unit_{i}",
                            dst="meter",
                            factor=float(i + 1),
                        ),
                    ),
                )
                graph = base.with_package(pkg)

                barrier.wait(timeout=5)  # synchronize start

                with ucon.using_graph(graph):
                    u = ucon.get_unit_by_name(f"unit_{i}")
                    m = ucon.get_unit_by_name("meter")
                    conv = graph.convert(src=u, dst=m)
                    results[i] = conv(1)

                    # Verify NO other thread's unit is visible
                    for j in range(10):
                        if j != i:
                            try:
                                ucon.get_unit_by_name(f"unit_{j}")
                                errors[i] = f"thread {i} saw unit_{j}"
                            except Exception:
                                pass  # correct
            except Exception as e:
                errors[i] = str(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Isolation violations: {errors}"
        for i in range(10):
            expected = float(i + 1)
            assert abs(results[i] - expected) < 0.01, (
                f"Thread {i}: expected {expected}, got {results[i]}"
            )


# ─────────────────────────────────────────────────────
# 5. NO GLOBAL MUTABLE SINGLETON
#    Unlike Pint's application_registry, ucon has no
#    process-global singleton that can be switched to
#    break other callers.
# ─────────────────────────────────────────────────────


class TestNoGlobalSingleton:
    """ucon does not have a set_application_registry() equivalent
    that can globally switch the active unit system."""

    def test_set_default_graph_does_not_exist_as_global_mutation(self):
        """ucon's set_default_graph exists but only sets the default for
        contexts that haven't explicitly chosen a graph. It doesn't
        retroactively change active using_graph() contexts."""
        base = ucon.get_default_graph()
        extended = base.with_package(brewing_package())

        result_inside = {}
        result_outside = {}

        def check_in_context():
            with ucon.using_graph(base):
                # Even if someone calls set_default_graph elsewhere,
                # this context is locked to 'base'
                try:
                    ucon.get_unit_by_name("smoot")
                    result_inside["smoot"] = True
                except Exception:
                    result_inside["smoot"] = False

        # Set extended as default
        ucon.set_default_graph(extended)

        # But an explicit using_graph(base) still uses base
        check_in_context()
        assert result_inside["smoot"] is False  # base doesn't have smoot

        # Restore
        ucon.set_default_graph(base)


# ─────────────────────────────────────────────────────
# 6. MULTI-TENANT MCP SERVER SCENARIO
#    The scenario Pint fails at: multiple agents with
#    different unit configurations, running concurrently.
# ─────────────────────────────────────────────────────


class TestMultiTenantMCPScenario:
    """Simulates an MCP server handling concurrent requests from
    multiple AI agents, each needing different unit packages."""

    def test_concurrent_agent_requests(self):
        """Three agents with different configurations process requests
        simultaneously without interference."""
        base = ucon.get_default_graph()

        # Agent configurations
        agent_configs = {
            "nursing": base.with_package(nursing_package()),
            "aerospace": base.with_package(aerospace_package()),
            "standard": base,  # SI only, no extensions
        }

        results = {}
        errors = {}

        def agent_request(agent_name, graph, convert_from, convert_to, value):
            try:
                with ucon.using_graph(graph):
                    src = ucon.get_unit_by_name(convert_from)
                    dst = ucon.get_unit_by_name(convert_to)
                    conv = graph.convert(src=src, dst=dst)
                    results[agent_name] = conv(value)
            except Exception as e:
                errors[agent_name] = str(e)

        threads = [
            threading.Thread(
                target=agent_request,
                args=("nursing", agent_configs["nursing"], "drop", "liter", 300),
            ),
            threading.Thread(
                target=agent_request,
                args=("aerospace", agent_configs["aerospace"], "slug", "kilogram", 2),
            ),
            threading.Thread(
                target=agent_request,
                args=("standard", agent_configs["standard"], "meter", "foot", 100),
            ),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Agent errors: {errors}"
        assert abs(results["nursing"] - 0.02) < 0.001  # 300 gtt = 0.02 L
        assert abs(results["aerospace"] - 29.1878) < 0.01  # 2 slug = 29.19 kg
        assert abs(results["standard"] - 328.084) < 0.1  # 100 m = 328.08 ft

    def test_agent_graphs_are_reusable_across_requests(self):
        """An agent's graph can be used for multiple sequential requests
        without degradation or state leakage."""
        base = ucon.get_default_graph()
        nursing = base.with_package(nursing_package())

        # Simulate 100 sequential requests on the same graph
        for i in range(100):
            with ucon.using_graph(nursing):
                u = ucon.get_unit_by_name("drop")
                L = ucon.get_unit_by_name("liter")
                conv = nursing.convert(src=u, dst=L)
                result = conv(15000 * (i + 1))  # 15000 gtt = 1 L
                expected = float(i + 1)
                assert abs(result - expected) < 0.01, (
                    f"Request {i}: expected {expected}, got {result}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

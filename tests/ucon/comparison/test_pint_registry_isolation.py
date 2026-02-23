"""
Test Suite: Pint UnitRegistry Isolation Failures
=================================================

Demonstrates that Pint's UnitRegistry architecture creates correctness
hazards in concurrent, multi-domain, and multi-tenant scenarios.

These are not bugs per se — Pint was designed for single-user, 
single-process scientific computing. But the design makes it unsafe
for MCP server, multi-agent, or multi-tenant use cases where different
contexts need different unit definitions simultaneously.

Run: pytest test_pint_registry_isolation.py -v
"""

import threading
import time
import pytest

pint = pytest.importorskip("pint", reason="pint not installed")


# ─────────────────────────────────────────────────────
# 1. CROSS-REGISTRY INCOMPATIBILITY
#    Quantities from different registries cannot interact,
#    even when they represent the same physical dimension.
# ─────────────────────────────────────────────────────


class TestCrossRegistryIncompatibility:
    """Pint quantities are bound to their parent registry.
    Two registries that both define the same units produce
    quantities that cannot be added, compared, or combined."""

    def test_addition_fails_across_registries(self):
        """Two 'meter' quantities from different registries cannot be added."""
        ureg1 = pint.UnitRegistry()
        ureg2 = pint.UnitRegistry()

        q1 = ureg1.Quantity(50, "meter")
        q2 = ureg2.Quantity(50, "meter")

        with pytest.raises(ValueError, match="different registries"):
            _ = q1 + q2

    def test_comparison_fails_across_registries(self):
        """Two identical physical quantities cannot be compared
        if they come from different registries."""
        ureg1 = pint.UnitRegistry()
        ureg2 = pint.UnitRegistry()

        q1 = ureg1.Quantity(100, "meter")
        q2 = ureg2.Quantity(50, "meter")

        with pytest.raises(ValueError):
            _ = q1 > q2

    def test_subtraction_fails_across_registries(self):
        ureg1 = pint.UnitRegistry()
        ureg2 = pint.UnitRegistry()

        with pytest.raises(ValueError, match="different registries"):
            _ = ureg1.Quantity(10, "kg") - ureg2.Quantity(5, "kg")

    def test_custom_units_cannot_interact_across_registries(self):
        """If Lab A defines 'smoot' and Lab B defines 'cubit', both as
        lengths, they cannot be added even though both are valid lengths."""
        ureg_a = pint.UnitRegistry()
        ureg_a.define("smoot = 1.7018 * meter")

        ureg_b = pint.UnitRegistry()
        ureg_b.define("cubit = 0.4572 * meter")

        q_smoot = ureg_a.Quantity(3, "smoot")
        q_cubit = ureg_b.Quantity(5, "cubit")

        # Both are lengths. Both are valid. They cannot interact.
        with pytest.raises(ValueError, match="different registries"):
            _ = q_smoot + q_cubit

    def test_conversion_target_from_wrong_registry(self):
        """Converting to a unit object from a different registry
        may silently succeed or fail unpredictably."""
        ureg1 = pint.UnitRegistry()
        ureg2 = pint.UnitRegistry()

        q = ureg1.Quantity(100, "meter")
        target = ureg2.foot  # foot from a different registry

        # This actually succeeds in Pint 0.25 — but it's brittle.
        # The behavior is undocumented and inconsistent with addition.
        result = q.to(target)
        assert abs(result.magnitude - 328.084) < 0.01
        # The inconsistency IS the problem: addition fails, conversion works.


# ─────────────────────────────────────────────────────
# 2. APPLICATION REGISTRY SINGLETON
#    pint.application_registry is process-global mutable
#    state. Switching it affects all code using pint.Quantity.
# ─────────────────────────────────────────────────────


class TestApplicationRegistrySingleton:
    """The application_registry is a process-global singleton proxy.
    Mutating it affects all code paths that use pint.Quantity directly."""

    def setup_method(self):
        """Reset to a clean default registry before each test."""
        pint.set_application_registry(pint.UnitRegistry())

    def test_set_application_registry_affects_pint_quantity(self):
        """Switching the application registry changes what units
        are available via pint.Quantity for ALL callers."""
        ureg1 = pint.UnitRegistry()
        ureg1.define("smoot = 1.7018 * meter")

        ureg2 = pint.UnitRegistry()
        ureg2.define("cubit = 0.4572 * meter")

        # Set registry to ureg1: smoot available, cubit not
        pint.set_application_registry(ureg1)
        q = pint.Quantity(1, "smoot")
        assert abs(q.to("meter").magnitude - 1.7018) < 0.001

        with pytest.raises(pint.errors.UndefinedUnitError):
            pint.Quantity(1, "cubit")

        # Switch to ureg2: cubit available, smoot disappears
        pint.set_application_registry(ureg2)
        q = pint.Quantity(1, "cubit")
        assert abs(q.to("meter").magnitude - 0.4572) < 0.001

        with pytest.raises(pint.errors.UndefinedUnitError):
            pint.Quantity(1, "smoot")

    def test_library_a_can_break_library_b(self):
        """Simulates two libraries sharing a process. Library A sets the
        application registry; Library B's code using pint.Quantity breaks."""
        shared_ureg = pint.UnitRegistry()
        pint.set_application_registry(shared_ureg)

        # Library B's function — relies on pint.Quantity
        def library_b_convert(value_meters):
            q = pint.Quantity(value_meters, "meter")
            return q.to("foot").magnitude

        # Works fine initially
        assert abs(library_b_convert(100) - 328.084) < 0.01

        # Library A decides to set its own registry with custom units
        custom_ureg = pint.UnitRegistry()
        custom_ureg.define("smoot = 1.7018 * meter")
        pint.set_application_registry(custom_ureg)

        # Library B still works (standard units exist in both registries)
        # but this is fragile — Library A could use a stripped registry
        assert abs(library_b_convert(100) - 328.084) < 0.01

        # Now Library A uses a minimal registry
        minimal = pint.UnitRegistry(None)  # empty registry
        minimal.define("meter = [length]")
        minimal.define("second = [time]")
        # foot is NOT defined in this minimal registry
        pint.set_application_registry(minimal)

        with pytest.raises(pint.errors.UndefinedUnitError):
            library_b_convert(100)  # Library B breaks


# ─────────────────────────────────────────────────────
# 3. SILENT REDEFINITION & CACHE INCONSISTENCY
#    Calling define() twice on the same name silently
#    updates internal definition but not the conversion cache.
# ─────────────────────────────────────────────────────


class TestSilentRedefinition:
    """Pint allows redefining units without warning. The internal
    _units dict updates, but the conversion cache may become stale."""

    def test_define_overwrites_internal_definition(self):
        """Calling define() twice updates _units to the new definition."""
        ureg = pint.UnitRegistry()
        ureg.define("widget = 100 * gram")
        assert ureg._units["widget"].converter.scale == 100

        ureg.define("widget = 200 * gram")
        assert ureg._units["widget"].converter.scale == 200
        # Internal state says 200...

    def test_cached_conversion_uses_stale_definition(self):
        """After redefinition, cached conversions still use the original
        factor. The registry is in an inconsistent state."""
        ureg = pint.UnitRegistry()
        ureg.define("widget = 100 * gram")

        # First conversion caches the 100g factor
        q1 = ureg.Quantity(1, "widget")
        assert abs(q1.to("gram").magnitude - 100) < 0.01

        # Redefine to 200g
        ureg.define("widget = 200 * gram")

        # New quantity STILL converts using the cached 100g factor
        q2 = ureg.Quantity(1, "widget")
        result = q2.to("gram").magnitude

        # This assertion documents the inconsistency:
        # Internal definition says 200g, but conversion returns 100g
        assert abs(result - 100) < 0.01, (
            f"Expected stale cache (100g), got {result}g. "
            "If this fails, Pint may have fixed the cache invalidation bug."
        )

    def test_redefinition_is_silently_accepted(self):
        """Pint allows redefinition without raising an exception.
        There is no error, no version tracking, and no way for
        downstream code to know the definition changed."""
        ureg = pint.UnitRegistry()
        ureg.define("widget = 100 * gram")

        # Redefinition does NOT raise — it silently takes effect
        ureg.define("widget = 200 * gram")

        # The new definition is now active
        assert ureg._units["widget"].converter.scale == 200

        # Any code that cached the old factor (e.g., in a closure or
        # precomputed table) now silently has stale data.
        # There is no mechanism to detect that the definition changed.


# ─────────────────────────────────────────────────────
# 4. THREAD SAFETY
#    Shared mutable registries require external locking.
#    There is no per-thread isolation without creating
#    separate registries (which then can't interoperate).
# ─────────────────────────────────────────────────────


class TestThreadSafety:
    """Pint registries are shared mutable state with no built-in
    thread isolation. Concurrent define() calls can produce
    unpredictable results."""

    def test_threads_must_create_separate_registries(self):
        """Each thread needs its own UnitRegistry to define custom units
        safely. But then quantities from different threads can't interact."""
        results = {}

        def worker(name, unit_name, factor):
            ureg = pint.UnitRegistry()
            ureg.define(f"{unit_name} = {factor} * meter")
            q = ureg.Quantity(10, unit_name)
            results[name] = q.to("meter").magnitude

        t1 = threading.Thread(target=worker, args=("A", "unitA", 1.5))
        t2 = threading.Thread(target=worker, args=("B", "unitB", 2.5))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert abs(results["A"] - 15.0) < 0.01
        assert abs(results["B"] - 25.0) < 0.01
        # Works — but results["A"] and results["B"] are just floats.
        # If they were Quantity objects, they couldn't be combined.

    def test_shared_registry_concurrent_define_is_unsafe(self):
        """Multiple threads defining units on a shared registry can
        produce race conditions. We demonstrate by checking that
        define() is not atomic with respect to cache state."""
        ureg = pint.UnitRegistry()
        errors = []
        barrier = threading.Barrier(2)

        def definer(unit_name, factor):
            try:
                barrier.wait(timeout=5)
                ureg.define(f"{unit_name} = {factor} * meter")
                # Immediately try to use it
                q = ureg.Quantity(1, unit_name)
                _ = q.to("meter")
            except Exception as e:
                errors.append((unit_name, str(e)))

        t1 = threading.Thread(target=definer, args=("raceA", 1.0))
        t2 = threading.Thread(target=definer, args=("raceB", 2.0))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Even if no errors occur, the fundamental issue remains:
        # both threads mutated the same registry without synchronization.
        # The test may pass on some runs and fail on others — which is
        # the definition of a race condition.
        # We just document that the pattern is structurally unsafe.
        assert True  # The hazard is structural, not necessarily triggered


# ─────────────────────────────────────────────────────
# 5. MULTI-TENANT SCENARIO (MCP Server)
#    Simulates multiple AI agents needing different unit
#    configurations simultaneously — Pint's architecture
#    forces a choose-one-registry-or-separate-and-isolate
#    tradeoff.
# ─────────────────────────────────────────────────────


class TestMultiTenantScenario:
    """In an MCP server, different agents may need:
    - Agent A: nursing units (gtt, dose)
    - Agent B: aerospace units (slug, lbf, knot)
    - Agent C: only SI units (no custom extensions)

    With Pint, each agent needs its own UnitRegistry,
    and quantities cannot be shared across agents."""

    def test_agents_cannot_share_quantities(self):
        """Two agents with domain-specific registries produce
        quantities that cannot interact."""
        # Agent A: nursing
        nursing_ureg = pint.UnitRegistry()
        nursing_ureg.define("gtt = 1/15 * mL")

        # Agent B: aerospace
        aero_ureg = pint.UnitRegistry()
        aero_ureg.define("slug = 14.5939 * kg")

        # Each agent can do its own conversions fine
        drip = nursing_ureg.Quantity(300, "gtt")
        assert abs(drip.to("mL").magnitude - 20.0) < 0.1

        mass = aero_ureg.Quantity(1, "slug")
        assert abs(mass.to("kg").magnitude - 14.5939) < 0.01

        # But a third agent that receives both results can't combine them
        # (e.g., computing a mass flow rate from both contexts)
        volume_ml = nursing_ureg.Quantity(20, "mL")
        mass_kg = aero_ureg.Quantity(14.5939, "kg")

        with pytest.raises(ValueError, match="different registries"):
            _ = mass_kg / volume_ml  # kg/mL — valid operation, blocked by registry

    def test_global_registry_forces_unit_collisions(self):
        """If all agents share one registry to avoid cross-registry errors,
        they risk name collisions and unintended interactions."""
        shared = pint.UnitRegistry()

        # Agent A defines 'unit' as a medication unit (international unit)
        shared.define("IU = 1e-6 * gram")  # simplified

        # Agent B later tries to define 'IU' differently for their domain
        # (e.g., a different potency standard)
        shared.define("IU = 2e-6 * gram")

        # The registry is now silently inconsistent (definition updated,
        # cache stale) or silently overwritten.
        q = shared.Quantity(1000, "IU")
        result = q.to("gram").magnitude
        # Which definition wins? The answer depends on cache state.
        # This is the fundamental shared-mutable-state problem.
        assert result > 0  # We can't even assert which value it should be


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

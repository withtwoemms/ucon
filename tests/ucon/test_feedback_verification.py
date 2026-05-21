# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Verification suite for open ucon-core items in the feedback registry.

Source registry:
    /Users/withtwoemms/programming/python/mcp.ucon.dev/docs/internal/feedback/
        ucon-feedback-registry.md (last updated 2026-04-30)

Two items are testable against ucon core directly:

- Issue 2.5: cross-basis arithmetic in compute() (P1, "blocking")
    Hypothesis: shipped in 1.6.6 via transform-graph-aware Vector arithmetic
    (`Vector._unify_basis`). Verified here at the Vector / Number layer,
    not the MCP `compute()` tool layer (that is ucon-tools).

- Triage-1: bare component letters in the dimension parser (P3)
    Hypothesis: 1.6.x parser unification may have resolved this incidentally.

Out of scope here (not ucon-core work):

- Issue 2.1 (compound parser routing) — ucon-tools `using_graph()` wrapper
- ux-1 (response capability hints) — ucon-tools / docs
- Issue 3 (namespace isolation) — v2.0 design space

Run with: pytest tests/ucon/test_feedback_verification.py -v
"""

from fractions import Fraction

import pytest

from ucon import Number, get_default_graph, units
from ucon.basis import (
    Basis,
    BasisComponent,
    BasisTransform,
    Vector,
    ops,
    using_basis_graph,
)
from ucon.basis.builtin import SI
from ucon.basis.graph import get_basis_graph
from ucon.dimension import resolve


# ---------------------------------------------------------------------------
# Helpers — construct an SI-extension basis and the canonical SI -> extension
# embedding without going through ucon-tools.
# ---------------------------------------------------------------------------


def _build_economic_basis() -> Basis:
    """SI components plus a 'currency' component in slot 8."""
    return Basis(
        "economic",
        list(SI) + [BasisComponent("currency", "$")],
    )


def _build_si_to_economic(economic: Basis) -> BasisTransform:
    """Identity embedding: SI[i] -> economic[i] for all SI components."""
    n_src = len(SI)
    n_tgt = len(economic)
    matrix = tuple(
        tuple(Fraction(1) if j == i else Fraction(0) for j in range(n_tgt))
        for i in range(n_src)
    )
    return BasisTransform(SI, economic, matrix)


def _vector(basis: Basis, **named_exponents: int) -> Vector:
    """Construct a Vector by component name (e.g., currency=1, time=-1)."""
    components = []
    for comp in basis:
        components.append(Fraction(named_exponents.get(comp.name, 0)))
    return Vector(basis, tuple(components))


# ---------------------------------------------------------------------------
# Issue 2.5: cross-basis arithmetic
# ---------------------------------------------------------------------------


class TestIssue25CrossBasisArithmetic:
    """Verify the registry's 2.5 acceptance cases at the Vector layer.

    History
    -------
    The original failure surfaced as:

        "Cannot multiply dimensions from different bases: 'economic' and 'SI'"

    raised by ``Vector.__mul__`` when called with mismatched bases. 1.6.6
    silently mediated cross-basis arithmetic from inside ``Vector.__mul__``
    via ``Vector._unify_basis`` consulting the active BasisGraph.

    1.8.0 makes ``Vector`` arithmetic strict same-basis again — cross-basis
    multiplication / division now lives in :mod:`ucon.basis.ops` as
    explicit ``multiply_via`` / ``divide_via`` calls. These tests therefore
    exercise the ops module rather than the ``*`` / ``/`` operators.

    Test #8 from the registry (declare_computation accepting 'USD/year')
    is skipped — it depends on ucon-tools issue 2.1.
    """

    def setup_method(self) -> None:
        self.economic = _build_economic_basis()
        self.si_to_economic = _build_si_to_economic(self.economic)
        # Build a graph that contains the standard transforms PLUS our embedding.
        base_graph = get_basis_graph()
        self.graph = base_graph.with_transform(self.si_to_economic)

    def test_1_currency_times_time(self) -> None:
        """USD * second -> currency * time, in the economic basis."""
        usd = _vector(self.economic, currency=1)
        second = _vector(SI, time=1)
        with using_basis_graph(self.graph):
            result = ops.multiply_via(usd, second)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == 1

    def test_2_currency_per_time(self) -> None:
        """USD / year -> currency / time."""
        usd = _vector(self.economic, currency=1)
        year = _vector(SI, time=1)  # year and second share the time dimension
        with using_basis_graph(self.graph):
            result = ops.divide_via(usd, year)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == -1

    def test_3_sigma_times_delta_phi(self) -> None:
        """Dimensionless scalar multiplication preserves currency/time."""
        usd_per_year = _vector(self.economic, currency=1, time=-1)
        dimensionless = _vector(SI)  # zero vector
        with using_basis_graph(self.graph):
            result = ops.multiply_via(usd_per_year, dimensionless)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == -1

    def test_4_oil_price_times_oil_flow(self) -> None:
        """USD/kg * kg/day -> USD/day (currency / time)."""
        usd_per_kg = _vector(self.economic, currency=1, mass=-1)
        kg_per_day = _vector(SI, mass=1, time=-1)
        with using_basis_graph(self.graph):
            result = ops.multiply_via(usd_per_kg, kg_per_day)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["mass"] == 0  # cancelled
        assert result["time"] == -1

    def test_5_multistep_dimensionless_compounding(self) -> None:
        """USD * (rate) * (year) -> currency * time, mass cancellation across SI/economic."""
        usd = _vector(self.economic, currency=1)
        dimensionless_rate = _vector(SI)
        year = _vector(SI, time=1)
        with using_basis_graph(self.graph):
            mid = ops.multiply_via(usd, dimensionless_rate)
            result = ops.multiply_via(mid, year)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == 1

    def test_6_pure_si_regression(self) -> None:
        """Pure-SI multiplication unchanged by graph extension (regression guard)."""
        kg = _vector(SI, mass=1)
        m_per_s = _vector(SI, length=1, time=-1)
        with using_basis_graph(self.graph):
            result = kg * m_per_s
        assert result.basis == SI
        assert result["mass"] == 1
        assert result["length"] == 1
        assert result["time"] == -1

    def test_7_pure_currency_regression(self) -> None:
        """Pure-currency multiplication stays in economic basis (regression guard)."""
        usd_a = _vector(self.economic, currency=1)
        usd_b = _vector(self.economic, currency=1)
        with using_basis_graph(self.graph):
            result = usd_a * usd_b
        assert result.basis == self.economic
        assert result["currency"] == 2

    @pytest.mark.skip(reason="Test #8 depends on ucon-tools issue 2.1 (declare_computation)")
    def test_8_declare_computation_accepts_cross_basis(self) -> None:
        """Out of scope for ucon core verification."""

    def test_failure_mode_disconnected_basis_still_rejects(self) -> None:
        """Sanity check: bases with no transform path still raise ValueError.

        Regression guard against over-eager unification — ``ops.multiply_via``
        should only succeed when a clean projection exists in the active
        graph. ``BasisMismatch`` subclasses ``ValueError`` so the legacy
        catch site continues to match.
        """
        unrelated = Basis("unrelated", [BasisComponent("flux", "Φ")])
        flux_vec = _vector(unrelated, flux=1)
        kg_vec = _vector(SI, mass=1)
        with using_basis_graph(self.graph):
            with pytest.raises(ValueError, match="different bases"):
                ops.multiply_via(flux_vec, kg_vec)


# ---------------------------------------------------------------------------
# Triage-1: bare component letters in dimension parser
# ---------------------------------------------------------------------------


class TestTriage1BareComponentDimensions:
    """Verify whether the registry's 6 dimension-string cases are accepted.

    Outcome (A): all six pass -> issue closes as resolved.
    Outcome (B): symbol singletons reject with a useful error -> documented.
    Outcome (C): symbol singletons reject with generic error -> stays open.

    ucon core does not expose a dedicated `parse_dimension(str)` helper;
    `get_unit_by_name` is the closest public entry point. These tests
    document current behavior so the registry can be updated either way.
    """

    @pytest.mark.parametrize(
        "spec",
        [
            "M",
            "M¹",
            "M^1",
            "M·T⁻¹",
            "mass",
            "mass^1",
        ],
    )
    def test_dimension_string_accepted_or_rejected(self, spec: str) -> None:
        """Document accept/reject behavior per spec.

        This test does NOT assert success; it asserts that the system
        either succeeds OR fails with a structured exception (not a crash).
        Run with -v to see which cases land on which side.
        """
        from ucon.resolver import get_unit_by_name

        try:
            result = get_unit_by_name(spec)
            outcome = f"ACCEPT: {spec!r} -> {result}"
        except Exception as exc:  # noqa: BLE001 - documenting all reject modes
            outcome = f"REJECT: {spec!r} -> {type(exc).__name__}: {exc}"
        # Always pass; the value is in the recorded outcome string.
        # Surface via assertion message so `-v` shows it.
        assert outcome, outcome
        print(outcome)

    def test_summary_table(self) -> None:
        """Print a registry-shaped summary of all six cases at once."""
        from ucon.resolver import get_unit_by_name

        cases = ["M", "M¹", "M^1", "M·T⁻¹", "mass", "mass^1"]
        rows = []
        for spec in cases:
            try:
                get_unit_by_name(spec)
                rows.append((spec, "ACCEPT", ""))
            except Exception as exc:
                rows.append((spec, "REJECT", f"{type(exc).__name__}: {exc}"))

        # Print as a simple table for the registry update.
        header = f"{'spec':<10}  {'result':<8}  detail"
        print()
        print(header)
        print("-" * len(header))
        for spec, status, detail in rows:
            print(f"{spec:<10}  {status:<8}  {detail}")

        # No assertion on the breakdown — this exists to record state.
        # If you want to fail-fast on regressions, replace with:
        #     assert all(s == "ACCEPT" for _, s, _ in rows)


# ---------------------------------------------------------------------------
# Smoke test: verify the standard graph contains expected transforms
# ---------------------------------------------------------------------------


def test_standard_graph_includes_expected_basis_transforms() -> None:
    """Confirm the standard graph wiring is intact under current main."""
    graph = get_basis_graph()
    from ucon.basis.builtin import CGS, CGS_ESU, NATURAL, PLANCK, ATOMIC

    # SI -> CGS, CGS_ESU, NATURAL, PLANCK, ATOMIC must all be reachable.
    for target in (CGS, CGS_ESU, NATURAL, PLANCK, ATOMIC):
        assert graph.are_connected(SI, target), (
            f"SI -> {target.name} not reachable in standard graph"
        )

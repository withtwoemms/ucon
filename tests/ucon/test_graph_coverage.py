# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests targeting uncovered lines in ucon.graph.

Coverage gaps addressed:
- add_edge basis_graph validation (NoTransformPath)
- _add_cross_basis_edge DimensionMismatch on bad transform
- package_constants property
- with_package / _package_edge_already_covered
- _convert_units connected-basis ConversionNotFound
- _bfs_convert_cross_dimensional (success path)
- _bfs_product_path multi-hop and failure paths
- _convert_products resolve-via-shorthand fallback (same dim & cross dim)
- _convert_factorwise duplicate effective vectors, structure mismatch,
  exponent mismatch, pseudo-dimension isolation, cross-dim factor failure
- conversion cache hit
"""

import unittest

from ucon import Dimension, units
from ucon.basis import Basis, BasisComponent, BasisGraph, BasisTransform
from ucon.basis.builtin import SI, CGS
from ucon.basis.transforms import CGS_TO_SI
from ucon.core import RebasedUnit, Scale, Unit, UnitFactor, UnitProduct
from ucon.graph import (
    ConversionGraph,
    ConversionNotFound,
    CyclicInconsistency,
    DimensionMismatch,
    get_default_graph,
    reset_default_graph,
    using_graph,
)
from ucon.maps import LinearMap, AffineMap, Map


# -----------------------------------------------------------------------
# add_edge: basis_graph validation raises NoTransformPath
# Covers lines 167→175, 171-172
# -----------------------------------------------------------------------
class TestAddEdgeBasisGraphValidation(unittest.TestCase):
    """add_edge raises NoTransformPath when basis_graph rejects unconnected bases."""

    def test_disconnected_bases_raise_no_transform_path(self):
        from ucon.basis import NoTransformPath

        # Create two disconnected bases
        comp_a = BasisComponent("X", "X")
        comp_b = BasisComponent("Y", "Y")
        basis_a = Basis("alpha", (comp_a,))
        basis_b = Basis("beta", (comp_b,))

        dim_a = Dimension.from_components(basis_a, **{comp_a.name: 1}, name="dim_a")
        dim_b = Dimension.from_components(basis_b, **{comp_b.name: 1}, name="dim_b")

        unit_a = Unit(name="ua", dimension=dim_a)
        unit_b = Unit(name="ub", dimension=dim_b)

        bg = BasisGraph()
        graph = ConversionGraph()
        graph._basis_graph = bg

        with self.assertRaises(NoTransformPath):
            graph.add_edge(src=unit_a, dst=unit_b, map=LinearMap(1))

    def test_connected_bases_no_raise(self):
        """Same basis or connected bases should not raise."""
        graph = ConversionGraph()
        graph._basis_graph = BasisGraph()
        # Same basis — no raise
        graph.add_edge(src=units.meter, dst=units.foot, map=LinearMap(3.28084))
        m = graph.convert(src=units.meter, dst=units.foot)
        self.assertAlmostEqual(m(1), 3.28084, places=4)


# -----------------------------------------------------------------------
# _add_cross_basis_edge: DimensionMismatch on bad transform
# Covers line 252
# -----------------------------------------------------------------------
class TestCrossBasisEdgeDimensionMismatch(unittest.TestCase):
    """_add_cross_basis_edge raises when transform doesn't map to dst's dimension."""

    def test_transform_dimension_mismatch(self):
        # Identity transform within SI maps length→length, not length→mass
        bt = BasisTransform.identity(SI)
        graph = ConversionGraph()

        with self.assertRaises(DimensionMismatch) as ctx:
            graph.add_edge(
                src=units.meter,
                dst=units.kilogram,  # mass, not length
                map=LinearMap(1),
                basis_transform=bt,
            )
        self.assertIn("does not map", str(ctx.exception))


# -----------------------------------------------------------------------
# package_constants property
# Covers line 303
# -----------------------------------------------------------------------
class TestPackageConstants(unittest.TestCase):
    """package_constants returns the stored tuple."""

    def test_default_package_constants_empty(self):
        graph = ConversionGraph()
        self.assertEqual(graph.package_constants, ())

    def test_package_constants_returns_set_value(self):
        graph = ConversionGraph()
        graph._package_constants = ("a", "b")
        self.assertEqual(graph.package_constants, ("a", "b"))


# -----------------------------------------------------------------------
# _convert_units: connected bases but no rebased edge
# Covers lines 617-626
# -----------------------------------------------------------------------
class TestConvertUnitsConnectedBasisNoEdge(unittest.TestCase):
    """ConversionNotFound when bases connected but no rebased edge registered."""

    def test_connected_bases_no_rebased_edge(self):
        graph = ConversionGraph()
        graph._basis_graph = get_default_graph()._basis_graph

        # CGS unit without a rebased edge to SI
        cgs_dim = Dimension.from_components(CGS, length=1, mass=1, name="cgs_custom_dim")
        cgs_unit = Unit(name="cgs_custom", dimension=cgs_dim)

        # SI unit in a dimension that could be reached if rebased edge existed
        si_dim = Dimension.from_components(SI, length=1, mass=1, name="si_custom_dim")
        si_unit = Unit(name="si_custom", dimension=si_dim)

        # Register units so BFS can at least see them
        graph._ensure_dimension(cgs_dim)
        graph._ensure_dimension(si_dim)
        graph._unit_edges[cgs_dim][cgs_unit] = {}
        graph._unit_edges[si_dim][si_unit] = {}

        with self.assertRaises(ConversionNotFound) as ctx:
            graph.convert(src=cgs_unit, dst=si_unit)
        self.assertIn("no rebased unit edge", str(ctx.exception).lower())


# -----------------------------------------------------------------------
# _bfs_convert_cross_dimensional: success path
# Covers line 690
# -----------------------------------------------------------------------
class TestCrossDimensionalBFS(unittest.TestCase):
    """Cross-dimensional BFS finds path through context edges."""

    def test_cross_dimensional_path_via_context(self):
        from ucon.contexts import spectroscopy, using_context
        # spectroscopy context adds meter→hertz (cross-dimensional)
        with using_context(spectroscopy):
            graph = get_default_graph()
            m = graph.convert(src=units.meter, dst=units.hertz)
            # c / lambda: 1 m → 299792458 Hz
            self.assertAlmostEqual(m(1), 299792458.0, places=0)


# -----------------------------------------------------------------------
# _bfs_product_path: multi-hop through product edges
# Covers lines 712, 725-736 (product BFS multi-hop)
# -----------------------------------------------------------------------
class TestBFSProductPathMultiHop(unittest.TestCase):
    """_bfs_product_path finds paths through multiple product edges."""

    def test_multi_hop_product_edges(self):
        graph = ConversionGraph()
        a = Unit(name="a_vol", dimension=Dimension.volume)
        b = Unit(name="b_vol", dimension=Dimension.volume)
        c = Unit(name="c_vol", dimension=Dimension.volume)

        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)
        pc = UnitProduct.from_unit(c)

        graph.add_edge(src=pa, dst=pb, map=LinearMap(2))
        graph.add_edge(src=pb, dst=pc, map=LinearMap(3))

        # Call _bfs_product_path directly to exercise multi-hop BFS
        m = graph._bfs_product_path(src=pa, dst=pc)
        self.assertAlmostEqual(m(1), 6.0, places=6)


# -----------------------------------------------------------------------
# _bfs_product_path: no path raises ConversionNotFound
# Covers line 766
# -----------------------------------------------------------------------
class TestBFSProductPathNoPath(unittest.TestCase):
    """_bfs_product_path raises when no product path exists."""

    def test_no_product_path_raises(self):
        graph = ConversionGraph()
        a = Unit(name="vol_a", dimension=Dimension.volume)
        b = Unit(name="vol_b", dimension=Dimension.volume)

        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)

        # No edges registered at all; factorwise will invoke _bfs_product_path
        # which should raise.
        # But _bfs_product_path is only called from _convert_factorwise
        # for cross-dimension factors. Let's trigger it directly:
        with self.assertRaises(ConversionNotFound):
            graph._bfs_product_path(src=pa, dst=pb)


# -----------------------------------------------------------------------
# _convert_products: resolve via shorthand (same-dimension path)
# Covers lines 832-846
# -----------------------------------------------------------------------
class TestConvertProductsResolveViaShorthand(unittest.TestCase):
    """_convert_products resolves multi-factor products to atomic units via shorthand."""

    def test_same_dimension_resolve_shorthand(self):
        graph = get_default_graph()

        # pascal_second has shorthand "Pa·s" and is a registered atomic unit.
        # Create a multi-factor UnitProduct that represents Pa·s structurally.
        pa_s_product = UnitProduct({
            UnitFactor(units.pascal, Scale.one): 1,
            UnitFactor(units.second, Scale.one): 1,
        })
        pas_atomic = UnitProduct.from_unit(units.pascal_second)

        # These have the same dimension (dynamic_viscosity).
        # The shorthand resolution should find pascal_second for both.
        m = graph.convert(src=pas_atomic, dst=pa_s_product)
        self.assertAlmostEqual(m(1), 1.0, places=6)


# -----------------------------------------------------------------------
# _convert_products: resolve via shorthand falls through to factorwise
# Covers lines 845-846 (ConversionNotFound/DimensionMismatch catch)
# -----------------------------------------------------------------------
class TestConvertProductsResolveFallthrough(unittest.TestCase):
    """Shorthand resolution falls through when _convert_units fails."""

    def test_shorthand_resolve_fallthrough_to_factorwise(self):
        # This tests the case where shorthand resolves to units, but
        # _convert_units fails, falling through to factorwise.
        graph = ConversionGraph()
        a = Unit(name="alpha", dimension=Dimension.length, aliases=("alph",))
        b = Unit(name="beta", dimension=Dimension.length, aliases=("bet",))

        graph.register_unit(a)
        graph.register_unit(b)
        # Register edge so factorwise can succeed
        graph.add_edge(src=a, dst=b, map=LinearMap(2.5))

        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)

        m = graph.convert(src=pa, dst=pb)
        self.assertAlmostEqual(m(1), 2.5, places=6)


# -----------------------------------------------------------------------
# _convert_products: cross-basis dim mismatch fallback via resolve_unit
# Covers lines 789-799 (dimension mismatch branch with resolve_unit)
# -----------------------------------------------------------------------
class TestConvertProductsCrossBasisFallback(unittest.TestCase):
    """Products with mismatched dimensions fall back to Unit-level cross-basis."""

    def test_poise_product_cross_basis_via_resolve(self):
        graph = get_default_graph()
        # poise is CGS dynamic viscosity, pascal_second is SI dynamic viscosity
        # Their UnitProduct wrappers have different dimensions.
        src = UnitProduct.from_unit(units.poise)
        dst = UnitProduct.from_unit(units.pascal_second)
        m = graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1), 0.1, places=5)

    def test_dim_mismatch_no_resolution_raises(self):
        """When neither product resolves to a unit, DimensionMismatch is raised."""
        graph = ConversionGraph()
        comp_x = BasisComponent("X", "X")
        comp_y = BasisComponent("Y", "Y")
        basis_x = Basis("bx", (comp_x,))
        basis_y = Basis("by", (comp_y,))

        dim_x = Dimension.from_components(basis_x, **{comp_x.name: 1}, name="dx")
        dim_y = Dimension.from_components(basis_y, **{comp_y.name: 1}, name="dy")

        ux = Unit(name="ux", dimension=dim_x)
        uy = Unit(name="uy", dimension=dim_y)

        # Multi-factor products that can't be resolved to atomic units
        px = UnitProduct({
            UnitFactor(ux, Scale.one): 1,
            UnitFactor(ux, Scale.kilo): 1,
        })
        py = UnitProduct({
            UnitFactor(uy, Scale.one): 1,
            UnitFactor(uy, Scale.kilo): 1,
        })

        with self.assertRaises(DimensionMismatch):
            graph.convert(src=px, dst=py)


# -----------------------------------------------------------------------
# _convert_factorwise: duplicate effective vectors
# Covers lines 872-875, 881-884
# -----------------------------------------------------------------------
class TestFactorwiseDuplicateVectors(unittest.TestCase):
    """Factorwise raises when multiple factors have same effective vector."""

    def test_duplicate_src_effective_vector(self):
        # Two factors with different dimensions but same effective vector
        # after raising to their exponents.
        # Use volume^1 (L³) and length^3 — both produce L³.
        # Factorwise decomposition can't handle this, but the base-form
        # fallback resolves it: 1 L·m³ = 0.001 m⁶.
        graph = get_default_graph()

        src = UnitProduct({
            UnitFactor(units.liter, Scale.one): 1,
            UnitFactor(units.meter, Scale.one): 3,
        })
        dst = UnitProduct({
            UnitFactor(units.meter, Scale.one): 6,
        })

        m = graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1.0), 0.001, places=10)


# -----------------------------------------------------------------------
# _convert_factorwise: factor structure mismatch
# Covers lines 888-891
# -----------------------------------------------------------------------
class TestFactorwiseStructureMismatch(unittest.TestCase):
    """Factorwise raises when effective vector sets don't match."""

    def test_vector_set_mismatch(self):
        graph = ConversionGraph()
        m = units.meter
        s = units.second
        g = units.gram

        graph.add_edge(src=m, dst=m, map=LinearMap(1))

        # m/s vs m/g — time vector vs mass vector
        src = UnitProduct({
            UnitFactor(m, Scale.one): 1,
            UnitFactor(s, Scale.one): -1,
        })
        dst = UnitProduct({
            UnitFactor(m, Scale.one): 1,
            UnitFactor(g, Scale.one): -1,
        })

        with self.assertRaises((ConversionNotFound, DimensionMismatch)):
            graph.convert(src=src, dst=dst)


# -----------------------------------------------------------------------
# _convert_factorwise: exponent mismatch for same dimension
# Covers lines 910-913
# -----------------------------------------------------------------------
class TestFactorwiseExponentMismatch(unittest.TestCase):
    """Factorwise raises on exponent mismatch within same-dimension factors."""

    def test_exponent_mismatch(self):
        # This requires two factors with same dimension but different exponents
        # that still produce the same effective vector (tricky to construct).
        # Actually, line 910 is reached when src_dim == dst_dim
        # but src_exp != dst_exp. The vectors matched so they paired,
        # but the exponents differ. This requires same-dim same-vector
        # but different exponents — which means vectors are equal because
        # vector ** exp1 == vector ** exp2 only when vector is zero vector.
        # Pseudo-dimensions have zero vectors, so this applies to angle, etc.
        # angle^1 vs angle^2 would have same zero vector.
        graph = get_default_graph()

        src = UnitProduct({UnitFactor(units.radian, Scale.one): 1})
        dst = UnitProduct({UnitFactor(units.degree, Scale.one): 2})

        # Same dimension (angle), same zero vector, but exponents 1 vs 2.
        # Dimension check passes (angle == angle raised appropriately),
        # but the exponent mismatch line should be hit.
        with self.assertRaises((ConversionNotFound, DimensionMismatch)):
            graph.convert(src=src, dst=dst)


# -----------------------------------------------------------------------
# _convert_factorwise: cross-dimension factor path failure
# Covers lines 943-946
# -----------------------------------------------------------------------
class TestFactorwiseCrossDimFactorFailure(unittest.TestCase):
    """Factorwise raises when cross-dimension factor BFS fails."""

    def test_cross_dim_factor_no_path(self):
        graph = ConversionGraph()

        # Create units with different dimensions but same overall product dimension
        vol = Unit(name="custom_vol", dimension=Dimension.volume)
        m = units.meter

        # Register the volume unit but don't add a product edge to m³
        graph.register_unit(vol)
        graph._ensure_dimension(Dimension.volume)
        graph._unit_edges[Dimension.volume][vol] = {}

        src = UnitProduct({UnitFactor(vol, Scale.one): 1})
        dst = UnitProduct({UnitFactor(m, Scale.one): 3})

        # volume^1 has same vector as length^3, but no product path exists
        with self.assertRaises(ConversionNotFound):
            graph._convert_factorwise(src=src, dst=dst)


# -----------------------------------------------------------------------
# Conversion cache hit
# Covers line 569-570
# -----------------------------------------------------------------------
class TestConversionCache(unittest.TestCase):
    """Conversion result is cached and reused."""

    def test_cache_hit_returns_same_map(self):
        graph = ConversionGraph()
        graph.add_edge(src=units.meter, dst=units.foot, map=LinearMap(3.28084))

        m1 = graph.convert(src=units.meter, dst=units.foot)
        m2 = graph.convert(src=units.meter, dst=units.foot)
        self.assertIs(m1, m2)

    def test_cache_cleared_on_add_edge(self):
        graph = ConversionGraph()
        graph.add_edge(src=units.meter, dst=units.foot, map=LinearMap(3.28084))
        m1 = graph.convert(src=units.meter, dst=units.foot)

        # Adding a new edge clears cache
        inch = Unit(name="test_inch", dimension=Dimension.length)
        graph.add_edge(src=units.foot, dst=inch, map=LinearMap(12))

        self.assertEqual(len(graph._conversion_cache), 0)


# -----------------------------------------------------------------------
# with_package and _package_edge_already_covered
# Covers lines 456-490, 498-510
# -----------------------------------------------------------------------
class TestWithPackage(unittest.TestCase):
    """with_package loads units, edges, and constants from a UnitPackage."""

    def test_with_package_basic(self):
        from ucon.packages import UnitPackage, UnitDef, EdgeDef

        pkg = UnitPackage(
            name="test_pkg",
            version="0.1.0",
            requires=frozenset(),
            units=(
                UnitDef(
                    name="smoot",
                    dimension="length",
                    shorthand="smt",
                    aliases=("smoot",),
                ),
            ),
            edges=(
                EdgeDef(src="smoot", dst="meter", factor=1.702),
            ),
            constants=(),
        )

        base_graph = get_default_graph()
        extended = base_graph.with_package(pkg)

        # smoot should be resolvable in the extended graph
        result = extended.resolve_unit("smoot")
        self.assertIsNotNone(result)
        self.assertEqual(result[0].name, "smoot")

        # Package name should be tracked
        self.assertIn("test_pkg", extended._loaded_packages)

    def test_with_package_missing_requires(self):
        from ucon.packages import UnitPackage, PackageLoadError

        pkg = UnitPackage(
            name="dependent_pkg",
            version="0.1.0",
            requires=frozenset({"nonexistent_pkg"}),
            units=(),
            edges=(),
            constants=(),
        )

        base_graph = get_default_graph()
        with self.assertRaises(PackageLoadError) as ctx:
            base_graph.with_package(pkg)
        self.assertIn("nonexistent_pkg", str(ctx.exception))

    def test_package_edge_already_covered_skips(self):
        from ucon.packages import UnitPackage, EdgeDef

        # meter→foot already exists in the default graph
        pkg = UnitPackage(
            name="redundant_pkg",
            version="0.1.0",
            requires=frozenset(),
            units=(),
            edges=(
                EdgeDef(src="meter", dst="foot", factor=3.28084),
            ),
            constants=(),
        )

        base_graph = get_default_graph()
        # Should not raise — edge is skipped because it's already covered
        extended = base_graph.with_package(pkg)
        self.assertIn("redundant_pkg", extended._loaded_packages)

    def test_package_edge_unresolvable_unit_not_covered(self):
        from ucon.packages import EdgeDef

        # Edge referencing a unit that doesn't exist in the graph
        edge_def = EdgeDef(src="nonexistent_src", dst="nonexistent_dst", factor=1.0)
        graph = get_default_graph()

        # _package_edge_already_covered should return False (UnknownUnitError branch)
        result = ConversionGraph._package_edge_already_covered(edge_def, graph)
        self.assertFalse(result)


# -----------------------------------------------------------------------
# _bfs_product_path: unit edges traversal (lines 739-764)
# -----------------------------------------------------------------------
class TestBFSProductPathUnitEdges(unittest.TestCase):
    """_bfs_product_path traverses unit edges for single-unit products."""

    def test_product_bfs_uses_unit_edges(self):
        graph = ConversionGraph()
        a = Unit(name="len_a", dimension=Dimension.length)
        b = Unit(name="len_b", dimension=Dimension.length)

        graph.add_edge(src=a, dst=b, map=LinearMap(5.0))

        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)

        # _bfs_product_path should find the path via unit edges
        m = graph._bfs_product_path(src=pa, dst=pb)
        self.assertAlmostEqual(m(1), 5.0, places=6)

    def test_product_bfs_already_visited_skipped(self):
        """Already-visited nodes in unit-edge traversal are skipped.

        Covers line 751: when BFS via unit edges encounters a product key
        that was already visited from a different path, it skips it.
        """
        graph = ConversionGraph()
        a = Unit(name="len_aa", dimension=Dimension.length)
        b = Unit(name="len_bb", dimension=Dimension.length)
        c = Unit(name="len_cc", dimension=Dimension.length)
        d = Unit(name="len_dd", dimension=Dimension.length)

        # Shape: a→b, a→c, b→d, c→d
        # BFS from a to d:
        # 1. Process a: visit b and c (via unit edges), add to queue
        # 2. Process b: visit d (b→d), visit a (inverse, already visited=skip)
        # 3. Process c: try to visit d (c→d), already visited → line 751 hit
        graph.add_edge(src=a, dst=b, map=LinearMap(2))
        graph.add_edge(src=a, dst=c, map=LinearMap(3))
        graph.add_edge(src=b, dst=d, map=LinearMap(5))
        graph.add_edge(src=c, dst=d, map=LinearMap(7))

        pa = UnitProduct.from_unit(a)
        pd = UnitProduct.from_unit(d)

        # BFS finds a→b→d first (2*5=10)
        m = graph._bfs_product_path(src=pa, dst=pd)
        self.assertAlmostEqual(m(1), 10.0, places=6)


# -----------------------------------------------------------------------
# edges_for_transform with no matching transform
# -----------------------------------------------------------------------
class TestEdgesForTransformEmpty(unittest.TestCase):
    """edges_for_transform returns empty list for unknown transforms."""

    def test_no_matching_edges(self):
        graph = ConversionGraph()
        bt = BasisTransform.identity(SI)
        edges = graph.edges_for_transform(bt)
        self.assertEqual(edges, [])


# -----------------------------------------------------------------------
# _convert_units: inverse cross-basis (dst has rebased version)
# Covers lines 603-606
# -----------------------------------------------------------------------
class TestConvertUnitsInverseRebased(unittest.TestCase):
    """When dst has a rebased version, the inverse path is used."""

    def test_inverse_rebased_conversion(self):
        # In the default graph, CGS→SI edges are registered with CGS as src.
        # Converting SI→CGS should use the inverse rebased path.
        graph = get_default_graph()
        # newton → dyne is SI → CGS (dst=dyne has no rebased, but src=dyne
        # is rebased to SI). The _convert_units path for newton→dyne should
        # find dyne in _rebased, see its rebased dimension == newton's dimension,
        # and use _bfs_convert from newton to rebased_dyne.
        m = graph.convert(src=units.newton, dst=units.dyne)
        self.assertAlmostEqual(m(1), 1e5, places=0)


# -----------------------------------------------------------------------
# _bfs_product_path: direct product edge hit
# Covers line 712
# -----------------------------------------------------------------------
class TestBFSProductPathDirectEdge(unittest.TestCase):
    """_bfs_product_path finds direct product edge."""

    def test_direct_product_edge_in_bfs(self):
        graph = ConversionGraph()
        a = Unit(name="e_a", dimension=Dimension.energy)
        b = Unit(name="e_b", dimension=Dimension.energy)

        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)

        graph.add_edge(src=pa, dst=pb, map=LinearMap(42))

        # _bfs_product_path should find the direct edge
        m = graph._bfs_product_path(src=pa, dst=pb)
        self.assertAlmostEqual(m(1), 42.0, places=6)


# -----------------------------------------------------------------------
# _convert_products: shorthand resolve for non-trivial products (cross-dim)
# Covers lines 789-797 (resolve_unit on shorthand in dim-mismatch branch)
# -----------------------------------------------------------------------
class TestConvertProductsShorthandCrossDim(unittest.TestCase):
    """Cross-dim products resolved via shorthand to atomic units."""

    def test_shorthand_cross_dim_resolve_trivial(self):
        graph = get_default_graph()
        # kayser (CGS wavenumber) → m⁻¹ (SI reciprocal_meter)
        src = UnitProduct.from_unit(units.kayser)
        dst = UnitProduct.from_unit(units.reciprocal_meter)
        m = graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1), 100, places=2)

    def test_shorthand_cross_dim_resolve_multi_factor(self):
        """Cross-dim multi-factor products resolved via shorthand.

        Exercises lines 789-797: when both products are multi-factor
        (as_unit returns None), resolve_unit(shorthand) finds the
        atomic unit, enabling cross-basis conversion.
        """
        graph = get_default_graph()

        # poise is CGS (cgs_dynamic_viscosity), pascal_second is SI (dynamic_viscosity)
        # Different dimensions → dim mismatch branch.
        # But as trivial wrappers, as_unit() returns non-None for both,
        # so lines 792/797 (shorthand resolve) are skipped.
        # To hit lines 792/797, we need as_unit() → None for both sides.
        # This requires multi-factor or non-unity-scale products.

        # Construct multi-factor Pa·s (shorthand "Pa·s" → resolves to pascal_second)
        pa_s = UnitProduct({
            UnitFactor(units.pascal, Scale.one): 1,
            UnitFactor(units.second, Scale.one): 1,
        })
        self.assertIsNone(pa_s.as_unit())

        # For the CGS side, we need a multi-factor product whose shorthand
        # resolves to poise. The poise shorthand is "P". To make a multi-factor
        # product with shorthand "P", we'd need a single factor named "P" —
        # but that's trivial. Instead, use a scaled product: as_unit returns
        # None for non-one scale.
        #
        # A scaled product: UnitFactor(poise, Scale.kilo) with exp=1
        # as_unit() → None (scale != Scale.one)
        # shorthand → "kP"
        # resolve_unit("kP") → likely None (no unit named "kP")
        #
        # This path exercised: as_unit()=None → resolve_unit called (line 790)
        # → returns None → src_unit stays None → falls to DimensionMismatch (800)
        # Lines 790 is executed, but 792 (src_unit = resolved[0]) is not.
        #
        # To hit 792, resolve must succeed. The shorthand must be in the registry.
        # Register a custom unit with the shorthand of our multi-factor product.

        # Create custom CGS-like viscosity unit with alias matching a compound shorthand
        cgs_dv_dim = units.poise.dimension  # cgs_dynamic_viscosity
        custom_cgs = Unit(
            name="custom_cgs_dv",
            dimension=cgs_dv_dim,
            aliases=("dyn·s/cm²",),
        )
        ext_graph = graph.copy()
        ext_graph.register_unit(custom_cgs)
        # Add cross-basis edge from custom_cgs to pascal_second
        ext_graph.add_edge(
            src=custom_cgs,
            dst=units.pascal_second,
            map=LinearMap(0.1),
            basis_transform=CGS_TO_SI,
        )

        # Make a multi-factor product with shorthand "dyn·s/cm²"
        dyn = Unit(name="dyn", dimension=cgs_dv_dim)
        s_cm2 = Unit(name="s/cm²", dimension=cgs_dv_dim)
        src = UnitProduct({
            UnitFactor(dyn, Scale.one): 1,
            UnitFactor(s_cm2, Scale.one): 1,
        })
        self.assertIsNone(src.as_unit())
        # Check shorthand
        shorthand = src.shorthand
        self.assertEqual(shorthand, "dyn·s/cm²")

        # resolve_unit("dyn·s/cm²") should return custom_cgs
        resolved = ext_graph.resolve_unit(shorthand)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved[0], custom_cgs)

        # Now convert: src (multi-factor, cgs_dv_dim) → pa_s (multi-factor, dv_dim)
        m = ext_graph.convert(src=src, dst=pa_s)
        self.assertAlmostEqual(m(1), 0.1, places=5)


# -----------------------------------------------------------------------
# _convert_products: shorthand resolve for same-dim products
# Covers lines 833-836 (resolve_unit on src shorthand, same-dim branch)
# -----------------------------------------------------------------------
class TestConvertProductsShorthandSameDim(unittest.TestCase):
    """Same-dim products with composite shorthand resolved to atomic units."""

    def test_shorthand_same_dim_resolve(self):
        # Build a custom graph where no direct product edge exists but
        # shorthand resolution can find the atomic unit.
        graph = ConversionGraph()

        # Create an "atomic" unit for dynamic viscosity
        dv_dim = units.pascal_second.dimension
        atomic = Unit(name="dv_atomic", dimension=dv_dim, aliases=("dv·x",))
        other = Unit(name="dv_other", dimension=dv_dim, aliases=("dvo",))

        graph.register_unit(atomic)
        graph.register_unit(other)
        graph.add_edge(src=atomic, dst=other, map=LinearMap(2.0))

        # Create a multi-factor product whose shorthand matches the alias
        # We need as_unit() → None AND shorthand that resolves.
        # Construct a product with shorthand "dv·x" — but UnitProduct.shorthand
        # is auto-generated from factors, so we need the factors to produce it.
        # Easier: register a unit whose name IS the shorthand of a product.
        #
        # Alternative: create a src product that's a trivial wrapper (as_unit works)
        # and a dst product that's multi-factor (as_unit → None, shorthand resolves).
        # For line 836 specifically, src must be multi-factor.
        #
        # Simplest: use two multi-factor products where factorwise would fail
        # but shorthand resolution succeeds.
        p = units.pascal
        s = units.second

        src_prod = UnitProduct({
            UnitFactor(p, Scale.one): 1,
            UnitFactor(s, Scale.one): 1,
        })
        # Register "Pa·s" alias to point to pascal_second in graph
        graph.register_unit(units.pascal_second)

        # dst is a trivial wrapper around pascal_second
        dst_prod = UnitProduct.from_unit(units.pascal_second)

        # Add unit edge so conversion works
        # pascal_second → pascal_second is identity, but we need it in the graph
        graph.add_edge(src=units.pascal_second, dst=units.pascal_second, map=LinearMap(1))

        # src.as_unit() → None (multi-factor), resolve_unit('Pa·s') → pascal_second
        m = graph.convert(src=src_prod, dst=dst_prod)
        self.assertAlmostEqual(m(1), 1.0, places=6)


# -----------------------------------------------------------------------
# _convert_factorwise: duplicate dst effective vector
# Covers line 882
# -----------------------------------------------------------------------
class TestFactorwiseDuplicateDstVector(unittest.TestCase):
    """Factorwise raises when dst has duplicate effective vectors."""

    def test_duplicate_dst_effective_vector(self):
        graph = get_default_graph()

        # Target with two factors that both produce L³ effective vector
        src = UnitProduct({UnitFactor(units.meter, Scale.one): 6})
        dst = UnitProduct({
            UnitFactor(units.liter, Scale.one): 1,
            UnitFactor(units.meter, Scale.one): 3,
        })

        with self.assertRaises((ConversionNotFound, DimensionMismatch)):
            graph._convert_factorwise(src=src, dst=dst)


# -----------------------------------------------------------------------
# _convert_factorwise: effective vector set mismatch after grouping
# Covers line 889
# -----------------------------------------------------------------------
class TestFactorwiseVectorSetMismatch(unittest.TestCase):
    """Factorwise raises when effective vector sets don't align."""

    def test_mismatched_vector_sets(self):
        graph = ConversionGraph()
        m = units.meter
        s = units.second
        kg = units.kilogram

        # m²·s⁻¹ vs m²·kg⁻¹ — different vector sets (T⁻¹ vs M⁻¹)
        src = UnitProduct({
            UnitFactor(m, Scale.one): 2,
            UnitFactor(s, Scale.one): -1,
        })
        dst = UnitProduct({
            UnitFactor(m, Scale.one): 2,
            UnitFactor(kg, Scale.one): -1,
        })

        with self.assertRaises(ConversionNotFound):
            graph._convert_factorwise(src=src, dst=dst)


# -----------------------------------------------------------------------
# _convert_factorwise: pseudo-dimension isolation
# Covers line 904
# -----------------------------------------------------------------------
class TestFactorwisePseudoDimIsolation(unittest.TestCase):
    """Factorwise prevents conversion between different pseudo-dimensions."""

    def test_pseudo_dim_conversion_blocked(self):
        graph = get_default_graph()

        # angle and solid_angle both have zero vectors but are distinct
        src = UnitProduct({UnitFactor(units.radian, Scale.one): 1})
        dst = UnitProduct({UnitFactor(units.steradian, Scale.one): 1})

        with self.assertRaises((ConversionNotFound, DimensionMismatch)):
            graph._convert_factorwise(src=src, dst=dst)


# -----------------------------------------------------------------------
# Helper: stub Map subclass for testing _maps_equal fallbacks
# -----------------------------------------------------------------------
class _StubMap(Map):
    """Minimal concrete Map subclass for testing."""

    def __init__(self, fn, name="stub"):
        object.__setattr__(self, '_fn', fn)
        object.__setattr__(self, '_name', name)

    def __call__(self, x):
        return self._fn(x)

    @property
    def invertible(self):
        return True

    def inverse(self):
        return self

    def __matmul__(self, other):
        from ucon.maps import ComposedMap
        return ComposedMap(outer=self, inner=other)

    def __pow__(self, n):
        return self

    def derivative(self, x):
        return 1.0


# -----------------------------------------------------------------------
# _maps_equal: fallback branches
# Covers lines 1024, 1032, 1034, 1042, 1044-1045
# -----------------------------------------------------------------------
class TestMapsEqualFallbacks(unittest.TestCase):
    """Test _maps_equal fallback evaluation points for exotic maps."""

    def test_first_try_false_at_zero(self):
        """Line 1024: maps agree at 1.0 but differ at 0.0."""
        m1 = LinearMap(1)  # identity: 1->1, 0->0
        m2 = _StubMap(lambda x: 999.0 if x == 0.0 else x)  # 1->1, 0->999
        # m1(1)=1, m2(1)=1 → pass first check
        # m1(0)=0, m2(0)=999 → differ → return False (line 1024)
        self.assertFalse(ConversionGraph._maps_equal(m1, m2))

    def test_fallback_to_second_try_block(self):
        """Lines 1032, 1034: first try raises at 0.0, second try succeeds."""
        from ucon.maps import LogMap
        # LogMap raises ValueError at x=0.0 (log(0) is undefined).
        m1 = LogMap(scale=10)  # 10 * log10(x)
        m2 = LogMap(scale=20)  # 20 * log10(x)
        # First try: m1(1.0)=0, m2(1.0)=0 → agree. m1(0.0) → ValueError → except.
        # Second try: m1(1.0)=0, m2(1.0)=0 → agree. m1(2.0)≈3.01, m2(2.0)≈6.02 → differ.
        # Line 1034: return False
        self.assertFalse(ConversionGraph._maps_equal(m1, m2))

    def test_fallback_second_try_equal(self):
        """Second try block returns True when maps agree at 1.0 and 2.0."""
        from ucon.maps import LogMap
        m1 = LogMap(scale=10)
        m2 = LogMap(scale=10)  # identical
        # First try raises at 0.0, second try checks 1.0 and 2.0 → agree → True
        self.assertTrue(ConversionGraph._maps_equal(m1, m2))

    def test_fallback_second_try_differ_at_one(self):
        """Line 1032: maps differ at 1.0 in the second try block.

        To reach line 1032, the first try must raise (sending us to second try),
        and then the maps must disagree at 1.0. A map that raises at 1.0 on
        first call but returns a value on subsequent calls creates this scenario.
        """
        call_count = [0]

        def fn_flaky(x):
            if x == 1.0:
                call_count[0] += 1
                if call_count[0] <= 1:
                    raise ValueError("first call at 1.0 raises")
                return 999.0  # second call returns different value
            if x == 0.0:
                raise ValueError("always fails at 0")
            return x

        m1 = _StubMap(fn_flaky)
        m2 = LinearMap(1)  # always returns x: 1.0→1.0

        # First try: m1(1.0) raises → except (call_count=1)
        # Second try: m1(1.0) returns 999.0 (call_count=2), m2(1.0) returns 1.0
        # abs(999 - 1) > 1e-9 → line 1032: return False
        self.assertFalse(ConversionGraph._maps_equal(m1, m2))

    def test_fallback_third_try_differ_at_half(self):
        """Line 1042: third try block, maps differ at 0.5."""
        def fn1(x):
            if x == 0.0 or x == 1.0:
                raise ValueError("bad")
            return x * 2.0
        def fn2(x):
            if x == 0.0 or x == 1.0:
                raise ValueError("bad")
            return x * 3.0
        m1 = _StubMap(fn1)
        m2 = _StubMap(fn2)
        # First try: raises at 1.0 → except → second try: raises at 1.0 → except
        # Third try: 0.5*2=1.0, 0.5*3=1.5 → differ → line 1042: return False
        self.assertFalse(ConversionGraph._maps_equal(m1, m2))

    def test_fallback_third_try_equal(self):
        """Lines 1044-1045: third try block, maps agree at 0.5 and 2.0."""
        def fn(x):
            if x == 0.0 or x == 1.0:
                raise ValueError("bad")
            return x * 2.0

        m1 = _StubMap(fn)
        m2 = _StubMap(fn)
        # First try: raises at 1.0 → second try: raises at 1.0
        # Third try: 0.5*2=1.0 agree, 2.0*2=4.0 agree → True (line 1045)
        self.assertTrue(ConversionGraph._maps_equal(m1, m2))

    def test_fallback_third_try_differ_at_two(self):
        """Line 1044: third try block, maps agree at 0.5 but differ at 2.0."""
        def fn1(x):
            if x == 0.0 or x == 1.0:
                raise ValueError("bad")
            if x == 2.0:
                return 100.0
            return x

        def fn2(x):
            if x == 0.0 or x == 1.0:
                raise ValueError("bad")
            if x == 2.0:
                return 200.0
            return x

        m1 = _StubMap(fn1)  # 0.5->0.5, 2.0->100
        m2 = _StubMap(fn2)  # 0.5->0.5, 2.0->200
        # Third try: agree at 0.5, differ at 2.0 → line 1044
        self.assertFalse(ConversionGraph._maps_equal(m1, m2))

    def test_all_points_raise_falls_back_to_type_check(self):
        """Line 1048: all evaluation points raise, falls back to type comparison."""
        m1 = _StubMap(lambda x: (_ for _ in ()).throw(ValueError("always")))
        m2 = _StubMap(lambda x: (_ for _ in ()).throw(ValueError("always")))

        # The lambda approach above is tricky; use a direct raising function
        def always_raise(x):
            raise ValueError("always fails")

        m1 = _StubMap(always_raise, "a")
        m2 = _StubMap(always_raise, "b")
        # All three try blocks raise → type(m1) is type(m2) → True
        self.assertTrue(ConversionGraph._maps_equal(m1, m2))

        # Different types → False
        m3 = LinearMap(1)
        self.assertFalse(ConversionGraph._maps_equal(m1, m3))


# -----------------------------------------------------------------------
# _cross_basis_edge_signature: early-continue branches
# Covers lines 1075, 1077, 1082
# -----------------------------------------------------------------------
class TestCrossBasisEdgeSignature(unittest.TestCase):
    """Test early-continue branches in _cross_basis_edge_signature."""

    def _make_rebased(self, original, bt, rebased_dim=None):
        """Create a RebasedUnit with proper rebased_dimension."""
        if rebased_dim is None:
            rebased_dim = original.dimension
        return RebasedUnit(
            original=original,
            rebased_dimension=rebased_dim,
            basis_transform=bt,
        )

    def test_dimension_not_in_edges(self):
        """Line 1075: rebased unit's dimension not in _unit_edges."""
        graph = ConversionGraph()
        bt = BasisTransform.identity(SI)
        rebased = self._make_rebased(units.meter, bt)
        # Don't add the rebased dimension to _unit_edges
        sig = graph._cross_basis_edge_signature([rebased])
        self.assertEqual(sig, {})

    def test_rebased_not_in_dimension_edges(self):
        """Line 1077: rebased unit's dimension exists but rebased not a source."""
        graph = ConversionGraph()
        bt = BasisTransform.identity(SI)
        rebased = self._make_rebased(units.meter, bt)
        dim = rebased.dimension
        graph._ensure_dimension(dim)
        # Dimension exists in edges but rebased is not a source node
        sig = graph._cross_basis_edge_signature([rebased])
        self.assertEqual(sig, {})

    def test_rebased_destination_skipped(self):
        """Line 1082: destinations that are RebasedUnit are skipped."""
        graph = ConversionGraph()
        bt = BasisTransform.identity(SI)
        rebased_src = self._make_rebased(units.meter, bt)
        rebased_dst = self._make_rebased(units.foot, bt)
        dim = rebased_src.dimension
        graph._ensure_dimension(dim)
        # Add an edge from rebased_src to rebased_dst (not to a plain Unit)
        graph._unit_edges[dim][rebased_src] = {rebased_dst: LinearMap(3.28084)}
        sig = graph._cross_basis_edge_signature([rebased_src])
        # rebased_dst is a RebasedUnit → skipped → empty signature
        self.assertEqual(sig, {})

    def test_non_rebased_destination_included(self):
        """Normal case: non-rebased destinations are included in signature."""
        graph = ConversionGraph()
        bt = BasisTransform.identity(SI)
        rebased_src = self._make_rebased(units.meter, bt)
        dim = rebased_src.dimension
        graph._ensure_dimension(dim)
        # Add an edge from rebased_src to a plain Unit
        graph._unit_edges[dim][rebased_src] = {units.foot: LinearMap(3.28084)}
        sig = graph._cross_basis_edge_signature([rebased_src])
        expected_key = ("meter", "foot", "SI_TO_SI")
        self.assertIn(expected_key, sig)


# -----------------------------------------------------------------------
# __eq__: inequality branches
# Covers lines 1095, 1099, 1116, 1133, 1147, 1153, 1157, 1165, 1169,
#         1173, 1180, 1188, 1192, 1194, 1197, 1199, 1201
# -----------------------------------------------------------------------
class TestGraphEquality(unittest.TestCase):
    """Test __eq__ returns False for each structural mismatch."""

    def _make_minimal_graph(self):
        """Create a minimal graph with known structure for comparison."""
        g = ConversionGraph()
        g.register_unit(units.meter)
        g.register_unit(units.foot)
        g.add_edge(src=units.meter, dst=units.foot, map=LinearMap(3.28084))
        return g

    def test_not_a_graph(self):
        """Line 1095: comparing with non-ConversionGraph returns NotImplemented."""
        g = self._make_minimal_graph()
        result = g.__eq__("not a graph")
        self.assertIs(result, NotImplemented)

    def test_name_registry_mismatch(self):
        """Line 1099: different registered unit names."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        extra = Unit(name="extra_unit", dimension=Dimension.length)
        g2.register_unit(extra)
        self.assertNotEqual(g1, g2)

    def test_loaded_packages_mismatch(self):
        """Line 1103: different loaded packages."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        g2._loaded_packages = frozenset({"some_package"})
        self.assertNotEqual(g1, g2)

    def test_constants_length_mismatch(self):
        """Line 1107: different number of constants."""
        from ucon.constants import Constant
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        c = Constant(
            symbol="x", name="test", value=1.0,
            unit=units.meter, uncertainty=None,
            source="test", category="session",
        )
        g2._package_constants = (c,)
        self.assertNotEqual(g1, g2)

    def test_constants_field_mismatch(self):
        """Line 1113: same number of constants but different fields."""
        from ucon.constants import Constant
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        c1 = Constant(
            symbol="x", name="test", value=1.0,
            unit=units.meter, uncertainty=None,
            source="test", category="session",
        )
        c2 = Constant(
            symbol="y", name="test2", value=2.0,
            unit=units.meter, uncertainty=None,
            source="test", category="session",
        )
        g1._package_constants = (c1,)
        g2._package_constants = (c2,)
        self.assertNotEqual(g1, g2)

    def test_constants_unit_dimension_mismatch(self):
        """Line 1116: constants have same fields but different unit dimensions."""
        from ucon.constants import Constant
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        c1 = Constant(
            symbol="x", name="test", value=1.0,
            unit=units.meter, uncertainty=None,
            source="test", category="session",
        )
        c2 = Constant(
            symbol="x", name="test", value=1.0,
            unit=units.second, uncertainty=None,
            source="test", category="session",
        )
        g1._package_constants = (c1,)
        g2._package_constants = (c2,)
        self.assertNotEqual(g1, g2)

    def test_basis_graph_one_none(self):
        """Line 1120: one graph has basis_graph, other doesn't."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        g1._basis_graph = BasisGraph()
        g2._basis_graph = None
        self.assertNotEqual(g1, g2)

    def test_basis_graph_edge_mismatch(self):
        """Line 1133: both have basis_graphs but with different edges."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        bg1 = BasisGraph()
        bg2 = BasisGraph()
        bg1.add_transform(CGS_TO_SI)
        # bg2 has no connections
        g1._basis_graph = bg1
        g2._basis_graph = bg2
        self.assertNotEqual(g1, g2)

    def test_dimension_set_mismatch(self):
        """Line 1139/1147: different dimension sets in unit edges."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        # Add a time dimension to g2 only
        t = units.second
        g2.register_unit(t)
        g2._ensure_dimension(Dimension.time)
        g2._unit_edges[Dimension.time][t] = {}
        g2.add_edge(src=units.second, dst=units.second, map=LinearMap(1))
        self.assertNotEqual(g1, g2)

    def test_src_node_mismatch(self):
        """Line 1147: same dimensions but different source units."""
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        a = Unit(name="a_len", dimension=Dimension.length)
        b = Unit(name="b_len", dimension=Dimension.length)
        c = Unit(name="c_len", dimension=Dimension.length)
        g1.register_unit(a)
        g1.register_unit(b)
        g1.register_unit(c)
        g2.register_unit(a)
        g2.register_unit(b)
        g2.register_unit(c)
        g1.add_edge(src=a, dst=b, map=LinearMap(2))
        g2.add_edge(src=a, dst=c, map=LinearMap(3))
        # g1 has {a: {b: ...}, b: {a: ...}} but g2 has {a: {c: ...}, c: {a: ...}}
        self.assertNotEqual(g1, g2)

    def test_dst_node_mismatch(self):
        """Line 1153: same source nodes but different destinations for a source.

        Directly manipulate _unit_edges to create the exact scenario
        where src nodes match but dst nodes for a given src differ,
        avoiding add_edge's bidirectional insertion.
        """
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        a = Unit(name="d_len", dimension=Dimension.length)
        b = Unit(name="e_len", dimension=Dimension.length)
        c = Unit(name="f_len", dimension=Dimension.length)
        for g in (g1, g2):
            g.register_unit(a)
            g.register_unit(b)
            g.register_unit(c)
            g._ensure_dimension(Dimension.length)
        # Both have same src nodes: {a}
        # g1: a→{b}, g2: a→{c}
        g1._unit_edges[Dimension.length] = {a: {b: LinearMap(2)}}
        g2._unit_edges[Dimension.length] = {a: {c: LinearMap(3)}}
        self.assertNotEqual(g1, g2)

    def test_map_mismatch(self):
        """Line 1157: same structure but different conversion maps."""
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        a = Unit(name="g_len", dimension=Dimension.length)
        b = Unit(name="h_len", dimension=Dimension.length)
        g1.register_unit(a)
        g1.register_unit(b)
        g2.register_unit(a)
        g2.register_unit(b)
        g1.add_edge(src=a, dst=b, map=LinearMap(2))
        g2.add_edge(src=a, dst=b, map=LinearMap(5))
        self.assertNotEqual(g1, g2)

    def test_product_edge_key_mismatch(self):
        """Line 1161/1165: different product edge source keys."""
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        a = Unit(name="vol_x", dimension=Dimension.volume)
        b = Unit(name="vol_y", dimension=Dimension.volume)
        c = Unit(name="vol_z", dimension=Dimension.volume)
        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)
        pc = UnitProduct.from_unit(c)
        g1.add_edge(src=pa, dst=pb, map=LinearMap(2))
        g2.add_edge(src=pa, dst=pc, map=LinearMap(3))
        self.assertNotEqual(g1, g2)

    def test_product_edge_dst_mismatch(self):
        """Line 1165: same product src keys but different destinations.

        Directly manipulate _product_edges to create the exact scenario
        where src keys match but dst keys for a given src differ.
        """
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        a = Unit(name="vol_p", dimension=Dimension.volume)
        b = Unit(name="vol_q", dimension=Dimension.volume)
        c = Unit(name="vol_r", dimension=Dimension.volume)
        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)
        pc = UnitProduct.from_unit(c)
        ka = g1._product_key(pa)
        kb = g1._product_key(pb)
        kc = g1._product_key(pc)
        # Both have same src key: {ka}
        # g1: ka→{kb}, g2: ka→{kc}
        g1._product_edges = {ka: {kb: LinearMap(2)}}
        g2._product_edges = {ka: {kc: LinearMap(3)}}
        self.assertNotEqual(g1, g2)

    def test_product_edge_map_mismatch(self):
        """Line 1169: same product structure but different maps."""
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        a = Unit(name="vol_m", dimension=Dimension.volume)
        b = Unit(name="vol_n", dimension=Dimension.volume)
        pa = UnitProduct.from_unit(a)
        pb = UnitProduct.from_unit(b)
        g1.add_edge(src=pa, dst=pb, map=LinearMap(2))
        g2.add_edge(src=pa, dst=pb, map=LinearMap(7))
        self.assertNotEqual(g1, g2)

    def _make_rebased(self, original, bt, rebased_dim=None):
        """Create a RebasedUnit with proper rebased_dimension."""
        if rebased_dim is None:
            rebased_dim = original.dimension
        return RebasedUnit(
            original=original,
            rebased_dimension=rebased_dim,
            basis_transform=bt,
        )

    def test_rebased_key_mismatch(self):
        """Line 1173: different rebased unit original keys."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        bt = BasisTransform.identity(SI)
        r1 = self._make_rebased(units.meter, bt)
        r2 = self._make_rebased(units.second, bt)
        g1._rebased = {units.meter: [r1]}
        g2._rebased = {units.second: [r2]}
        self.assertNotEqual(g1, g2)

    def test_rebased_edge_signature_key_mismatch(self):
        """Line 1180: same rebased keys but different edge signatures."""
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        bt = BasisTransform.identity(SI)
        r = self._make_rebased(units.meter, bt)
        dim = r.dimension
        # g1: rebased meter → foot
        g1._ensure_dimension(dim)
        g1._unit_edges[dim][r] = {units.foot: LinearMap(3.28084)}
        g1._rebased = {units.meter: [r]}
        # g2: rebased meter → inch (different destination)
        inch = Unit(name="test_inch_eq", dimension=Dimension.length)
        g2._ensure_dimension(dim)
        g2._unit_edges[dim][r] = {inch: LinearMap(39.3701)}
        g2._rebased = {units.meter: [r]}
        self.assertNotEqual(g1, g2)

    def test_rebased_edge_map_mismatch(self):
        """Line 1184: same rebased signature keys but different maps."""
        g1 = ConversionGraph()
        g2 = ConversionGraph()
        bt = BasisTransform.identity(SI)
        r = self._make_rebased(units.meter, bt)
        dim = r.dimension
        g1._ensure_dimension(dim)
        g1._unit_edges[dim][r] = {units.foot: LinearMap(3.28084)}
        g1._rebased = {units.meter: [r]}
        g2._ensure_dimension(dim)
        g2._unit_edges[dim][r] = {units.foot: LinearMap(999.0)}
        g2._rebased = {units.meter: [r]}
        self.assertNotEqual(g1, g2)

    def test_context_key_mismatch(self):
        """Line 1188: different context names."""
        from ucon.contexts import ConversionContext, ContextEdge
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        ctx = ConversionContext(
            name="test_ctx",
            edges=(
                ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(299792458)),
            ),
            description="test context",
        )
        g1.register_context(ctx)
        self.assertNotEqual(g1, g2)

    def test_context_description_mismatch(self):
        """Line 1192: same context name but different descriptions."""
        from ucon.contexts import ConversionContext, ContextEdge
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        edge = ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(299792458))
        ctx1 = ConversionContext(name="ctx", edges=(edge,), description="alpha")
        ctx2 = ConversionContext(name="ctx", edges=(edge,), description="beta")
        g1.register_context(ctx1)
        g2.register_context(ctx2)
        self.assertNotEqual(g1, g2)

    def test_context_edge_count_mismatch(self):
        """Line 1194: same context name but different number of edges."""
        from ucon.contexts import ConversionContext, ContextEdge
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        edge1 = ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(299792458))
        edge2 = ContextEdge(src=units.second, dst=units.hertz, map=LinearMap(1))
        ctx1 = ConversionContext(name="ctx", edges=(edge1,))
        ctx2 = ConversionContext(name="ctx", edges=(edge1, edge2))
        g1.register_context(ctx1)
        g2.register_context(ctx2)
        self.assertNotEqual(g1, g2)

    def test_context_edge_src_mismatch(self):
        """Line 1197: same context structure but different edge source."""
        from ucon.contexts import ConversionContext, ContextEdge
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        edge1 = ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(299792458))
        edge2 = ContextEdge(src=units.foot, dst=units.hertz, map=LinearMap(299792458))
        ctx1 = ConversionContext(name="ctx", edges=(edge1,))
        ctx2 = ConversionContext(name="ctx", edges=(edge2,))
        g1.register_context(ctx1)
        g2.register_context(ctx2)
        self.assertNotEqual(g1, g2)

    def test_context_edge_dst_mismatch(self):
        """Line 1199: same context structure but different edge destination."""
        from ucon.contexts import ConversionContext, ContextEdge
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        edge1 = ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(299792458))
        edge2 = ContextEdge(src=units.meter, dst=units.second, map=LinearMap(299792458))
        ctx1 = ConversionContext(name="ctx", edges=(edge1,))
        ctx2 = ConversionContext(name="ctx", edges=(edge2,))
        g1.register_context(ctx1)
        g2.register_context(ctx2)
        self.assertNotEqual(g1, g2)

    def test_context_edge_map_mismatch(self):
        """Line 1201: same context structure but different edge map."""
        from ucon.contexts import ConversionContext, ContextEdge
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        edge1 = ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(299792458))
        edge2 = ContextEdge(src=units.meter, dst=units.hertz, map=LinearMap(42))
        ctx1 = ConversionContext(name="ctx", edges=(edge1,))
        ctx2 = ConversionContext(name="ctx", edges=(edge2,))
        g1.register_context(ctx1)
        g2.register_context(ctx2)
        self.assertNotEqual(g1, g2)

    def test_equal_graphs(self):
        """Positive case: structurally identical graphs are equal."""
        g1 = self._make_minimal_graph()
        g2 = self._make_minimal_graph()
        self.assertEqual(g1, g2)


if __name__ == '__main__':
    unittest.main()

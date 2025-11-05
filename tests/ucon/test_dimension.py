import unittest

from ucon.algebra import Vector
from ucon.dimension import Dimension


class TestDimension(unittest.TestCase):

    def test_basic_dimensions_are_unique(self):
        seen = set()
        for dim in Dimension:
            self.assertNotIn(dim.value, seen, f'Duplicate vector found for {dim.name}')
            seen.add(dim.value)

    def test_multiplication_adds_exponents(self):
        self.assertEqual(
            Dimension.mass * Dimension.acceleration,
            Dimension.force,
        )
        self.assertEqual(
            Dimension.length * Dimension.length,
            Dimension.area,
        )
        self.assertEqual(
            Dimension.length * Dimension.length * Dimension.length,
            Dimension.volume,
        )

    def test_division_subtracts_exponents(self):
        self.assertEqual(
            Dimension.length / Dimension.time,
            Dimension.velocity,
        )
        self.assertEqual(
            Dimension.force / Dimension.area,
            Dimension.pressure,
        )

    def test_none_dimension_behaves_neutrally(self):
        base = Dimension.mass
        self.assertEqual(base * Dimension.none, base)
        self.assertEqual(base / Dimension.none, base)
        self.assertEqual(Dimension.none * base, base)
        with self.assertRaises(ValueError) as exc:
            Dimension.none / base
        assert type(exc.exception) == ValueError
        assert str(exc.exception).endswith('is not a valid Dimension')

    def test_hash_and_equality_consistency(self):
        d1 = Dimension.mass
        d2 = Dimension.mass
        d3 = Dimension.length
        self.assertEqual(d1, d2)
        self.assertNotEqual(d1, d3)
        self.assertEqual(hash(d1), hash(d2))
        self.assertNotEqual(hash(d1), hash(d3))

    def test_composite_quantities_examples(self):
        # Energy = Force * Length
        self.assertEqual(
            Dimension.force * Dimension.length,
            Dimension.energy,
        )
        # Power = Energy / Time
        self.assertEqual(
            Dimension.energy / Dimension.time,
            Dimension.power,
        )
        # Pressure = Force / Area
        self.assertEqual(
            Dimension.force / Dimension.area,
            Dimension.pressure,
        )
        # Charge = Current * Time
        self.assertEqual(
            Dimension.current * Dimension.time,
            Dimension.charge,
        )

    def test_vector_equality_reflects_dimension_equality(self):
        self.assertEqual(Dimension.mass.value, Dimension.mass.value)
        self.assertNotEqual(Dimension.mass.value, Dimension.time.value)
        self.assertEqual(Dimension.mass, Dimension.mass)
        self.assertNotEqual(Dimension.mass, Dimension.time)

    def test_pow_identity_and_zero(self):
        self.assertIs(Dimension.length ** 1, Dimension.length)
        self.assertIs(Dimension.mass ** 0, Dimension.none)

    def test_pow_known_results(self):
        self.assertEqual(Dimension.length ** 2, Dimension.area)
        self.assertEqual(Dimension.time ** -1, Dimension.frequency)

    @unittest.skip("TODO (ucon#68): should pass when dynamic dimensions are supported")
    def test_pow_returns_derived_dimension_for_unknown(self):
        jerk = Dimension.length * (Dimension.time ** -3)  # length / time^3
        self.assertTrue(jerk.name.startswith("derived("))
        self.assertNotIn(jerk.name, Dimension.__members__)

    def test_resolve_known_vector_returns_enum_member(self):
        dim = Dimension._resolve(Vector(0, 1, 0, 0, 0, 0, 0))
        self.assertIs(dim, Dimension.length)

    def test_resolve_unknown_vector_returns_dynamic_dimension(self):
        vec = Vector(T=1, L=-1, M=0, I=0, Θ=0, J=0, N=0)  # “speed per time”, not an enum member
        dyn = Dimension._resolve(vec)
        self.assertNotIn(dyn.name, Dimension.__members__)
        self.assertEqual(dyn.value, vec)
        self.assertEqual(dyn.name, f"derived({vec})")

    def test_resolve_returns_same_dynamic_for_same_vector(self):
        vec = Vector(T=2, L=-2, M=0, I=0, Θ=0, J=0, N=0)
        first = Dimension._resolve(vec)
        second = Dimension._resolve(vec)
        self.assertEqual(first.value, second.value)
        self.assertEqual(first.name, second.name)

    def test_dynamic_dimensions_compare_by_vector(self):
        v1 = Vector(T=2, L=-2, M=0, I=0, Θ=0, J=0, N=0)
        v2 = Vector(T=2, L=-2, M=0, I=0, Θ=0, J=0, N=0)
        d1 = Dimension._resolve(v1)
        d2 = Dimension._resolve(v2)
        self.assertEqual(d1.value, d2.value)
        self.assertEqual(d1 == d2, True)
        self.assertEqual(hash(d1), hash(d2))


class TestDimensionEdgeCases(unittest.TestCase):

    def test_invalid_multiplication_type(self):
        with self.assertRaises(TypeError):
            Dimension.length * 5
        with self.assertRaises(TypeError):
            "mass" * Dimension.time

    def test_invalid_division_type(self):
        with self.assertRaises(TypeError):
            Dimension.time / "length"
        with self.assertRaises(TypeError):
            5 / Dimension.mass

    def test_equality_with_non_dimension(self):
        with self.assertRaises(TypeError):
            Dimension.mass ==  "mass"

    def test_enum_uniqueness_and_hash(self):
        # Hashes should be unique per distinct dimension
        hashes = {hash(d) for d in Dimension}
        self.assertEqual(len(hashes), len(Dimension))
        # All Dimension.value entries must be distinct Vectors
        values = [d.value for d in Dimension]
        self.assertEqual(len(values), len(set(values)))

    def test_combined_chained_operations(self):
        # (mass * acceleration) / area = pressure
        result = (Dimension.mass * Dimension.acceleration) / Dimension.area
        self.assertEqual(result, Dimension.pressure)

    def test_dimension_round_trip_equality(self):
        # Multiplying and dividing by the same dimension returns self
        d = Dimension.energy
        self.assertEqual((d * Dimension.none) / Dimension.none, d)
        self.assertEqual(d / Dimension.none, d)
        self.assertEqual(Dimension.none * d, d)

    def test_enum_is_hashable_and_iterable(self):
        seen = {d for d in Dimension}
        self.assertIn(Dimension.mass, seen)
        self.assertEqual(len(seen), len(Dimension))

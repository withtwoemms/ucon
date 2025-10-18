import unittest
from ucon.dimension import Vector, Dimension


class TestVector(unittest.TestCase):

    def test_vector_iteration_and_length(self):
        v = Vector(1, 0, 0, 0, 0, 0, 0)
        self.assertEqual(tuple(v), (1, 0, 0, 0, 0, 0, 0))
        self.assertEqual(len(v), 7)  # always 7 components

    def test_vector_addition(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0)
        v2 = Vector(0, 2, 0, 0, 0, 0, 0)
        result = v1 + v2
        self.assertEqual(result, Vector(1, 2, 0, 0, 0, 0, 0))

    def test_vector_subtraction(self):
        v1 = Vector(2, 1, 0, 0, 0, 0, 0)
        v2 = Vector(1, 1, 0, 0, 0, 0, 0)
        self.assertEqual(v1 - v2, Vector(1, 0, 0, 0, 0, 0, 0))

    def test_vector_equality_and_hash(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0)
        v2 = Vector(1, 0, 0, 0, 0, 0, 0)
        v3 = Vector(0, 1, 0, 0, 0, 0, 0)
        self.assertTrue(v1 == v2)
        self.assertFalse(v1 == v3)
        self.assertEqual(hash(v1), hash(v2))
        self.assertNotEqual(hash(v1), hash(v3))


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


class TestVectorEdgeCases(unittest.TestCase):

    def test_zero_vector_equality_and_additivity(self):
        zero = Vector()
        self.assertEqual(zero, Vector(0, 0, 0, 0, 0, 0, 0))
        # Adding or subtracting zero should yield same vector
        v = Vector(1, 2, 3, 4, 5, 6, 7)
        self.assertEqual(v + zero, v)
        self.assertEqual(v - zero, v)

    def test_vector_with_negative_exponents(self):
        v1 = Vector(1, -2, 3, 0, 0, 0, 0)
        v2 = Vector(-1, 2, -3, 0, 0, 0, 0)
        result = v1 + v2
        self.assertEqual(result, Vector(0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(v1 - v1, Vector())  # perfect cancellation

    def test_vector_equality_with_non_vector(self):
        v = Vector()
        with self.assertRaises(AssertionError):
            v == "not a vector"
        with self.assertRaises(AssertionError):
            v == None

    def test_hash_consistency_for_equal_vectors(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0)
        v2 = Vector(1, 0, 0, 0, 0, 0, 0)
        self.assertEqual(hash(v1), hash(v2))
        self.assertEqual(len({v1, v2}), 1)

    def test_iter_length_order_consistency(self):
        v = Vector(1, 2, 3, 4, 5, 6, 7)
        components = list(v)
        self.assertEqual(len(components), len(v))
        # Ensure order of iteration is fixed (T→L→M→I→Θ→J→N)
        self.assertEqual(components, [1, 2, 3, 4, 5, 6, 7])

    def test_vector_arithmetic_does_not_mutate_operands(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0)
        v2 = Vector(0, 1, 0, 0, 0, 0, 0)
        _ = v1 + v2
        self.assertEqual(v1, Vector(1, 0, 0, 0, 0, 0, 0))
        self.assertEqual(v2, Vector(0, 1, 0, 0, 0, 0, 0))

    def test_invalid_addition_type_raises(self):
        v = Vector(1, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(TypeError):
            _ = v + "length"
        with self.assertRaises(TypeError):
            _ = v - 5


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

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

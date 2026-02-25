import math
import unittest

from ucon import Dimension, units
from ucon.core import Exponent, Scale, ScaleDescriptor, UnitFactor, UnitProduct


# ---------------------------------------------------------------------------
# DIMENSION – uncovered lines (141, 174, 182)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# SCALE — uncovered lines (236, 240, 252–254, 266–268)
# ---------------------------------------------------------------------------

class TestScaleExtended(unittest.TestCase):

    def test_scale_mul_with_unknown_exponent_hits_nearest(self):
        # Construct two strange scales (base10^7 * base10^5 = base10^12 = tera)
        s = Scale.nearest(10**7) * Scale.nearest(10**5)
        self.assertIs(s, Scale.tera)

    def test_scale_div_hits_nearest(self):
        # giga / kilo = 10^(9-3) = 10^6 = mega
        self.assertIs(Scale.giga / Scale.kilo, Scale.mega)

    def test_scale_mul_non_unit_non_scale(self):
        self.assertEqual(Scale.kilo.__mul__("nope"), NotImplemented)

    def test_scale_div_non_scale(self):
        self.assertEqual(Scale.kilo.__truediv__("bad"), NotImplemented)


# ---------------------------------------------------------------------------
# UNIT — uncovered lines (290, 293–295, 304, 307)
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# COMPOSITE UNIT — uncovered lines (356, 362–363, 391–378, 424→exit,
#                                   433, 437→exit, 444, 451, 456,
#                                   464–475, 478–498, 507–514, 520–522, 525)
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# QUANTITY (`Number`) uncovered paths (quantity eq, magnitude eq, etc.)
# ---------------------------------------------------------------------------

class TestNumberExtended(unittest.TestCase):

    def test_number_equality_scaled_units(self):
        from ucon import Number, units

        km = Scale.kilo * units.meter
        n1 = Number(unit=km, quantity=1)
        n2 = Number(unit=units.meter, quantity=1000)
        # They should be equal in numeric magnitude
        self.assertEqual(n1, n2)

    def test_number_equality_dimension_mismatch(self):
        from ucon import Number, units
        n1 = Number(unit=units.meter, quantity=1)
        n2 = Number(unit=units.second, quantity=1)
        self.assertNotEqual(n1, n2)

    def test_number_eq_raises_for_bad_type(self):
        from ucon import Number
        with self.assertRaises(TypeError):
            _ = Number(unit=UnitFactor("m", dimension=Dimension.length), quantity=1) == 10



from unittest import TestCase

from ucon.dimension import Dimension
from ucon.unit import Unit


class TestUnit(TestCase):

    unit_name = 'second'
    unit_type = 'time'
    unit_aliases = ('seconds', 'secs', 's', 'S')
    unit = Unit(*unit_aliases, name=unit_name, dimension=Dimension.time)

    def test___repr__(self):
        self.assertEqual(f'<{self.unit_type} | {self.unit_name}>', str(self.unit))

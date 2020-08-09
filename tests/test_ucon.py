from unittest import TestCase

from ucon import Unit


class TestUnit(TestCase):

    unit_name = 'second'
    unit_aliases = ('seconds', 'secs', 's', 'S')
    unit = Unit(unit_name, *unit_aliases)

    def test___repr__(self):
        self.assertEqual(f'<{self.unit_name}>', str(self.unit))


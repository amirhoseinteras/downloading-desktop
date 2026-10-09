import unittest
from downloading import human_size
class Tests(unittest.TestCase):
    def test_human_size(self):
        self.assertTrue(human_size(2048).endswith("KB"))
        self.assertEqual(human_size(0),"—")

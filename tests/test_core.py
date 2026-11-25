import unittest

from downloading import APP_NAME, APP_VERSION, human_size


class Tests(unittest.TestCase):
    def test_human_size(self):
        self.assertTrue(human_size(2048).endswith("KB"))
        self.assertEqual(human_size(0), "—")

    def test_release_identity(self):
        self.assertEqual(APP_NAME, "AmigaNLoad")
        self.assertEqual(APP_VERSION, "3.2")


if __name__ == "__main__":
    unittest.main()

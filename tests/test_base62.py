import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import ALPHABET, decode, encode  # noqa: E402


class TestEncode(unittest.TestCase):
    def test_zero_is_zero_not_empty(self):
        self.assertEqual(encode(0), "0")

    def test_single_digits(self):
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_carry(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(3843), "ZZ")
        self.assertEqual(encode(3844), "100")

    def test_alphabet_order(self):
        self.assertEqual(ALPHABET, "0123456789" + "abcdefghijklmnopqrstuvwxyz"
                         + "ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_non_int_rejected(self):
        for bad in (1.0, "1", None, True):
            with self.assertRaises(TypeError):
                encode(bad)


class TestDecode(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("100"), 3844)

    def test_round_trip(self):
        for n in list(range(0, 5000)) + [10 ** 9, 2 ** 64, 100_000_000]:
            self.assertEqual(decode(encode(n)), n)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_bad_characters_rejected(self):
        for bad in ("-1", "a b", "가", "a!", "_"):
            with self.assertRaises(ValueError):
                decode(bad)

    def test_non_str_rejected(self):
        with self.assertRaises(TypeError):
            decode(10)


if __name__ == "__main__":
    unittest.main()

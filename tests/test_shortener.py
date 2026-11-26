"""SPEC.md 6절 S1~S11: 단축기 경계 사례.

테스트 본문은 ShortenerContract에 두고 make_shortener()만 바꿔 끼운다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import encode  # noqa: E402
from hash_table import HashTable  # noqa: E402
from shortener import InvalidURLError, Shortener  # noqa: E402


class ShortenerContract:
    table_factory = None

    def make_shortener(self):
        return Shortener(table_factory=self.table_factory)

    # S1
    def test_codes_are_sequential_base62(self):
        s = self.make_shortener()
        codes = [s.shorten("https://example.com/%d" % i) for i in range(1, 64)]
        self.assertEqual(codes[0], "1")
        self.assertEqual(codes[1], "2")
        self.assertEqual(codes[60], "Z")    # 61번째
        self.assertEqual(codes[61], "10")   # 62번째
        self.assertEqual(codes, [encode(i) for i in range(1, 64)])

    # S2
    def test_same_url_same_code(self):
        s = self.make_shortener()
        a = s.shorten("https://www.yonsei.ac.kr")
        b = s.shorten("https://www.yonsei.ac.kr")
        self.assertEqual(a, b)
        self.assertEqual(len(s), 1)
        self.assertEqual(s.shorten("https://github.com"), "2")

    # S3
    def test_round_trip(self):
        s = self.make_shortener()
        for url in ("https://github.com", "http://localhost:8000/x?y=1",
                    "https://lec-algorithm.github.io/lecture/"):
            self.assertEqual(s.expand(s.shorten(url)), url)

    # S4
    def test_colliding_urls_get_different_codes(self):
        s = self.make_shortener()
        probe = self.table_factory(capacity=11, max_load=None)
        target = probe.index_of("https://example.com/0")
        same = ["https://example.com/0"]
        i = 1
        while len(same) < 3:
            u = "https://example.com/%d" % i
            if probe.index_of(u) == target:
                same.append(u)
            i += 1
        codes = [s.shorten(u) for u in same]
        self.assertEqual(len(codes), 3)
        self.assertNotEqual(codes[0], codes[1])
        self.assertNotEqual(codes[1], codes[2])
        self.assertNotEqual(codes[0], codes[2])
        for u, c in zip(same, codes):
            self.assertEqual(s.expand(c), u)

    # S5
    def test_expand_unknown(self):
        s = self.make_shortener()
        s.shorten("https://github.com")
        for bad in ("2", "", "!!", None, 1, "01"):
            with self.assertRaises(KeyError):
                s.expand(bad)

    # S6
    def test_invalid_urls(self):
        s = self.make_shortener()
        bad_urls = ["", "   ", "ftp://files.example.com", "www.yonsei.ac.kr",
                    "https://", "https:///path", "http:// example.com",
                    "javascript:alert(1)", "https://a.com/\x00x",
                    "https://example.com/" + "a" * 2029, None, 123]
        self.assertEqual(len(bad_urls[9]), 2049)
        for bad in bad_urls:
            with self.assertRaises(InvalidURLError, msg=repr(bad)[:60]):
                s.shorten(bad)
        self.assertTrue(issubclass(InvalidURLError, ValueError))
        self.assertEqual(len(s), 0)

    # S7
    def test_invalid_url_does_not_use_a_number(self):
        s = self.make_shortener()
        self.assertEqual(s.shorten("https://a.com"), "1")
        with self.assertRaises(InvalidURLError):
            s.shorten("ftp://files.example.com")
        self.assertEqual(s.shorten("https://b.com"), "2")

    # S8
    def test_surrounding_whitespace_ignored(self):
        s = self.make_shortener()
        a = s.shorten("  https://github.com\n")
        self.assertEqual(s.shorten("https://github.com"), a)
        self.assertEqual(s.expand(a), "https://github.com")

    # S9
    def test_scheme_and_host_case_insensitive(self):
        s = self.make_shortener()
        a = s.shorten("HTTPS://WWW.Yonsei.ac.kr/Path")
        b = s.shorten("https://www.yonsei.ac.kr/Path")
        self.assertEqual(a, b)
        self.assertEqual(s.expand(a), "https://www.yonsei.ac.kr/Path")
        c = s.shorten("https://www.yonsei.ac.kr/path")
        self.assertNotEqual(a, c)

    # S10
    def test_query_fragment_korean_and_max_length(self):
        s = self.make_shortener()
        for url in ("https://example.com/a?b=1&c=2#top",
                    "https://ko.wikipedia.org/wiki/해시_테이블",
                    "https://example.com/" + "a" * 2028):
            self.assertEqual(s.expand(s.shorten(url)), url)
        self.assertEqual(len("https://example.com/" + "a" * 2028), 2048)

    # S11
    def test_many_urls(self):
        s = self.make_shortener()
        codes = []
        for i in range(1000):
            codes.append(s.shorten("https://example.com/page/%d" % i))
        self.assertEqual(len(s), 1000)
        ordered = sorted(codes)
        for a, b in zip(ordered, ordered[1:]):
            self.assertNotEqual(a, b)
        for i, c in enumerate(codes):
            self.assertEqual(s.expand(c), "https://example.com/page/%d" % i)


class TestShortenerWithChaining(ShortenerContract, unittest.TestCase):
    table_factory = HashTable


if __name__ == "__main__":
    unittest.main()

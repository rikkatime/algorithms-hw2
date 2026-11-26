"""SPEC.md 6절 H1~H12: 해시 테이블 경계 사례.

테스트 본문은 HashTableContract에 두고 make_table()만 바꿔 끼운다.
같은 테스트를 다른 충돌 처리 방식의 테이블에도 돌릴 수 있다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable, horner, horner_steps  # noqa: E402


def is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def colliding_keys(table, count, prefix="k"):
    """table에서 같은 칸에 떨어지는 서로 다른 키 count개를 찾는다."""
    target = None
    found = []
    i = 0
    while len(found) < count:
        key = "%s%d" % (prefix, i)
        idx = table.index_of(key)
        if target is None:
            target = idx
        if idx == target:
            found.append(key)
        i += 1
    return found


class HashTableContract:
    """모든 해시 테이블이 지켜야 하는 동작. make_table을 덮어쓴다."""

    def make_table(self, **kw):
        raise NotImplementedError

    # H1
    def test_empty_table(self):
        t = self.make_table()
        self.assertEqual(len(t), 0)
        self.assertIsNone(t.get("x"))
        self.assertEqual(t.get("x", "기본"), "기본")
        self.assertFalse("x" in t)
        with self.assertRaises(KeyError):
            t.remove("x")

    def test_put_then_get(self):
        t = self.make_table()
        t.put("https://github.com", "1")
        self.assertEqual(t.get("https://github.com"), "1")
        self.assertTrue("https://github.com" in t)
        self.assertEqual(len(t), 1)

    # H2
    def test_put_same_key_updates_value(self):
        t = self.make_table()
        t.put("a", 1)
        t.put("a", 2)
        self.assertEqual(t.get("a"), 2)
        self.assertEqual(len(t), 1)

    # H3
    def test_colliding_keys_all_found(self):
        t = self.make_table(capacity=11, max_load=None)
        keys = colliding_keys(t, 4)
        for i, k in enumerate(keys):
            t.put(k, i)
        for i, k in enumerate(keys):
            self.assertEqual(t.get(k), i)
        self.assertEqual(len(t), 4)

    # H4
    def test_remove_head_middle_tail_of_collision_group(self):
        for which in (0, 1, 2):
            t = self.make_table(capacity=11, max_load=None)
            keys = colliding_keys(t, 3)
            for i, k in enumerate(keys):
                t.put(k, i)
            t.remove(keys[which])
            self.assertFalse(keys[which] in t)
            self.assertEqual(len(t), 2)
            for i, k in enumerate(keys):
                if i != which:
                    self.assertEqual(t.get(k), i, "remove(%d) 뒤에 %s를 못 찾음" % (which, k))

    def test_remove_then_put_again(self):
        t = self.make_table()
        t.put("a", 1)
        t.remove("a")
        self.assertEqual(len(t), 0)
        t.put("a", 3)
        self.assertEqual(t.get("a"), 3)

    # H5
    def test_empty_string_key(self):
        t = self.make_table()
        self.assertEqual(t.index_of(""), 0)
        t.put("", "빈 키")
        self.assertEqual(t.get(""), "빈 키")

    def test_korean_key(self):
        t = self.make_table()
        t.put("https://연세.kr/국제캠퍼스", "k")
        self.assertEqual(t.get("https://연세.kr/국제캠퍼스"), "k")

    # H6
    def test_non_str_key_rejected(self):
        t = self.make_table()
        for bad in (1, None, b"bytes", ("a",)):
            with self.assertRaises(TypeError):
                t.put(bad, 1)
            with self.assertRaises(TypeError):
                t.get(bad)

    # H7
    def test_index_is_horner(self):
        t = self.make_table(capacity=97, max_load=None)
        self.assertEqual(t.index_of("a"), 0)       # 97 mod 97
        self.assertEqual(t.index_of("ab"), 1)      # (31*0 + 98) mod 97
        self.assertEqual(t.index_of("stop"), 9)    # 18 → 92 → 53 → 9
        for key in ("stop", "pots", "https://www.yonsei.ac.kr"):
            self.assertEqual(t.index_of(key), horner(key, 97))

    # H8
    def test_grows_to_prime_and_keeps_keys(self):
        t = self.make_table(capacity=11)
        for i in range(200):
            t.put("https://example.com/%d" % i, i)
        self.assertGreater(t.capacity, 11)
        self.assertTrue(is_prime(t.capacity), t.capacity)
        self.assertEqual(len(t), 200)
        for i in range(200):
            self.assertEqual(t.get("https://example.com/%d" % i), i)

    # H11
    def test_bad_arguments(self):
        for cap in (0, -1):
            with self.assertRaises(ValueError):
                self.make_table(capacity=cap)
        for load in (0, -0.5):
            with self.assertRaises(ValueError):
                self.make_table(max_load=load)

    # H12
    def test_items_returns_each_pair_once(self):
        t = self.make_table(capacity=11, max_load=None)
        for i in range(9):
            t.put("key%d" % i, i)
        pairs = sorted(t.items())
        self.assertEqual(pairs, sorted(("key%d" % i, i) for i in range(9)))

    def test_probes_hit_at_least_one(self):
        t = self.make_table(capacity=11, max_load=None)
        for i in range(8):
            t.put("key%d" % i, i)
        for i in range(8):
            self.assertGreaterEqual(t.probes("key%d" % i), 1)


class TestHorner(unittest.TestCase):
    def test_steps_match_hash(self):
        steps = horner_steps("stop", 97)
        self.assertEqual([s[0] for s in steps], list("stop"))
        self.assertEqual([s[1] for s in steps], [115, 116, 111, 112])
        self.assertEqual([s[3] for s in steps], [18, 92, 53, 9])
        self.assertEqual(steps[-1][3], horner("stop", 97))

    def test_same_letters_different_slots(self):
        # 더하기 해시라면 모두 같은 칸. 호너는 글자 순서를 본다
        slots = [horner(w, 97) for w in ("stop", "pots", "tops", "spot")]
        self.assertNotEqual(slots[0], slots[1])

    def test_deterministic(self):
        # 내장 hash()와 달리 실행할 때마다 같다
        self.assertEqual(horner("https://github.com", 11),
                         horner("https://github.com", 11))


class TestChainingHashTable(HashTableContract, unittest.TestCase):
    def make_table(self, **kw):
        return HashTable(**kw)

    def test_new_node_goes_to_end_of_chain(self):
        t = self.make_table(capacity=11, max_load=None)
        keys = colliding_keys(t, 3)
        for k in keys:
            t.put(k, k)
        chain = t.buckets()[t.index_of(keys[0])]
        self.assertEqual([k for k, _ in chain], keys)

    # H9
    def test_no_resize_when_max_load_none(self):
        t = self.make_table(capacity=7, max_load=None)
        for i in range(30):
            t.put("u%d" % i, i)
        self.assertEqual(t.capacity, 7)
        self.assertGreater(t.load_factor(), 4)
        for i in range(30):
            self.assertEqual(t.get("u%d" % i), i)

    def test_default_resize_threshold(self):
        t = self.make_table(capacity=11)  # max_load 기본 2.0
        for i in range(22):
            t.put("u%d" % i, i)
        self.assertEqual(t.capacity, 11)   # 22/11 = 2.0, 넘지 않음
        t.put("u22", 22)
        self.assertEqual(t.capacity, 23)   # 2*11+1 = 23 (소수)

    # H10
    def test_probe_counts(self):
        t = self.make_table(capacity=11, max_load=None)
        keys = colliding_keys(t, 3)
        for k in keys:
            t.put(k, k)
        self.assertEqual([t.probes(k) for k in keys], [1, 2, 3])
        # 같은 칸의 없는 키: 체인 길이만큼
        other = colliding_keys(t, 4)[3]
        self.assertFalse(other in t)
        self.assertEqual(t.probes(other), 3)
        # 빈 칸의 없는 키: 0
        empty_idx = (t.index_of(keys[0]) + 1) % 11
        i = 0
        while t.index_of("e%d" % i) != empty_idx:
            i += 1
        self.assertEqual(t.probes("e%d" % i), 0)


if __name__ == "__main__":
    unittest.main()

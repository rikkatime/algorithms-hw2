"""과제: 선형 탐지 해시 테이블.

HashTableContract(체이닝과 같은 테스트)를 그대로 돌리고,
선형 탐지에만 있는 경계 사례(끝 칸 → 0번 칸, 가득 찬 테이블, 뒤로 당기기 삭제)를 더한다.
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from linear_probing import LinearProbingHashTable, TableFullError  # noqa: E402
from test_hash_table import HashTableContract  # noqa: E402


def keys_with_home(table, home, count, prefix="w"):
    """자기 칸이 home인 서로 다른 키 count개."""
    out = []
    i = 0
    while len(out) < count:
        k = "%s%d" % (prefix, i)
        if table.index_of(k) == home:
            out.append(k)
        i += 1
    return out


class TestLinearProbingContract(HashTableContract, unittest.TestCase):
    def make_table(self, **kw):
        return LinearProbingHashTable(**kw)


class TestLinearProbing(unittest.TestCase):
    def test_collision_goes_to_next_slot(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        a, b, c = keys_with_home(t, 3, 3)
        for k in (a, b, c):
            t.put(k, k)
        self.assertEqual([t.slot_of(k) for k in (a, b, c)], [3, 4, 5])
        self.assertEqual([t.probes(k) for k in (a, b, c)], [1, 2, 3])
        self.assertEqual(t.probe_path(c), [3, 4, 5])

    def test_wraparound_from_last_slot_to_zero(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        a, b, c = keys_with_home(t, 10, 3)
        for k in (a, b, c):
            t.put(k, k)
        self.assertEqual([t.slot_of(k) for k in (a, b, c)], [10, 0, 1])
        for k in (a, b, c):
            self.assertEqual(t.get(k), k)
        self.assertEqual(t.probe_path(c), [10, 0, 1])
        # 없는 키(자기 칸 10)는 10, 0, 1을 보고 빈 2번 칸에서 멈춘다: 4칸
        d = keys_with_home(t, 10, 4)[3]
        self.assertFalse(d in t)
        self.assertEqual(t.probes(d), 4)

    def test_remove_across_wraparound_shifts_back(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        a, b, c = keys_with_home(t, 10, 3)
        for k in (a, b, c):
            t.put(k, k)
        t.remove(a)
        self.assertFalse(a in t)
        self.assertEqual(t.slot_of(b), 10)   # 0번 칸에서 10번 칸으로 당겨짐
        self.assertEqual(t.slot_of(c), 0)
        self.assertEqual(t.get(b), b)
        self.assertEqual(t.get(c), c)
        self.assertIsNone(t.slots()[1])

    def test_remove_does_not_move_key_before_its_home(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        a, b = keys_with_home(t, 3, 2)
        x = keys_with_home(t, 5, 1, prefix="x")[0]
        for k in (a, b, x):
            t.put(k, k)          # a:3, b:4, x:5
        t.remove(a)              # b는 3으로 당겨지고, x는 자기 칸 5에 남아야 한다
        self.assertEqual(t.slot_of(b), 3)
        self.assertEqual(t.slot_of(x), 5)
        self.assertIsNone(t.slots()[4])

    def test_full_table(self):
        t = LinearProbingHashTable(capacity=7, max_load=None)
        keys = ["f%d" % i for i in range(7)]
        for i, k in enumerate(keys):
            t.put(k, i)
        self.assertEqual(len(t), 7)
        self.assertEqual(t.load_factor(), 1.0)
        for i, k in enumerate(keys):
            self.assertEqual(t.get(k), i)
        # 있는 키의 값 바꾸기는 된다
        t.put(keys[3], "new")
        self.assertEqual(t.get(keys[3]), "new")
        # 새 키는 넣을 수 없다
        with self.assertRaises(TableFullError):
            t.put("one-more", 1)
        # 없는 키를 찾아도 끝없이 돌지 않는다: M칸을 보고 멈춘다
        self.assertFalse("absent" in t)
        self.assertIsNone(t.get("absent"))
        self.assertEqual(t.probes("absent"), 7)
        with self.assertRaises(KeyError):
            t.remove("absent")
        # 하나 지우면 다시 넣을 수 있다
        t.remove(keys[0])
        t.put("one-more", 1)
        self.assertEqual(t.get("one-more"), 1)
        for k in keys[1:]:
            self.assertTrue(k in t)

    def test_unsuccessful_search_counts_empty_slot(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        self.assertEqual(t.probes("nothing"), 1)

    def test_default_resize_threshold(self):
        t = LinearProbingHashTable(capacity=11)  # max_load 기본 0.75
        for i in range(8):
            t.put("u%d" % i, i)
        self.assertEqual(t.capacity, 11)   # 8/11 = 0.73
        t.put("u8", 8)
        self.assertEqual(t.capacity, 23)   # 9/11 = 0.82 > 0.75

    def test_no_resize_when_max_load_none(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        for i in range(11):
            t.put("u%d" % i, i)
        self.assertEqual(t.capacity, 11)

    def test_random_inserts_and_removes(self):
        rng = random.Random(7)
        t = LinearProbingHashTable(capacity=401, max_load=None)
        keys = ["https://example.com/%d/%d" % (i, rng.randint(0, 10 ** 6)) for i in range(350)]
        for i, k in enumerate(keys):
            t.put(k, i)
        removed = keys[:]
        rng.shuffle(removed)
        removed = removed[:175]
        for k in removed:
            t.remove(k)
        self.assertEqual(len(t), 175)
        removed.sort()
        for i, k in enumerate(keys):
            lo, hi = 0, len(removed)
            while lo < hi:
                mid = (lo + hi) // 2
                if removed[mid] < k:
                    lo = mid + 1
                else:
                    hi = mid
            gone = lo < len(removed) and removed[lo] == k
            if gone:
                self.assertFalse(k in t)
            else:
                self.assertEqual(t.get(k), i)


if __name__ == "__main__":
    unittest.main()

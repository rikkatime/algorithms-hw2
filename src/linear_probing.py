"""선형 탐지(open addressing) 해시 테이블. HashTable과 같은 연산을 제공한다.

- 칸마다 키 하나. 자기 칸(호너 해시)이 차 있으면 다음 칸(+1, 끝 칸 다음은 0번 칸)을 본다.
- 삭제는 묘비(tombstone) 없이 뒤로 당기기(backward shift)로 한다.
  지운 자리 뒤의 덩어리에서, 지운 자리로 옮겨도 찾을 수 있는 키를 당겨 와 빈 칸을 메운다.
- 탐색 비용은 들여다본 칸 수. 실패 탐색은 마지막에 본 빈 칸까지 센다.
- 파이썬 내장 사전·집합과 내장 해시 함수를 쓰지 않는다.
"""
from hash_table import check_args, check_key, horner, horner_steps, next_prime


class TableFullError(RuntimeError):
    """크기 늘리기를 끈(max_load=None) 테이블이 가득 찼는데 새 키를 넣으려 함."""


class LinearProbingHashTable:
    kind = "linear"

    def __init__(self, capacity=11, max_load=0.75):
        check_args(capacity, max_load)
        self._keys = [None] * capacity
        self._values = [None] * capacity
        self._n = 0
        self.max_load = max_load

    # ---- 기본 연산 ----------------------------------------------------

    @property
    def capacity(self):
        return len(self._keys)

    def __len__(self):
        return self._n

    def load_factor(self):
        return self._n / len(self._keys)

    def index_of(self, key):
        """자기 칸(home). 실제로 들어간 칸은 slot_of로 본다."""
        check_key(key)
        return horner(key, len(self._keys))

    def _locate(self, key):
        """(찾은 칸 또는 -1, 처음 만난 빈 칸 또는 -1, 들여다본 칸 수)"""
        m = len(self._keys)
        i = self.index_of(key)
        for step in range(m):
            k = self._keys[i]
            if k is None:
                return -1, i, step + 1
            if k == key:
                return i, -1, step + 1
            i = (i + 1) % m
        return -1, -1, m  # 가득 찼고 키가 없다

    def put(self, key, value):
        found, empty, _ = self._locate(key)
        if found >= 0:
            self._values[found] = value
            return
        if empty < 0:
            if self.max_load is None:
                raise TableFullError("테이블이 가득 찼습니다 (칸 %d개)" % len(self._keys))
            self._resize(next_prime(2 * len(self._keys) + 1))
            found, empty, _ = self._locate(key)
        self._keys[empty] = key
        self._values[empty] = value
        self._n += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._resize(next_prime(2 * len(self._keys) + 1))

    def get(self, key, default=None):
        found, _, _ = self._locate(key)
        return default if found < 0 else self._values[found]

    def __contains__(self, key):
        return self._locate(key)[0] >= 0

    def slot_of(self, key):
        """키가 실제로 들어 있는 칸. 없으면 -1."""
        return self._locate(key)[0]

    def remove(self, key):
        """키를 지우고 뒤의 덩어리를 당겨 빈 칸을 메운다. 없으면 KeyError."""
        i, _, _ = self._locate(key)
        if i < 0:
            raise KeyError(key)
        m = len(self._keys)
        j = i
        for _ in range(m - 1):  # 가득 찬 테이블에서도 한 바퀴를 넘지 않는다
            j = (j + 1) % m
            k = self._keys[j]
            if k is None:
                break
            home = horner(k, m)
            # home이 (i, j] 구간(원형)에 있으면 j에 그대로 두어야 찾을 수 있다.
            if i <= j:
                stays = i < home <= j
            else:
                stays = home > i or home <= j
            if not stays:
                self._keys[i], self._values[i] = k, self._values[j]
                i = j
        self._keys[i] = None
        self._values[i] = None
        self._n -= 1

    def items(self):
        out = []
        for k, v in zip(self._keys, self._values):
            if k is not None:
                out.append((k, v))
        return out

    def _resize(self, new_capacity):
        old = self.items()
        self._keys = [None] * new_capacity
        self._values = [None] * new_capacity
        self._n = 0
        saved, self.max_load = self.max_load, None
        try:
            for k, v in old:
                self.put(k, v)
        finally:
            self.max_load = saved

    # ---- 실험·화면용 ----------------------------------------------------

    def probes(self, key):
        """탐색 비용 = 들여다본 칸 수 (실패는 빈 칸까지, 가득 찬 테이블의 실패는 M)."""
        return self._locate(key)[2]

    def probe_path(self, key):
        """탐색하며 들여다본 칸 번호들."""
        m = len(self._keys)
        i = self.index_of(key)
        path = []
        for _ in range(self._locate(key)[2]):
            path.append(i)
            i = (i + 1) % m
        return path

    def horner_steps(self, key):
        check_key(key)
        return horner_steps(key, len(self._keys))

    def slots(self):
        """칸마다 (키, 값) 또는 None."""
        out = []
        for k, v in zip(self._keys, self._values):
            out.append(None if k is None else (k, v))
        return out

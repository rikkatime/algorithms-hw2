"""개별 체이닝 해시 테이블 (SPEC.md 3절).

- 칸마다 단일 연결 리스트. 새 노드는 리스트 끝에 붙인다.
- 해시: 호너 방식 h <- (31*h + ord(c)) mod M
- 파이썬 내장 사전·집합과 내장 해시 함수를 쓰지 않는다 (SPEC 3절).
"""

R = 31  # 호너 해시의 기수


def horner(s, m):
    """문자열 s의 칸 번호. 글자마다 h = (31*h + ord(c)) mod m."""
    h = 0
    for c in s:
        h = (R * h + ord(c)) % m
    return h


def horner_steps(s, m):
    """호너 해시의 계산 과정. 글자마다 (글자, 글자 코드, 이전 h, 새 h)."""
    steps = []
    h = 0
    for c in s:
        new_h = (R * h + ord(c)) % m
        steps.append((c, ord(c), h, new_h))
        h = new_h
    return steps


def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def next_prime(n):
    """n 이상인 가장 작은 소수."""
    while not is_prime(n):
        n += 1
    return n


def check_key(key):
    if not isinstance(key, str):
        raise TypeError("키는 문자열만 됩니다: %r" % (key,))


def check_args(capacity, max_load):
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("capacity는 1 이상의 정수여야 합니다: %r" % (capacity,))
    if max_load is not None and not max_load > 0:
        raise ValueError("max_load는 0보다 커야 합니다 (끄려면 None): %r" % (max_load,))


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next=None):
        self.key = key
        self.value = value
        self.next = next


class HashTable:
    """문자열 키 -> 값. 충돌은 개별 체이닝으로 처리한다."""

    kind = "chaining"

    def __init__(self, capacity=11, max_load=2.0):
        check_args(capacity, max_load)
        self._slots = [None] * capacity
        self._n = 0
        self.max_load = max_load

    # ---- 기본 연산 ----------------------------------------------------

    @property
    def capacity(self):
        return len(self._slots)

    def __len__(self):
        return self._n

    def load_factor(self):
        return self._n / len(self._slots)

    def index_of(self, key):
        check_key(key)
        return horner(key, len(self._slots))

    def put(self, key, value):
        """없으면 리스트 끝에 넣고, 있으면 값만 바꾼다."""
        i = self.index_of(key)
        node = self._slots[i]
        if node is None:
            self._slots[i] = _Node(key, value)
        else:
            while True:
                if node.key == key:
                    node.value = value
                    return
                if node.next is None:
                    break
                node = node.next
            node.next = _Node(key, value)
        self._n += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._resize(next_prime(2 * len(self._slots) + 1))

    def _find(self, key):
        node = self._slots[self.index_of(key)]
        while node is not None:
            if node.key == key:
                return node
            node = node.next
        return None

    def get(self, key, default=None):
        node = self._find(key)
        return default if node is None else node.value

    def __contains__(self, key):
        return self._find(key) is not None

    def remove(self, key):
        """키를 지운다. 없으면 KeyError."""
        i = self.index_of(key)
        prev = None
        node = self._slots[i]
        while node is not None:
            if node.key == key:
                if prev is None:
                    self._slots[i] = node.next
                else:
                    prev.next = node.next
                self._n -= 1
                return
            prev, node = node, node.next
        raise KeyError(key)

    def items(self):
        """(키, 값) 쌍을 칸 순서, 리스트 순서대로."""
        out = []
        for head in self._slots:
            node = head
            while node is not None:
                out.append((node.key, node.value))
                node = node.next
        return out

    def _resize(self, new_capacity):
        old = self._slots
        self._slots = [None] * new_capacity
        self._n = 0
        saved, self.max_load = self.max_load, None  # 다시 넣는 동안 또 늘리지 않는다
        try:
            for head in old:
                node = head
                while node is not None:
                    self.put(node.key, node.value)
                    node = node.next
        finally:
            self.max_load = saved

    # ---- 실험·화면용 ----------------------------------------------------

    def probes(self, key):
        """탐색 비용 = 비교한 노드 수.
        성공: 찾은 노드가 k번째면 k. 실패: 그 칸 리스트의 길이(빈 칸이면 0)."""
        count = 0
        node = self._slots[self.index_of(key)]
        while node is not None:
            count += 1
            if node.key == key:
                return count
            node = node.next
        return count

    def horner_steps(self, key):
        check_key(key)
        return horner_steps(key, len(self._slots))

    def buckets(self):
        """칸마다 [(키, 값), ...] 리스트. 화면에 그리기 위한 것."""
        out = []
        for head in self._slots:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            out.append(chain)
        return out

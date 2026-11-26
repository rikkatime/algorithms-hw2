"""base62 인코딩: 0 이상의 정수 <-> 0-9, a-z, A-Z 순서의 62진법 문자열.

    encode(0)    == "0"
    encode(61)   == "Z"
    encode(62)   == "10"
    encode(3844) == "100"
    decode(encode(n)) == n
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def _digit_value(ch):
    """글자 하나의 값(0~61). 알파벳에 없으면 -1."""
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "a" <= ch <= "z":
        return ord(ch) - ord("a") + 10
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 36
    return -1


def encode(n):
    """0 이상의 정수 n을 base62 문자열로 바꾼다.

    bool, 정수가 아닌 값은 TypeError, 음수는 ValueError.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("encode()에는 정수만 넣을 수 있습니다: %r" % (n,))
    if n < 0:
        raise ValueError("encode()에는 0 이상의 정수만 넣을 수 있습니다: %d" % n)
    if n == 0:
        return ALPHABET[0]  # 흔한 구현은 여기서 ""을 돌려준다
    digits = []
    while n > 0:
        n, r = divmod(n, BASE)
        digits.append(ALPHABET[r])
    digits.reverse()  # 나머지는 아래 자리부터 나오므로 뒤집는다
    return "".join(digits)


def decode(s):
    """base62 문자열 s를 정수로 되돌린다.

    문자열이 아니면 TypeError, 빈 문자열이나 알파벳 밖의 글자는 ValueError.
    """
    if not isinstance(s, str):
        raise TypeError("decode()에는 문자열만 넣을 수 있습니다: %r" % (s,))
    if s == "":
        raise ValueError("decode()에 빈 문자열을 넣을 수 없습니다")
    n = 0
    for ch in s:
        v = _digit_value(ch)
        if v < 0:
            raise ValueError("base62에 없는 글자입니다: %r" % ch)
        n = n * BASE + v
    return n

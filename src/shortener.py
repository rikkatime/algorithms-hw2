"""URL 단축기 (SPEC.md 4절).

코드는 일련번호(1부터)를 base62로 바꾼 것이다. URL의 해시값으로 만들지 않는다.
저장은 직접 만든 해시 테이블 두 개(URL->코드, 코드->URL)로 한다.
"""
from urllib.parse import urlsplit

from base62 import encode
from hash_table import HashTable

MAX_URL_LENGTH = 2048


class InvalidURLError(ValueError):
    """http/https URL이 아니거나 형식이 잘못된 입력."""


def normalize_url(url):
    """검사하고 정규화한 URL을 돌려준다. 잘못되면 InvalidURLError.

    앞뒤 공백을 지우고, 스킴과 호스트를 소문자로 바꾼다. 나머지는 그대로 둔다.
    """
    if not isinstance(url, str):
        raise InvalidURLError("URL은 문자열이어야 합니다")
    url = url.strip()
    if url == "":
        raise InvalidURLError("URL이 비어 있습니다")
    for c in url:
        if c.isspace() or ord(c) < 32 or ord(c) == 127:
            raise InvalidURLError("URL 안에 공백이나 제어 문자가 있습니다")
    try:
        parts = urlsplit(url)
    except ValueError as e:
        raise InvalidURLError("URL 형식이 잘못되었습니다: %s" % e) from None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidURLError("http:// 또는 https://로 시작하는 URL만 줄일 수 있습니다")
    if not parts.netloc or not parts.hostname:
        raise InvalidURLError("URL에 호스트가 없습니다")
    # 스킴과 호스트(netloc)만 소문자로. 사용자 정보가 있으면 그 부분은 그대로 둔다.
    netloc = parts.netloc
    at = netloc.rfind("@")
    netloc = netloc[:at + 1] + netloc[at + 1:].lower()
    rest = url[len(parts.scheme) + 3 + len(parts.netloc):]
    normalized = scheme + "://" + netloc + rest
    if len(normalized) > MAX_URL_LENGTH:
        raise InvalidURLError("URL이 너무 깁니다 (최대 %d자)" % MAX_URL_LENGTH)
    return normalized


class Shortener:
    def __init__(self, table_factory=HashTable):
        self.table_factory = table_factory
        self.url_to_code = table_factory()
        self.code_to_url = table_factory()
        self._next = 1

    def __len__(self):
        return len(self.url_to_code)

    @property
    def table(self):
        """화면에 그리는 URL->코드 테이블."""
        return self.url_to_code

    def shorten(self, url):
        url = normalize_url(url)
        code = self.url_to_code.get(url)
        if code is not None:
            return code
        code = encode(self._next)
        self._next += 1
        self.url_to_code.put(url, code)
        self.code_to_url.put(code, url)
        return code

    def expand(self, code):
        if not isinstance(code, str) or code == "":
            raise KeyError(code)
        url = self.code_to_url.get(code)
        if url is None:
            raise KeyError(code)
        return url

    def normalize(self, url):
        return normalize_url(url)

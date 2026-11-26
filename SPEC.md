# 명세: URL 단축기

초안은 에이전트가 쓰고, **본인이 읽고 고칩니다.** 무엇을 고쳤는지는 이슈에 댓글로 남깁니다.
에이전트는 이 파일을 읽고 구현합니다. 여기 적지 않은 것은 에이전트가 마음대로 정합니다.

## 1. 무엇을 만드는가

사용자가 긴 URL(`http://` 또는 `https://`)을 넣으면 `http://<호스트>/<코드>` 형태의 짧은 링크를 돌려주고,
짧은 링크를 열면 원래 URL로 이동시키는 웹 서비스.
저장은 Python의 `dict`가 아니라 **직접 구현한 해시 테이블**로 한다.

## 2. base62 인코딩

- 파일: `src/base62.py`, 함수 `encode(n) -> str`, `decode(s) -> int`
- 글자 순서는 `0-9`, `a-z`, `A-Z` (값 0~61). 예: `encode(61) == "Z"`, `encode(62) == "10"`, `encode(3844) == "100"`
- `encode(0) == "0"` (빈 문자열이 아니다)
- 음수는 `ValueError`, 정수가 아닌 값(`bool`, 실수, 문자열, `None`)은 `TypeError`
- `decode`: 빈 문자열이나 알파벳 밖의 글자(`-`, 공백, `_`, 한글 등)는 `ValueError`, 문자열이 아니면 `TypeError`
- 모든 `n >= 0`에 대해 `decode(encode(n)) == n`

## 3. 해시 테이블

- 파일: `src/hash_table.py`, 클래스 `HashTable`
- 충돌 처리: **개별 체이닝**. 칸마다 단일 연결 리스트(노드: key, value, next). 새 노드는 리스트 **끝**에 붙인다
- 해시 함수: 주제 08의 **호너 방식**. 문자열 `s`, 칸 수 `M`에 대해
  `h = 0`, 글자마다 `h = (31 * h + ord(c)) mod M`. 마지막 `h`가 칸 번호. 빈 문자열은 0번 칸
- 키는 `str`만 받는다 (아니면 `TypeError`). 값은 아무 것이나
- 처음 크기 `capacity=11`, `capacity < 1`이면 `ValueError`
- 크기 늘리기: 넣은 뒤 적재율 `n / M`이 `max_load`(기본 2.0)를 넘으면 `2M + 1` 이상인 가장 작은 소수로 늘리고 모든 키를 다시 넣는다.
  `max_load=None`이면 늘리지 않는다 (실험용). `max_load <= 0`이면 `ValueError`
- 연산: `put(key, value)`(없으면 넣고 있으면 값만 바꿈), `get(key, default=None)`, `key in table`,
  `remove(key)`(없으면 `KeyError`), `len(table)`, `items()`, `capacity`, `load_factor()`
- 실험·화면용: `index_of(key)`(칸 번호), `horner_steps(key)`(글자마다의 계산 과정), `probes(key)`(탐색 비용), `buckets()`(칸마다의 노드 목록)
- **탐색 비용**은 비교한 노드 수로 센다. 성공 탐색은 찾은 노드가 리스트의 k번째이면 k,
  실패 탐색은 그 칸 리스트의 길이(빈 칸이면 0)
- `src/` 안에서 `dict`, `set`, 내장 `hash()`를 쓰지 않는다 (내장 `hash()`는 실행할 때마다 문자열 해시값이 바뀐다)

## 4. 단축기

- 파일: `src/shortener.py`, 클래스 `Shortener(table_factory=HashTable)`
- 테이블 두 개: URL→코드, 코드→URL. 둘 다 2절의 해시 테이블
- `shorten(url) -> code`
  - 코드는 **일련번호**(1부터)를 base62로 바꾼 것: 첫 URL은 `"1"`, 다음은 `"2"`, …, 62번째는 `"10"`.
    URL의 해시값으로 코드를 만들지 않는다 (서로 다른 URL이 같은 코드를 받을 수 있으므로)
  - 같은 URL을 다시 넣으면 **같은 코드**를 돌려주고 번호를 쓰지 않는다
  - 정규화: 앞뒤 공백은 지운다. 스킴과 호스트는 소문자로 바꾼다. 경로·쿼리·프래그먼트는 그대로 둔다
  - 잘못된 URL은 `InvalidURLError`(`ValueError`의 하위 클래스)를 던지고 번호를 쓰지 않는다
- 잘못된 URL
  - 문자열이 아님, 빈 문자열, 공백뿐
  - 스킴이 `http`/`https`가 아님 (`ftp://…`, `javascript:…`, 스킴 없는 `www.yonsei.ac.kr`)
  - 호스트가 없음 (`https://`, `https:///path`)
  - 중간에 공백이나 제어 문자가 있음 (`http:// example.com`)
  - 정규화한 뒤 길이가 2048자를 넘음
- `expand(code) -> url`: 없는 코드, 빈 문자열, base62 밖의 글자, 문자열이 아닌 값은 모두 `KeyError`
- `len(shortener)`: 저장된 URL 수
- 단축기는 해시 테이블의 공개 연산만 쓴다 (테이블 구현을 바꿔 끼울 수 있게)

## 5. 웹 서버

- 파일: `src/server.py`, 표준 모듈 `http.server`만 쓴다. `make serve`로 포트 8000에서 뜬다 (`--port`로 바꿀 수 있음)

| 요청 | 응답 |
| --- | --- |
| `GET /` | URL 입력 폼 (200) |
| `POST /shorten` (폼 필드 `url`) | 짧은 링크, 코드, URL이 들어간 칸 번호를 보여 주는 화면 (200). 잘못된 URL이면 오류 문구와 폼 (400) |
| `GET /<코드>` | 원래 URL로 `302` 이동 (`Location` 헤더). 없는 코드는 404 화면 |
| `GET /table` | 현재 URL→코드 해시 테이블. 칸마다 연결 리스트의 노드(URL, 코드, 짧은 링크)를 화살표로 잇고 끝은 NULL. 노드마다 호너 해시 계산 과정을 펼쳐 볼 수 있다. 노드가 둘 이상인 칸은 **충돌**로 표시 |
| `POST /demo` | 수업 예시 URL 10개를 넣는다 (충돌 시연용) |
| `POST /reset` | 테이블을 비운다 |

- 짧은 링크의 호스트는 `X-Forwarded-Host`(+ `X-Forwarded-Proto`)를 먼저 보고, 없으면 `Host` 헤더를 쓴다 (Codespaces 프록시 뒤에서 휴대폰으로 열기 위해)
- 화면에 넣는 모든 문자열은 HTML 이스케이프한다
- 화면에는 스크롤바를 표시하지 않는다 (긴 내용은 줄바꿈)

## 6. 경계 사례

**base62**
- B1 `encode(0) == "0"`, `decode("0") == 0`
- B2 자리 올림: 61→`"Z"`, 62→`"10"`, 3843→`"ZZ"`, 3844→`"100"`
- B3 음수 `ValueError`, `bool`·실수·문자열 `TypeError`
- B4 `decode("")`, `decode("-1")`, `decode("가")` 는 `ValueError`
- B5 0~4999와 큰 수(2^64)에서 왕복

**해시 테이블**
- H1 빈 테이블: `len == 0`, `get`은 `None`(또는 기본값), `in`은 `False`, `remove`는 `KeyError`
- H2 같은 키를 두 번 넣으면 값만 바뀌고 `len`은 그대로
- H3 같은 칸에 떨어진 서로 다른 키(충돌) 여럿을 모두 찾을 수 있다
- H4 연결 리스트의 맨 앞·가운데·맨 끝 노드를 지워도 나머지는 그대로 찾는다
- H5 빈 문자열 키(0번 칸), 한글 키
- H6 `str`이 아닌 키는 `TypeError`
- H7 호너 해시 값이 손으로 계산한 값과 같고, 실행할 때마다 같다 (`index_of("a")`, `"ab"` 등)
- H8 적재율이 `max_load`를 넘으면 소수 크기로 늘어나고, 늘어난 뒤에도 모든 키를 찾는다
- H9 `max_load=None`이면 늘어나지 않고 적재율이 1을 넘을 수 있다
- H10 탐색 비용: 빈 칸 실패 0, 체인 길이 L인 칸 실패 L, k번째 노드 성공 k
- H11 `capacity < 1`, `max_load <= 0`은 `ValueError`
- H12 `items()`는 모든 쌍을 정확히 한 번씩 돌려준다

**단축기**
- S1 첫 코드는 `"1"`, 그다음 `"2"`, 61번째 `"Z"`, 62번째 `"10"`
- S2 같은 URL을 두 번 넣으면 같은 코드, 번호를 쓰지 않는다
- S3 `expand(shorten(u)) == u`
- S4 같은 칸에 떨어지는 서로 다른 URL도 서로 다른 코드를 받는다
- S5 없는 코드, `""`, `"!!"`, `None`은 `KeyError`
- S6 잘못된 URL: `""`, `"   "`, `"ftp://files.example.com"`, `"www.yonsei.ac.kr"`, `"https://"`, `"http:// example.com"`, `"javascript:alert(1)"`, 2049자 URL, `None`
- S7 잘못된 URL은 번호를 쓰지 않는다 (다음 정상 URL이 이어지는 코드를 받는다)
- S8 앞뒤 공백을 지운 URL과 같은 코드
- S9 `HTTPS://WWW.Yonsei.ac.kr/Path`는 `https://www.yonsei.ac.kr/Path`와 같은 코드 (경로 대소문자는 유지)
- S10 쿼리·프래그먼트·한글 경로가 있는 URL, 정확히 2048자 URL은 받는다
- S11 URL 1000개(크기 늘리기 포함)를 넣어도 코드가 모두 다르고 모두 되돌아온다

**웹 서버**
- W1 `GET /`는 폼, `POST /shorten`은 짧은 링크
- W2 잘못된 URL은 400, 없는 코드는 404
- W3 짧은 링크를 열면 302와 원래 URL
- W4 `X-Forwarded-Host`가 있으면 그 호스트로 짧은 링크를 만든다
- W5 `/table`에 칸 번호, 노드, 호너 계산 과정, 충돌 표시가 나온다
- W6 `<script>`가 든 URL도 화면에서 이스케이프된다

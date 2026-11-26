# 구현 계획

SPEC.md를 기준으로 한다. 단계마다 테스트를 먼저 쓰고, 구현은 그 테스트를 통과시키는 데까지만 한다.
`src/`에서는 `dict`, `set`, 내장 `hash()`를 쓰지 않는다.

## 0. 공통 규칙

- 테스트는 `unittest`, `make test`(= `python3 -m unittest discover -s tests -v`)로 돌린다
- 테스트 파일은 맨 위에서 `src/`를 `sys.path`에 넣고 모듈을 가져온다
- 외부 라이브러리 없음. 표준 모듈만

## 1. base62 (`src/base62.py`) — 끝남 (1단계)

## 2. 테스트 먼저 (4단계 앞부분)

1. `tests/test_hash_table.py`: SPEC 6절 H1~H12를 그대로 옮긴다
   - 충돌 키는 테스트 안에서 `index_of`로 같은 칸에 떨어지는 키를 찾아서 쓴다 (손으로 고르지 않는다)
   - 테스트 본문은 `HashTableContract` 믹스인에 두고, `make_table(**kw)`만 바꿔 끼우면
     다른 해시 테이블(과제의 선형 탐지)에도 돌릴 수 있게 한다
2. `tests/test_shortener.py`: S1~S11
3. 이 시점에 `make test`는 실패한다 (구현이 없으므로 정상)

## 3. 해시 테이블 (`src/hash_table.py`)

1. `horner_hash(s, m)`, `horner_steps(s, m)` (글자마다 `(글자, 코드, 이전 h, 새 h)`)
2. `_Node(key, value, next)` — 단일 연결 리스트 노드
3. `HashTable.__init__(capacity=11, max_load=2.0)` — 인자 검사, `[None] * capacity`
4. `put` — 칸의 리스트를 따라가며 같은 키면 값 교체, 없으면 끝에 붙이고 `n += 1`, 필요하면 `_resize`
5. `get` / `__contains__` / `remove`(앞 노드와 함께 걸어가며 링크를 끊음)
6. `_resize` — `2M+1` 이상의 가장 작은 소수, 모든 노드를 새 배열에 다시 넣음
7. `probes(key)`, `index_of`, `buckets()`, `items()`, `load_factor()`

## 4. 단축기 (`src/shortener.py`)

1. `InvalidURLError(ValueError)`
2. `normalize_url(url)` — 타입·공백·제어 문자·스킴·호스트·길이 검사, 스킴/호스트 소문자화
   (`urllib.parse.urlsplit` 사용)
3. `Shortener(table_factory=HashTable)` — URL→코드, 코드→URL 두 테이블과 다음 번호(1부터)
4. `shorten` — 정규화 → URL→코드 테이블에 있으면 그 코드 → 없으면 `encode(번호)`, 두 테이블에 넣고 번호 += 1
5. `expand` — 문자열이 아니거나 없으면 `KeyError`
6. 코드는 일련번호로만 만든다. URL의 해시값으로 코드를 만들지 않는다

## 5. 규칙 파일 (5단계)

- `.github/copilot-instructions.md`에 저장소 규칙(금지 문법, make test, 테스트 고치지 않기, git flow)을 적는다
- `grep -n "dict\|set(\|hash(" src/*.py`로 위반을 검사한다

## 6. 실험 (6단계, `experiments/probe_experiment.py`)

- `HashTable(capacity=4093, max_load=None)`에 고정 시드의 무작위 URL을 넣으며 적재율 0.25, 0.5, …, 4에서 멈춤
- 성공: 넣은 키 전부의 `probes` 평균. 실패: 넣지 않은 URL 2000개의 `probes` 평균
- 이론: 성공 `1 + α/2`, 실패 `α`. `experiments/results.csv`, `experiments/results.svg` (SVG는 직접 그림)

## 7. 웹 서버 (7단계, `src/server.py`)

- `http.server.ThreadingHTTPServer` + 잠금 하나. 라우팅은 경로 문자열 비교
- `/`, `POST /shorten`, `GET /<코드>`, `GET /table`, `POST /demo`, `POST /reset`
- 짧은 링크 호스트: `X-Forwarded-Host` → `Host`
- `tests/test_server.py`: 포트 0으로 서버를 띄워 W1~W6을 확인

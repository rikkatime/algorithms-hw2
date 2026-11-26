"""단축 URL 웹 서비스 (SPEC.md 5절). 표준 모듈 http.server만 쓴다.

    make serve                 # 포트 8000
    python3 src/server.py --port 8000
    python3 src/server.py --table linear   # 짧은 링크를 선형 탐지 테이블로 처리

  GET  /            URL 입력 폼
  POST /shorten     짧은 링크 화면 (잘못된 URL은 400)
  GET  /<코드>      원래 URL로 302 이동 (없으면 404)
  GET  /table       URL->코드 해시 테이블 (칸마다 연결 리스트, 호너 계산 과정)
  GET  /table?impl=linear   같은 URL을 넣은 선형 탐지 테이블 (들여다본 칸, 계산 근거)
  POST /demo        수업 예시 URL 10개 넣기 (충돌 시연)
  POST /reset       비우기
"""
import argparse
import html
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, quote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base62 import ALPHABET  # noqa: E402
from hash_table import HashTable  # noqa: E402
from linear_probing import LinearProbingHashTable  # noqa: E402
from shortener import InvalidURLError, Shortener, normalize_url  # noqa: E402

# 수업 슬라이드의 예시 (ftp 주소는 잘못된 입력, yonsei는 두 번)
DEMO_URLS = [
    "https://www.yonsei.ac.kr",
    "https://github.com",
    "https://learnus.yonsei.ac.kr",
    "https://www.yonsei.ac.kr",
    "ftp://files.example.com",
    "https://lec-algorithm.github.io/lecture/",
    "https://docs.python.org/3/",
    "https://portal.yonsei.ac.kr",
    "https://www.python.org",
    "https://library.yonsei.ac.kr",
]

MAX_BODY = 64 * 1024
URL_SAFE = ":/?#[]@!$&'()*+,;=%~"

CSS = """
*{box-sizing:border-box;scrollbar-width:none;-ms-overflow-style:none}
*::-webkit-scrollbar{display:none;width:0;height:0}
html,body{margin:0;background:#f6f7f9;color:#191919;
 font-family:system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;line-height:1.5}
main{max-width:980px;margin:0 auto;padding:20px 16px 48px}
nav{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:18px}
nav a{color:#257de0;text-decoration:none;font-weight:600}
nav .brand{color:#191919;font-size:18px;margin-right:auto}
h1{font-size:22px;margin:4px 0 12px}
.card{background:#fff;border:1px solid #e3e5e8;border-radius:12px;padding:16px;margin:12px 0}
form.inline{display:inline}
input[type=text]{width:100%;font-size:16px;padding:12px;border:1px solid #c9ccd1;border-radius:8px}
button{font-size:15px;padding:10px 16px;border:0;border-radius:8px;background:#257de0;color:#fff;
 font-weight:600;cursor:pointer;margin-top:8px}
button.ghost{background:#eef1f5;color:#191919}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.error{background:#fdecec;border-color:#f3b4b4;color:#8a1c1c}
.short{font-size:22px;font-weight:700;overflow-wrap:anywhere}
.muted{color:#666;font-size:14px}
.url{overflow-wrap:anywhere;word-break:break-all}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.stats{display:flex;gap:10px;flex-wrap:wrap}
.stat{background:#fff;border:1px solid #e3e5e8;border-radius:10px;padding:8px 12px}
.stat b{display:block;font-size:20px}
.bucket{display:flex;align-items:flex-start;gap:6px;flex-wrap:wrap;padding:8px;border-radius:10px;
 border:1px solid transparent;margin:4px 0}
.bucket.collide{background:#fff4ec;border-color:#f6b48f}
.idx{flex:0 0 auto;width:56px;text-align:center;font-weight:700;background:#191919;color:#fff;
 border-radius:8px;padding:8px 0}
.idx small{display:block;font-weight:400;font-size:11px;opacity:.75}
.arrow{flex:0 0 auto;align-self:center;color:#666;font-size:18px}
.null{flex:0 0 auto;align-self:center;color:#999;font-family:ui-monospace,monospace;font-size:13px}
.node{flex:1 1 220px;max-width:320px;background:#fff;border:1px solid #c9ccd1;border-radius:8px;
 padding:8px 10px;font-size:13px}
.node.hl{border:2px solid #257de0;box-shadow:0 0 0 3px #d6e6fa}
.node.cmp{border:2px solid #f2a600}
.node .k{overflow-wrap:anywhere;word-break:break-all}
.node .c{font-weight:700;font-size:15px}
.badge{display:inline-block;font-size:12px;font-weight:700;padding:1px 8px;border-radius:99px;
 background:#ec4647;color:#fff;margin-left:6px}
.badge.blue{background:#257de0}
details summary{cursor:pointer;color:#257de0;font-size:12px;margin-top:4px}
table.steps{border-collapse:collapse;font-size:12px;margin-top:6px;width:100%}
table.steps td,table.steps th{border-bottom:1px solid #eee;padding:2px 4px;text-align:left;
 font-family:ui-monospace,monospace;white-space:nowrap}
table.steps tr:last-child td{font-weight:700;background:#eef5fd}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}
.tab{padding:8px 14px;border-radius:99px;background:#eef1f5;color:#191919;text-decoration:none;font-weight:600}
.tab.on{background:#191919;color:#fff}
.formula{font-family:ui-monospace,monospace;background:#eef1f5;border-radius:6px;padding:2px 6px}
"""


def esc(s):
    return html.escape(str(s), quote=True)


def is_code(s):
    if not s:
        return False
    for c in s:
        if c not in ALPHABET:
            return False
    return True


def horner_html(steps, m, title="호너 해시 계산"):
    rows = ["<tr><th>글자</th><th>코드</th><th>h = (31·h + 코드) mod %d</th></tr>" % m]
    for ch, code, prev, new in steps:
        shown = ch if ch.isprintable() and not ch.isspace() else "\\u%04x" % ord(ch)
        rows.append("<tr><td>%s</td><td>%d</td><td>(31·%d + %d) mod %d = %d</td></tr>"
                    % (esc(shown), code, prev, code, m, new))
    last = steps[-1][3] if steps else 0
    return ("<details><summary>%s → %d번 칸</summary><table class='steps'>%s</table></details>"
            % (esc(title), last, "".join(rows)))


class App:
    """단축기 두 개를 같은 순서로 채운다: 개별 체이닝과 선형 탐지.

    둘 다 같은 URL을 같은 순서로 받으므로 같은 코드를 낸다. 짧은 링크는 primary 쪽이 처리하고,
    /table에서는 두 테이블을 나란히 볼 수 있다.
    """

    def __init__(self, capacity=11, primary="chaining"):
        if primary not in ("chaining", "linear"):
            raise ValueError("primary는 chaining 또는 linear")
        self.capacity = capacity
        self.primary = primary
        self.lock = threading.Lock()
        self.clear()

    def clear(self):
        cap = self.capacity
        # 체이닝은 적재율 2를 넘으면, 선형 탐지는 0.9를 넘으면 늘린다
        # (선형 탐지도 수업 예시 9개를 같은 11칸에서 볼 수 있게 0.9로 둔다)
        self.chaining = Shortener(table_factory=lambda: HashTable(capacity=cap, max_load=2.0))
        self.linear = Shortener(
            table_factory=lambda: LinearProbingHashTable(capacity=cap, max_load=0.9))

    @property
    def shortener(self):
        return self.chaining if self.primary == "chaining" else self.linear

    def shorten(self, url):
        code = self.shortener.shorten(url)
        other = self.linear if self.primary == "chaining" else self.chaining
        other.shorten(url)
        return code

    def expand(self, code):
        return self.shortener.expand(code)


class Handler(BaseHTTPRequestHandler):
    app = None  # make_server가 채운다
    quiet = False
    server_version = "hw2-shortener/1.0"

    # ---- 공통 ----------------------------------------------------------

    def base_url(self):
        """짧은 링크의 앞부분. 프록시(Codespaces) 뒤면 X-Forwarded-Host를 쓴다."""
        fwd_host = (self.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
        fwd_proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        host = fwd_host or (self.headers.get("Host") or "").strip()
        if not host or not _safe_host(host):
            host = "localhost:%d" % self.server.server_address[1]
        proto = fwd_proto if fwd_proto in ("http", "https") else "http"
        return "%s://%s" % (proto, host)

    def send_html(self, status, title, body):
        page = ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>%s</title><style>%s</style></head><body><main>"
                "<nav><a class='brand' href='/'>✂ URL 단축기</a>"
                "<a href='/'>줄이기</a><a href='/table'>해시 테이블</a></nav>%s</main></body></html>"
                % (esc(title), CSS, body))
        data = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location, status=303):
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def read_form(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        length = max(0, min(length, MAX_BODY))
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        return parse_qsl(raw, keep_blank_values=True)

    def log_message(self, fmt, *args):
        if self.quiet:
            return
        sys.stderr.write("[server] %s\n" % (fmt % args))

    # ---- 라우팅 --------------------------------------------------------

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        query = parse_qsl(parts.query, keep_blank_values=True)
        if path == "/":
            return self.page_home()
        if path == "/table":
            return self.page_table(query)
        code = path[1:]
        if is_code(code):
            with self.app.lock:
                try:
                    url = self.app.expand(code)
                except KeyError:
                    url = None
            if url is not None:
                # Location 헤더는 ASCII만 된다. 한글 등은 퍼센트 인코딩한다
                return self.redirect(quote(url, safe=URL_SAFE), status=302)
        return self.page_not_found(code)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/shorten":
            return self.page_shorten(self.read_form())
        if path == "/demo":
            self.read_form()
            with self.app.lock:
                for u in DEMO_URLS:
                    try:
                        self.app.shorten(u)
                    except InvalidURLError:
                        pass
            return self.redirect("/table")
        if path == "/reset":
            self.read_form()
            with self.app.lock:
                self.app.clear()
            return self.redirect("/table")
        return self.page_not_found(path[1:])

    # ---- 화면 ----------------------------------------------------------

    def form_html(self, value=""):
        return ("<div class='card'><form method='post' action='/shorten'>"
                "<label for='url'><b>줄일 URL</b></label>"
                "<input type='text' id='url' name='url' value='%s' placeholder='https://...' "
                "autocomplete='off' autofocus><div class='row'><button type='submit'>줄이기</button>"
                "</div></form></div>" % esc(value))

    def page_home(self):
        with self.app.lock:
            n = len(self.app.shortener)
            m = self.app.chaining.table.capacity
        body = ("<h1>긴 URL을 짧게</h1>" + self.form_html() +
                "<div class='card'><div class='muted'>저장은 직접 만든 해시 테이블"
                "(개별 체이닝과 선형 탐지, 호너 해시)로 합니다. 지금 URL %d개, 체이닝 칸 %d개.</div>"
                "<div class='row'><form class='inline' method='post' action='/demo'>"
                "<button class='ghost'>수업 예시 URL 10개 넣기</button></form>"
                "<a href='/table'><button class='ghost' type='button'>해시 테이블 보기</button></a>"
                "</div></div>" % (n, m))
        self.send_html(200, "URL 단축기", body)

    def page_shorten(self, form):
        url = ""
        for k, v in form:
            if k == "url":
                url = v
        with self.app.lock:
            try:
                code = self.app.shorten(url)
                normalized = self.app.shortener.expand(code)
                table = self.app.chaining.table
                idx = table.index_of(normalized)
                steps = table.horner_steps(normalized)
                m = table.capacity
                chain_len = len(table.buckets()[idx])
                lp = self.app.linear.table
                lp_home, lp_slot = lp.index_of(normalized), lp.slot_of(normalized)
                err = None
            except InvalidURLError as e:
                err = str(e)
        if err is not None:
            body = ("<h1>줄일 수 없는 URL</h1><div class='card error'>%s</div>%s"
                    % (esc(err), self.form_html(url)))
            return self.send_html(400, "잘못된 URL", body)
        short = "%s/%s" % (self.base_url(), code)
        note = ""
        if chain_len > 1:
            note = ("<span class='badge'>충돌</span> 이 칸에는 URL %d개가 연결 리스트로 이어져 있습니다."
                    % chain_len)
        body = ("<h1>짧은 링크</h1><div class='card'>"
                "<div class='short'><a href='%s'>%s</a></div>"
                "<div class='row'><button type='button' class='ghost' "
                "onclick=\"navigator.clipboard&&navigator.clipboard.writeText('%s')\">복사</button></div>"
                "<p class='muted url'>원래 주소: %s</p>"
                "<p>코드 <b class='mono'>%s</b> · URL→코드 테이블의 <b>%d번 칸</b> (M = %d) %s</p>%s"
                "<p class='muted'>선형 탐지 테이블(M = %d)에서는 자기 칸 %d번, 실제로 들어간 칸 %d번</p>"
                "<p><a href='/table?hl=%s#b%d'>해시 테이블에서 보기 →</a> · "
                "<a href='/table?impl=linear&hl=%s#b%d'>선형 탐지로 보기 →</a></p></div>%s"
                % (esc(short), esc(short), esc(short), esc(normalized), esc(code), idx, m, note,
                   horner_html(steps, m), lp.capacity, lp_home, lp_slot, quote(code), idx,
                   quote(code), lp_slot, self.form_html()))
        self.send_html(200, "짧은 링크", body)

    def page_not_found(self, code):
        body = ("<h1>없는 짧은 링크</h1><div class='card error'>코드 <b class='mono'>%s</b>는 "
                "등록되어 있지 않습니다.</div>%s" % (esc(code[:80]), self.form_html()))
        self.send_html(404, "없는 링크", body)

    def page_table(self, query):
        hl, find, impl = "", None, "chaining"
        for k, v in query:
            if k == "hl":
                hl = v
            elif k == "find":
                find = v
            elif k == "impl" and v in ("chaining", "linear"):
                impl = v
        base = self.base_url()
        with self.app.lock:
            tabs = impl_tabs(impl, hl, find, self.app.primary)
            if impl == "linear":
                body = tabs + render_linear(self.app.linear.table, base, hl, find)
            else:
                body = tabs + render_chaining(self.app.chaining.table, base, hl, find)
        self.send_html(200, "해시 테이블", body)


def impl_tabs(impl, hl, find, primary):
    out = ["<div class='tabs'>"]
    for key, label in (("chaining", "개별 체이닝"), ("linear", "선형 탐지")):
        q = "impl=" + key
        if hl:
            q += "&hl=" + quote(hl)
        if find:
            q += "&find=" + quote(find)
        mark = " (짧은 링크 처리)" if key == primary else ""
        cls = "tab on" if key == impl else "tab"
        out.append("<a class='%s' href='/table?%s'>%s%s</a>" % (cls, esc(q), label, mark))
    out.append("</div>")
    return "".join(out)


def _safe_host(host):
    if len(host) > 255:
        return False
    for c in host:
        if not (c.isascii() and (c.isalnum() or c in ".-:[]")):
            return False
    return True


def find_form(find, label, impl="chaining"):
    return ("<div class='card'><form method='get' action='/table'>"
            "<input type='hidden' name='impl' value='%s'>" % esc(impl) +
            "<label for='find'><b>%s</b></label>"
            "<input type='text' id='find' name='find' value='%s' placeholder='https://...'>"
            "<div class='row'><button type='submit'>찾아보기</button></div></form></div>"
            % (esc(label), esc(find or "")))


def controls_html():
    return ("<div class='row'><form class='inline' method='post' action='/demo'>"
            "<button class='ghost'>수업 예시 URL 10개 넣기</button></form>"
            "<form class='inline' method='post' action='/reset'>"
            "<button class='ghost'>비우기</button></form></div>")


def render_chaining(table, base, hl="", find=None):
    m = table.capacity
    n = len(table)
    buckets = table.buckets()
    collide = 0
    for chain in buckets:
        if len(chain) > 1:
            collide += 1
    out = ["<h1>URL→코드 해시 테이블 · 개별 체이닝</h1>",
           "<div class='stats'>"
           "<div class='stat'><span class='muted'>칸 수 M</span><b>%d</b></div>"
           "<div class='stat'><span class='muted'>URL 수 n</span><b>%d</b></div>"
           "<div class='stat'><span class='muted'>적재율 α</span><b>%.2f</b></div>"
           "<div class='stat'><span class='muted'>충돌한 칸</span><b>%d</b></div></div>"
           % (m, n, n / m, collide),
           "<p class='muted'>칸 번호 = 호너 해시 <span class='formula'>h ← (31·h + 글자 코드) mod %d</span>. "
           "같은 칸에 떨어진 URL은 연결 리스트로 이어집니다. 노드의 '호너 해시 계산'을 펼치면 "
           "그 칸이 나온 근거가 보입니다.</p>" % m,
           controls_html()]
    find_idx, find_path = -1, 0
    if find:
        try:
            key = normalize_url(find)
        except InvalidURLError as e:
            key = None
            out.append("<div class='card error'>%s</div>" % esc(e))
        if key is not None:
            find_idx = table.index_of(key)
            cost = table.probes(key)
            hit = key in table
            find_path = cost
            out.append("<div class='card'><b>%s</b> 탐색: %d번 칸으로 가서 노드 <b>%d개</b>를 비교했고 %s. %s</div>"
                       % (esc(key), find_idx, cost, "찾았습니다" if hit else "없습니다",
                          horner_html(table.horner_steps(key), m)))
    out.append(find_form(find, "URL로 찾아보기 (비교한 노드를 표시)", "chaining"))
    for i, chain in enumerate(buckets):
        cls = "bucket collide" if len(chain) > 1 else "bucket"
        row = ["<div class='%s' id='b%d'><div class='idx'>%d<small>칸</small></div>" % (cls, i, i)]
        for pos, (url, code) in enumerate(chain):
            ncls = "node"
            if code == hl:
                ncls += " hl"
            if i == find_idx and pos < find_path:
                ncls += " cmp"
            row.append("<span class='arrow'>→</span>")
            row.append("<div class='%s'><div class='c mono'>%s</div><div class='k'>%s</div>"
                       "<div class='muted'><a href='%s/%s'>%s/%s</a></div>%s</div>"
                       % (ncls, esc(code), esc(url), esc(base), esc(code), esc(base), esc(code),
                          horner_html(table.horner_steps(url), m)))
        row.append("<span class='arrow'>→</span><span class='null'>NULL</span>")
        if len(chain) > 1:
            row.append("<span class='badge'>충돌 %d개</span>" % len(chain))
        row.append("</div>")
        out.append("".join(row))
    return "".join(out)


def render_linear(table, base, hl="", find=None):
    m = table.capacity
    n = len(table)
    slots = table.slots()
    moved = 0
    for i, cell in enumerate(slots):
        if cell is not None and table.index_of(cell[0]) != i:
            moved += 1
    out = ["<h1>URL→코드 해시 테이블 · 선형 탐지</h1>",
           "<div class='stats'>"
           "<div class='stat'><span class='muted'>칸 수 M</span><b>%d</b></div>"
           "<div class='stat'><span class='muted'>URL 수 n</span><b>%d</b></div>"
           "<div class='stat'><span class='muted'>적재율 α</span><b>%.2f</b></div>"
           "<div class='stat'><span class='muted'>밀려난 키</span><b>%d</b></div></div>"
           % (m, n, n / m, moved),
           "<p class='muted'>자기 칸 = 호너 해시 <span class='formula'>h ← (31·h + 글자 코드) mod %d</span>. "
           "자기 칸이 차 있으면 다음 칸(h+1, 끝 칸 다음은 0번)을 봅니다. "
           "주황색 칸은 충돌 때문에 자기 칸이 아닌 곳에 들어간 키입니다.</p>" % m,
           controls_html()]
    path = []
    if find:
        try:
            key = normalize_url(find)
        except InvalidURLError as e:
            key = None
            out.append("<div class='card error'>%s</div>" % esc(e))
        if key is not None:
            path = table.probe_path(key)
            hit = key in table
            out.append("<div class='card'><b>%s</b> 탐색: 자기 칸 %d번에서 시작해 <b>%d칸</b>을 들여다봤고 %s "
                       "(<span class='mono'>%s</span>). %s</div>"
                       % (esc(key), table.index_of(key), len(path),
                          "찾았습니다" if hit else "빈 칸을 만나 없다고 판단했습니다",
                          " → ".join(str(p) for p in path),
                          horner_html(table.horner_steps(key), m)))
    out.append(find_form(find, "URL로 찾아보기 (들여다본 칸을 표시)", "linear"))
    for i, cell in enumerate(slots):
        order = 0
        for step, p in enumerate(path):
            if p == i:
                order = step + 1
        if cell is None:
            cls = "bucket"
            node = "<span class='null'>빈 칸</span>"
        else:
            url, code = cell
            home = table.index_of(url)
            probe = table.probe_path(url)
            cls = "bucket collide" if home != i else "bucket"
            ncls = "node"
            if code == hl:
                ncls += " hl"
            info = ("자기 칸 %d번 · 들여다본 칸 %d개 (<span class='mono'>%s</span>)"
                    % (home, len(probe), " → ".join(str(p) for p in probe)))
            badge = "<span class='badge'>%d칸 밀림</span>" % ((i - home) % m) if home != i else ""
            node = ("<div class='%s'><div class='c mono'>%s %s</div><div class='k'>%s</div>"
                    "<div class='muted'><a href='%s/%s'>%s/%s</a></div><div class='muted'>%s</div>%s</div>"
                    % (ncls, esc(code), badge, esc(url), esc(base), esc(code), esc(base), esc(code),
                       info, horner_html(table.horner_steps(url), m)))
        if order:
            node += "<span class='badge blue'>%d번째로 봄</span>" % order
        out.append("<div class='%s' id='b%d'><div class='idx'>%d<small>칸</small></div>"
                   "<span class='arrow'>→</span>%s</div>" % (cls, i, i, node))
    return "".join(out)


def make_server(host="0.0.0.0", port=8000, capacity=11, quiet=False, primary="chaining"):
    class BoundHandler(Handler):
        pass

    BoundHandler.app = App(capacity=capacity, primary=primary)
    BoundHandler.quiet = quiet
    return ThreadingHTTPServer((host, port), BoundHandler)


def main(argv=None):
    p = argparse.ArgumentParser(description="URL 단축 웹 서비스")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--capacity", type=int, default=11, help="해시 테이블의 처음 칸 수")
    p.add_argument("--table", choices=("chaining", "linear"), default="chaining",
                   help="짧은 링크를 처리할 해시 테이블")
    args = p.parse_args(argv)
    httpd = make_server(args.host, args.port, args.capacity, primary=args.table)
    print("http://localhost:%d 에서 실행 중 · 테이블: %s (Ctrl+C로 종료)" % (args.port, args.table))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

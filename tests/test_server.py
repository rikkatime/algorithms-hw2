"""SPEC.md 6절 W1~W6: 웹 서버. 포트 0(빈 포트)으로 띄워서 실제 HTTP로 확인한다."""
import http.client
import os
import sys
import threading
import unittest
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import make_server  # noqa: E402


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.httpd = make_server("127.0.0.1", 0, quiet=True)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": "localhost:%d" % self.port}
        if body is not None:
            h["Content-Type"] = "application/x-www-form-urlencoded"
        h.update(headers or {})
        conn.request(method, path, body=body, headers=h)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        return resp, data

    def shorten(self, url, headers=None):
        return self.request("POST", "/shorten", urlencode({"url": url}), headers)

    # W1
    def test_home_has_form(self):
        resp, data = self.request("GET", "/")
        self.assertEqual(resp.status, 200)
        self.assertIn("<form", data)
        self.assertIn('name=\'url\'', data)

    def test_shorten_shows_short_link(self):
        resp, data = self.shorten("https://www.yonsei.ac.kr")
        self.assertEqual(resp.status, 200)
        self.assertIn("http://localhost:%d/1" % self.port, data)

    # W2
    def test_invalid_url_is_400(self):
        resp, data = self.shorten("ftp://files.example.com")
        self.assertEqual(resp.status, 400)
        self.assertIn("<form", data)

    def test_unknown_code_is_404(self):
        resp, _ = self.request("GET", "/zz9")
        self.assertEqual(resp.status, 404)
        resp, _ = self.request("GET", "/favicon.ico")
        self.assertEqual(resp.status, 404)

    # W3
    def test_short_link_redirects(self):
        self.shorten("https://github.com")
        resp, _ = self.request("GET", "/1")
        self.assertEqual(resp.status, 302)
        self.assertEqual(resp.getheader("Location"), "https://github.com")

    def test_korean_url_redirect_is_percent_encoded(self):
        self.shorten("https://ko.wikipedia.org/wiki/해시_테이블")
        resp, _ = self.request("GET", "/1")
        self.assertEqual(resp.status, 302)
        self.assertEqual(resp.getheader("Location"),
                         "https://ko.wikipedia.org/wiki/%ED%95%B4%EC%8B%9C_%ED%85%8C%EC%9D%B4%EB%B8%94")

    # W4
    def test_forwarded_host_used_for_short_link(self):
        resp, data = self.shorten("https://github.com", headers={
            "X-Forwarded-Host": "fluffy-space-xyz-8000.app.github.dev",
            "X-Forwarded-Proto": "https"})
        self.assertIn("https://fluffy-space-xyz-8000.app.github.dev/1", data)
        self.assertNotIn("localhost:%d/1" % self.port, data)

    # W5
    def test_table_shows_buckets_horner_and_collisions(self):
        self.request("POST", "/demo", "")
        resp, data = self.request("GET", "/table")
        self.assertEqual(resp.status, 200)
        self.assertIn("NULL", data)
        self.assertIn("mod 11", data)
        self.assertIn("충돌", data)
        self.assertIn("https://www.python.org", data)
        self.assertNotIn("ftp://files.example.com", data)

    def test_table_find_reports_compared_nodes(self):
        self.request("POST", "/demo", "")
        resp, data = self.request("GET", "/table?" + urlencode({"find": "https://github.com"}))
        self.assertEqual(resp.status, 200)
        self.assertIn("찾았습니다", data)

    def test_table_linear_probing_view(self):
        self.request("POST", "/demo", "")
        resp, data = self.request("GET", "/table?impl=linear")
        self.assertEqual(resp.status, 200)
        self.assertIn("선형 탐지", data)
        self.assertIn("자기 칸", data)
        self.assertIn("mod 11", data)
        resp, data = self.request("GET", "/table?" + urlencode(
            {"impl": "linear", "find": "https://www.python.org"}))
        self.assertIn("들여다봤고", data)

    # W6
    def test_html_is_escaped(self):
        resp, data = self.shorten("https://example.com/<script>alert(1)</script>")
        self.assertEqual(resp.status, 200)
        self.assertNotIn("<script>alert(1)</script>", data)
        self.assertIn("&lt;script&gt;", data)


class LinearPrimaryServerTest(unittest.TestCase):
    def test_short_links_served_by_linear_probing(self):
        httpd = make_server("127.0.0.1", 0, quiet=True, primary="linear")
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("POST", "/shorten", body=urlencode({"url": "https://github.com"}),
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            conn.getresponse().read()
            conn.request("GET", "/1")
            resp = conn.getresponse()
            resp.read()
            self.assertEqual(resp.status, 302)
            self.assertEqual(resp.getheader("Location"), "https://github.com")
            self.assertEqual(type(httpd.RequestHandlerClass.app.shortener.table).__name__,
                             "LinearProbingHashTable")
            conn.close()
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()

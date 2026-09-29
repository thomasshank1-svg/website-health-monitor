import sqlite3
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import domain


class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            return
        body = b'<a href="/ok">OK</a><a href="/missing">Missing</a>'
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class MonitorDomainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        domain.init(self.db)

    def test_scan_reports_missing_header_and_broken_link(self):
        report = domain.scan({"id": "fixture", "name": "Fixture", "url": f"http://127.0.0.1:{self.server.server_port}/"})
        self.assertEqual(report["status"], "Needs attention")
        self.assertIn("content-security-policy", report["missing_headers"])
        self.assertTrue(any(link["status_code"] == 404 for link in report["links"]))

    def test_api_rejects_unknown_target(self):
        with self.assertRaises(ValueError):
            domain.handle("POST", "/api/check", {"target_id": "outside"}, self.db)


if __name__ == "__main__":
    unittest.main()

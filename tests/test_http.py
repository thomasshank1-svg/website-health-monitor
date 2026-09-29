import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import server

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        server.DB_PATH = str(Path(cls.temp.name) / 'test.db')
        server.initialize()
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.temp.cleanup()

    def test_page_and_headers(self):
        with urlopen(self.url) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b'<main', response.read())
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')

    def test_private_files_not_served(self):
        for path in ['/server.py', '/data/app.db', '/../server.py']:
            with self.assertRaises(HTTPError) as caught:
                urlopen(self.url + path)
            self.assertEqual(caught.exception.code, 404)

    def test_cross_origin_write_rejected(self):
        request = Request(self.url+'/api/nope', data=b'{}', headers={
            'Content-Type':'application/json', 'Origin':'https://untrusted.example'})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 403)

    def test_invalid_json_rejected(self):
        request = Request(self.url+'/api/nope', data=b'bad', headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 400)

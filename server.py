"""Local demo HTTP server. Standard library only; not a production server."""
import json
import mimetypes
import os
import sqlite3
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import domain

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "data" / "app.db"))

def connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def initialize():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        domain.init(db)

class Handler(BaseHTTPRequestHandler):
    def send(self, status, payload, content_type="application/json; charset=utf-8"):
        body = json.dumps(payload).encode() if content_type.startswith("application/json") else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; img-src 'self' data:; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        # Bind to loopback and reject rebinding/cross-origin writes.
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            return self.send(403, {"error": "Use the localhost address printed by the server."})
        path = urlsplit(self.path).path
        try:
            if path.startswith("/api/"):
                data = {}
                if self.command != "GET":
                    origin = self.headers.get("Origin")
                    if origin and origin not in {"http://" + h for h in allowed}:
                        return self.send(403, {"error": "Cross-origin requests are not allowed."})
                    if self.headers.get_content_type() != "application/json":
                        return self.send(415, {"error": "Send application/json."})
                    size = int(self.headers.get("Content-Length", "0"))
                    if size < 0 or size > 65536:
                        return self.send(413, {"error": "Request must be smaller than 64 KB."})
                    data = json.loads(self.rfile.read(size) or b"{}")
                    if not isinstance(data, dict):
                        raise ValueError("Expected a JSON object.")
                db = connect()
                try:
                    with db:
                        payload = domain.handle(self.command, path, data, db)
                finally:
                    db.close()
                return self.send(200, payload)
            if self.command != "GET":
                return self.send(404, {"error": "Not found."})
            public = (ROOT / "public").resolve()
            file = (public / (path.lstrip("/") or "index.html")).resolve()
            if not file.is_relative_to(public) or not file.is_file():
                return self.send(404, {"error": "Not found."})
            return self.send(200, file.read_bytes(), mimetypes.guess_type(file)[0] or "application/octet-stream")
        except (ValueError, TypeError, KeyError) as error:
            self.send(400, {"error": str(error) or "Invalid request."})
        except sqlite3.IntegrityError:
            self.send(409, {"error": "This record already exists or the slot is no longer available."})
        except LookupError:
            self.send(404, {"error": "Record or endpoint not found."})
        except Exception:
            self.log_error("Request failed; details omitted to avoid exposing private data.")
            self.send(500, {"error": "Something went wrong. Please try again."})

    do_GET = dispatch
    do_POST = dispatch
    do_PATCH = dispatch
    do_DELETE = dispatch

if __name__ == "__main__":
    initialize()
    port = int(os.environ.get("PORT", "8105"))
    print(f"Signal running at http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

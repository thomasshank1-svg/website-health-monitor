"""Bounded website health checks for known demo targets."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import json
import socket
import ssl
import time

TARGETS = [
    {"id": "support", "name": "SourceDesk", "url": "http://127.0.0.1:8101/"},
    {"id": "booking", "name": "Slotly", "url": "http://127.0.0.1:8102/"},
    {"id": "store", "name": "Form & Function", "url": "http://127.0.0.1:8103/"},
    {"id": "crm", "name": "Pipeline", "url": "http://127.0.0.1:8104/"},
]

SECURITY_HEADERS = ["content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy"]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        values = dict(attrs)
        href = values.get("href")
        if href:
            self.links.append(href)


def init(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS checks(
            id INTEGER PRIMARY KEY,
            target_id TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            report_json TEXT NOT NULL
        )"""
    )


def allowed_target(target_id):
    for target in TARGETS:
        if target["id"] == target_id:
            return target
    raise ValueError("Choose a configured local target.")


def fetch(url, timeout=4):
    start = time.perf_counter()
    try:
        request = Request(url, headers={"User-Agent": "SignalLocalDemo/1.0"})
        with urlopen(request, timeout=timeout) as response:
            body = response.read(131072)
            duration = int((time.perf_counter() - start) * 1000)
            return {
                "ok": 200 <= response.status < 400,
                "status_code": response.status,
                "duration_ms": duration,
                "headers": {key.lower(): value for key, value in response.headers.items()},
                "body": body.decode("utf-8", "replace"),
                "error": None,
            }
    except HTTPError as error:
        duration = int((time.perf_counter() - start) * 1000)
        return {"ok": False, "status_code": error.code, "duration_ms": duration, "headers": {}, "body": "", "error": str(error)}
    except (URLError, TimeoutError, socket.timeout) as error:
        duration = int((time.perf_counter() - start) * 1000)
        return {"ok": False, "status_code": 0, "duration_ms": duration, "headers": {}, "body": "", "error": str(error)}


def tls_days_remaining(url):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return None
    port = parsed.port or 443
    context = ssl.create_default_context()
    with socket.create_connection((parsed.hostname, port), timeout=4) as sock:
        with context.wrap_socket(sock, server_hostname=parsed.hostname) as wrapped:
            cert = wrapped.getpeercert()
    expires = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return (expires - datetime.now(timezone.utc)).days


def same_origin_links(url, body):
    parsed = urlparse(url)
    parser = LinkParser()
    parser.feed(body)
    links = []
    for href in parser.links:
        absolute = urljoin(url, href)
        next_parsed = urlparse(absolute)
        if next_parsed.scheme in {"http", "https"} and next_parsed.netloc == parsed.netloc:
            links.append(absolute.split("#", 1)[0])
    return sorted(set(links))[:12]


def scan(target):
    response = fetch(target["url"])
    missing = [header for header in SECURITY_HEADERS if header not in response["headers"]]
    links = []
    if response["body"]:
        for link in same_origin_links(target["url"], response["body"]):
            link_response = fetch(link, timeout=3)
            links.append({"url": link, "status_code": link_response["status_code"], "ok": link_response["ok"]})
    try:
        tls_days = tls_days_remaining(target["url"])
    except Exception:
        tls_days = None
    problems = []
    if not response["ok"]:
        problems.append("main request failed")
    if missing:
        problems.append("missing security headers")
    if any(not link["ok"] for link in links):
        problems.append("broken internal link")
    if tls_days is not None and tls_days < 14:
        problems.append("TLS certificate expiring soon")
    return {
        "target": target,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "Pass" if not problems else "Needs attention",
        "duration_ms": response["duration_ms"],
        "status_code": response["status_code"],
        "error": response["error"],
        "missing_headers": missing,
        "tls_days_remaining": tls_days,
        "links": links,
        "problems": problems,
    }


def history(db):
    return [
        {**dict(row), "report": json.loads(row["report_json"])}
        for row in db.execute("SELECT * FROM checks ORDER BY id DESC LIMIT 20")
    ]


def handle(method, path, data, db):
    if method == "GET" and path == "/api/state":
        return {"targets": TARGETS, "history": history(db)}

    if method == "POST" and path == "/api/check":
        target = allowed_target(str(data.get("target_id", "")))
        report = scan(target)
        row = db.execute(
            "INSERT INTO checks(target_id,checked_at,status,duration_ms,report_json) VALUES(?,?,?,?,?)",
            (target["id"], report["checked_at"], report["status"], report["duration_ms"], json.dumps(report)),
        )
        return {"id": row.lastrowid, "report": report, "history": history(db)}

    raise LookupError()

# Signal

Signal is a bounded website health monitor for QA, IT, and security-awareness demos. It checks configured local targets for HTTP status, response time, common security headers, TLS expiry for HTTPS URLs, and same-origin links.

## Run

```sh
python3 server.py
```

Open `http://127.0.0.1:8105`.

## One-off CLI check

Use this only for sites you own or are allowed to test:

```sh
python3 monitor.py https://example.com --name Example
```

## What it demonstrates

- Health check reporting
- Bounded link checking
- Security-header awareness
- JSON report persistence in SQLite
- Local QA automation tests

## Test

```sh
python3 -m unittest discover -s tests -v
```

Signal is not a penetration test, vulnerability scanner, or compliance assessment.

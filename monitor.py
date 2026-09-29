#!/usr/bin/env python3
"""Run a one-off health check for an explicit URL you own or are allowed to test."""
import argparse
import json

import domain


def main():
    parser = argparse.ArgumentParser(description="Run a bounded website health check.")
    parser.add_argument("url", help="Explicit URL to check")
    parser.add_argument("--name", default="Manual target")
    args = parser.parse_args()
    print(json.dumps(domain.scan({"id": "manual", "name": args.name, "url": args.url}), indent=2))


if __name__ == "__main__":
    main()

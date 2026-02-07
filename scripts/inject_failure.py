#!/usr/bin/env python3
"""Failure injection CLI for edge node simulator.

Usage:
    python scripts/inject_failure.py --node 3 --failure cpu_spike --duration 30
    python scripts/inject_failure.py --node 7 --failure memory_leak --duration 60
    python scripts/inject_failure.py --node all --failure latency_spike --duration 20
"""

import argparse
import sys
import urllib.error
import urllib.request
import json

VALID_FAILURES = ["cpu_spike", "memory_leak", "latency_spike", "error_burst", "node_crash"]
BASE_PORT = 8000


def inject(node_id: int, failure: str, duration: int) -> dict:
    port = BASE_PORT + node_id
    url = f"http://localhost:{port}/inject?mode={failure}&duration={duration}"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"error": str(e), "node_id": node_id}


def main():
    parser = argparse.ArgumentParser(description="Inject failures into edge nodes")
    parser.add_argument(
        "--node",
        required=True,
        help="Node ID (1-12) or 'all'",
    )
    parser.add_argument(
        "--failure",
        required=True,
        choices=VALID_FAILURES,
        help="Failure mode to inject",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds (default: 30)",
    )
    args = parser.parse_args()

    if args.node == "all":
        nodes = list(range(1, 13))
    else:
        try:
            n = int(args.node)
            if not 1 <= n <= 12:
                print(f"Error: node must be 1-12, got {n}", file=sys.stderr)
                sys.exit(1)
            nodes = [n]
        except ValueError:
            print(f"Error: node must be 1-12 or 'all', got '{args.node}'", file=sys.stderr)
            sys.exit(1)

    for node_id in nodes:
        result = inject(node_id, args.failure, args.duration)
        if "error" in result:
            print(f"  [FAIL] Node {node_id}: {result['error']}")
        else:
            print(f"  [OK]   Node {node_id}: {args.failure} injected for {args.duration}s")


if __name__ == "__main__":
    main()

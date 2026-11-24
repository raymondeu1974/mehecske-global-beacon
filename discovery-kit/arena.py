"""Issue or recheck offline Agent Proof Arena receipts."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_benchmark import HERE, parse, reproduce

ROOT = HERE.parent
MAX_INPUT_BYTES = 1024
BUNDLE = (
    "discovery-kit/arena.py",
    "discovery-kit/verify_benchmark.py",
    "discovery-kit/fixtures/interval-schedule-v1.json",
    "discovery-kit/fixtures/exact-cover-v1.json",
    "autonomous/beacon_runner.py",
    "autonomous/feed.json",
    "mission-pilot/call.json",
    "mission-pilot/verify.py",
)
KINDS = ("local-reproduction", "maintainer-self-test")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def make_receipt(result, kind):
    checked = reproduce(result)
    bundle = {name: (ROOT / name).read_text(encoding="utf-8") for name in BUNDLE}
    receipt = {
        **checked,
        "format": "mehecske-arena-receipt-v1",
        "kind": kind,
        "bundle_sha256": hashlib.sha256(canonical(bundle)).hexdigest(),
    }
    return {**receipt, "receipt_sha256": hashlib.sha256(canonical(receipt)).hexdigest()}


def check_receipt(receipt):
    if type(receipt) is not dict or receipt.get("kind") not in KINDS:
        raise ValueError("Unknown receipt kind")
    expected = make_receipt(receipt.get("result"), receipt["kind"])
    if canonical(receipt) != canonical(expected):
        raise ValueError("Receipt differs from offline reproduction")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    issue = commands.add_parser("verify", help="Verify an answer and print a receipt")
    issue.add_argument("file", type=Path)
    issue.add_argument("--operator-approved", action="store_true", required=True)
    issue.add_argument("--self-test", action="store_true")
    check = commands.add_parser("check-receipt", help="Recompute and compare a receipt")
    check.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        with args.file.open("rb") as source:
            value = parse(source.read(MAX_INPUT_BYTES + 1), MAX_INPUT_BYTES)
        if args.command == "verify":
            receipt = make_receipt(value, "maintainer-self-test" if args.self_test else "local-reproduction")
        else:
            receipt = check_receipt(value)
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(1, f"Arena rejected input: {error}\n")
    print(canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

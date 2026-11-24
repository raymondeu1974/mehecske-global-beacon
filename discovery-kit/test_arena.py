"""Regression checks for the public Arena CLI and manifest."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
RESULTS = (
    {"task_id": "synthetic-shortest-path-v1", "distance": 4, "shortest_paths": 4},
    {"task_id": "interval-schedule-v1", "max_priority": 19, "optimal_subsets": 8},
    {"task_id": "exact-cover-v1", "exact_covers": 4, "minimum_placements": 2},
)


def run(command, value, *flags):
    path = ROOT / "discovery-kit" / f"arena-input-{uuid4().hex}.json"
    try:
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "discovery-kit/arena.py"), command, str(path), *flags],
            cwd=ROOT.parent, capture_output=True, text=True, timeout=10,
        )
    finally:
        path.unlink(missing_ok=True)


class ArenaTests(unittest.TestCase):
    def receipt(self, result=RESULTS[0], *flags):
        completed = run("verify", result, "--operator-approved", *flags)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    def test_manifest_resolves_to_existing_catalog(self):
        discovery = json.loads((ROOT / "agent-discovery.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / discovery["agent_proof_arena"]["manifest_path"]).read_text(encoding="utf-8"))
        catalog = json.loads((ROOT / manifest["catalog_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["task_ids"], [r["task_id"] for r in RESULTS])
        self.assertEqual({t["id"]: set(t["result_fields"]) for t in catalog["tasks"]},
                         {r["task_id"]: set(r) for r in RESULTS})
        for field in ("cli_path", "guide_path"):
            self.assertTrue((ROOT / manifest[field]).is_file())
        self.assertFalse(manifest["automatic_publication"])

    def test_all_tasks_round_trip(self):
        for result in RESULTS:
            with self.subTest(task=result["task_id"]):
                receipt = self.receipt(result)
                self.assertEqual(json.loads(receipt)["result"], result)
                self.assertEqual(json.loads(receipt)["kind"], "local-reproduction")
                checked = run("check-receipt", receipt)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertEqual(checked.stdout, receipt)

    def test_self_test_has_separate_receipt(self):
        local = json.loads(self.receipt())
        self_test = self.receipt(RESULTS[0], "--self-test")
        checked = run("check-receipt", self_test)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(self_test)["kind"], "maintainer-self-test")
        self.assertNotEqual(local["receipt_sha256"], json.loads(self_test)["receipt_sha256"])

    def test_requires_explicit_operator_approval(self):
        self.assertEqual(run("verify", RESULTS[0]).returncode, 2)

    def test_wrong_answer_for_each_task(self):
        for result in RESULTS:
            field = next(key for key in result if key != "task_id")
            self.assertEqual(run("verify", result | {field: 999}, "--operator-approved").returncode, 1)

    def test_invalid_input(self):
        for value in (
            RESULTS[0] | {"distance": True},
            RESULTS[0] | {"task_id": "../call"},
            RESULTS[0] | {"operator": "alice"},
            '{"task_id":"a","task_id":"b"}',
            " " * 1025,
        ):
            with self.subTest(value=value):
                self.assertEqual(run("verify", value, "--operator-approved").returncode, 1)

    def test_recheck_rejects_tampering_and_independence_claims(self):
        receipt = json.loads(self.receipt())
        for update in (
            {"receipt_sha256": "0" * 64},
            {"bundle_sha256": "0" * 64},
            {"kind": "verified-independent"},
            {"operator": "alice"},
            {"reproduced": 1},
            {"result": RESULTS[0] | {"distance": 5}},
        ):
            with self.subTest(update=update):
                self.assertEqual(run("check-receipt", receipt | update).returncode, 1)

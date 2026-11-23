"""Check catalog consistency and the offline verification entry points."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from xml.etree import ElementTree

from test_discovery import exchange, load, request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = {
    "synthetic-shortest-path-v1": {"distance": 4, "shortest_paths": 4},
    "interval-schedule-v1": {"max_priority": 19, "optimal_subsets": 8},
    "exact-cover-v1": {"exact_covers": 4, "minimum_placements": 2},
}


def run(payload):
    return subprocess.run([sys.executable, "-B", str(HERE / "verify_benchmark.py")],
                          input=payload, capture_output=True, timeout=10)


class BenchmarkTests(unittest.TestCase):
    def test_catalog_matches_manifest_release_and_verifier(self):
        manifest = load("../agent-discovery.json")
        catalog = load("catalog.json")
        atom = ElementTree.parse(ROOT / "docs" / "changes.atom")
        entry_id = atom.findtext("{*}entry/{*}id")
        self.assertEqual(manifest["discovery"]["release_id"], catalog["release_id"])
        self.assertEqual(entry_id.split("#")[-1], catalog["release_id"])
        self.assertIs(catalog["operator_authorization_required"], True)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual([task["id"] for task in catalog["tasks"]], list(RESULTS))
        for task in catalog["tasks"]:
            task_id = task["id"]
            with self.subTest(task=task_id):
                self.assertEqual(set(task["result_fields"]), RESULTS[task_id].keys() | {"task_id"})
                self.assertEqual(task["mode"], "public-mailbox" if task_id.startswith("synthetic-")
                                 else "offline-only")
                prefix = "https://raw.githubusercontent.com/raymondeu1974/mehecske-global-beacon/main/"
                self.assertTrue(task["fixture_url"].startswith(prefix))
                self.assertTrue((ROOT / task["fixture_url"][len(prefix):]).is_file())
                result = {"task_id": task_id, **RESULTS[task_id]}
                proc = run(json.dumps(result).encode())
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["result"], result)

    def test_invalid_untrusted_results(self):
        bad_results = (
            b'{"task_id":"../../private"}',
            b'{"task_id":"exact-cover-v1","exact_covers":4,"minimum_placements":true}',
            b'{"task_id":"exact-cover-v1","exact_covers":3,"minimum_placements":2}',
            b'{"task_id":"exact-cover-v1","exact_covers":4,"minimum_placements":2,"command":"run"}',
            b'{"task_id":"exact-cover-v1","exact_covers":4,"exact_covers":4,"minimum_placements":2}',
            b" " * 1025,
        )
        for payload in bad_results:
            with self.subTest(payload=payload[:100]):
                proc = run(payload)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout, b"")
                self.assertIn(b"Benchmark rejected", proc.stderr)

    def test_catalog_mcp_resource(self):
        uri = "beacon://discovery/catalog.json"
        listing, read = exchange(request(1, "resources/list"), request(2, "resources/read", uri=uri))
        self.assertIn(uri, [resource["uri"] for resource in listing["result"]["resources"]])
        content, = read["result"]["contents"]
        self.assertEqual(json.loads(content["text"]), load("catalog.json"))

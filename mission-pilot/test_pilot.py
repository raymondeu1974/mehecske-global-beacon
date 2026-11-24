import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import unittest

from verify import verify_route

ROOT = Path(__file__).resolve().parent
CALL = json.loads((ROOT / "call.json").read_text(encoding="utf-8-sig"))
GOOD = json.loads((ROOT / "reviewer-example.json").read_text(encoding="utf-8-sig"))


def invoke(result, consent=None):
    path = Path(__file__).with_name(f'result-{uuid4().hex}.json')
    try:
        path.write_text(result if isinstance(result, str) else json.dumps(result),
                        encoding="utf-8")
        command = [sys.executable, "-B", str(ROOT / "verify.py"), str(path)]
        if consent is not None:
            command.extend(["--consent", consent])
        return subprocess.run(command, capture_output=True, text=True)
    finally:
        path.unlink(missing_ok=True)

class PilotTest(unittest.TestCase):
    def test_three_arms_same_task_and_opt_in(self):
        self.assertEqual([v["id"] for v in CALL["variants"]], list("ABC"))
        self.assertEqual(len({v["opening"] for v in CALL["variants"]}), 3)
        self.assertEqual(invoke(GOOD).returncode, 2)
        self.assertEqual(invoke(GOOD, "NO").returncode, 2)

    def test_reproduce_by_enumerating_simple_paths(self):
        fixture = CALL["fixture"]
        paths = [(fixture["source"],)]
        completed = []
        while paths:
            path = paths.pop()
            if path[-1] == fixture["target"]:
                completed.append(len(path) - 1)
            else:
                paths.extend((*path, end) for start, end in fixture["edges"]
                             if start == path[-1] and end not in path)
        distance = min(completed)
        self.assertEqual((distance, completed.count(distance)), (4, 4))
        run = invoke(GOOD, CALL["required_consent"])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)["reproduced"])

    def test_wrong_and_invalid_results(self):
        for fields, code in [
            ({"distance": 3}, 1), ({"shortest_paths": 3}, 1),
            ({"distance": -1}, 2), ({"shortest_paths": 0}, 2),
            ({"distance": 4.25}, 2), ({"distance": 4.0}, 0),
            ({"distance": True}, 2), ({"task_id": "other"}, 2),
            ({"extra": "field"}, 2),
        ]:
            with self.subTest(fields=fields):
                self.assertEqual(invoke(GOOD | fields, CALL["required_consent"]).returncode, code)


class RouteTest(unittest.TestCase):
    def assert_route(self, path, distance, code):
        result = {"task_id": "synthetic-shortest-route-v1", "path": path, "distance": distance}
        run = invoke(result, "AUTHORIZE SYNTHETIC ROUTE V1")
        self.assertEqual(run.returncode, code, run.stderr)
        if code != 2:
            self.assertEqual(json.loads(run.stdout),
                             {"task_id": result["task_id"], "reproduced": code == 0})

    def test_all_equal_shortest_routes(self):
        for path in ("ABDGH", "ABEGH", "ACDGH", "ACFGH"):
            with self.subTest(path=path):
                self.assert_route(list(path), 4, 0)

    def test_second_fixture_with_two_shortest_routes_and_one_longer(self):
        fixture = {
            "source": "S", "target": "T",
            "edges": [("S", "A"), ("A", "T"), ("S", "B"), ("B", "T"),
                      ("S", "C"), ("C", "D"), ("D", "T")],
        }
        for path, expected in (("SAT", True), ("SBT", True), ("SCDT", False)):
            with self.subTest(path=path):
                result = {"path": list(path), "distance": len(path) - 1}
                self.assertEqual(verify_route(result, fixture), expected)

    def test_longer_route(self):
        self.assert_route(list("ACFABDGH"), 7, 1)

    def test_missing_directed_edge(self):
        self.assert_route(list("ABFGH"), 4, 1)

    def test_wrong_endpoints(self):
        self.assert_route(list("BDGH"), 3, 1)
        self.assert_route(list("ABDG"), 3, 1)

    def test_false_reported_distance(self):
        self.assert_route(list("ABDGH"), 5, 1)

    def test_malformed_json(self):
        run = invoke('{"task_id": "synthetic-shortest-route-v1",',
                          "AUTHORIZE SYNTHETIC ROUTE V1")
        self.assertEqual(run.returncode, 2)
        self.assertFalse(run.stdout)

    def test_invalid_path_shape_or_consent(self):
        self.assert_route([], 0, 2)
        self.assert_route(["A", ["B"], "H"], 2, 2)
        result = {"task_id": "synthetic-shortest-route-v1", "path": list("ABDGH"), "distance": 4}
        self.assertEqual(invoke(result, CALL["required_consent"]).returncode, 2)


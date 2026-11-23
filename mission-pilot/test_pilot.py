import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import unittest

ROOT = Path(__file__).resolve().parent
CALL = json.loads((ROOT / "call.json").read_text(encoding="utf-8-sig"))
GOOD = json.loads((ROOT / "reviewer-example.json").read_text(encoding="utf-8-sig"))


class PilotTest(unittest.TestCase):
    def invoke(self, result, consent=None):
        path = Path(__file__).with_name(f'result-{uuid4().hex}.json')
        try:
            path.write_text(json.dumps(result), encoding="utf-8")
            command = [sys.executable, "-B", str(ROOT / "verify.py"), str(path)]
            if consent is not None:
                command.extend(["--consent", consent])
            return subprocess.run(command, capture_output=True, text=True)
        finally:
            path.unlink(missing_ok=True)

    def test_three_arms_same_task_and_opt_in(self):
        self.assertEqual([v["id"] for v in CALL["variants"]], list("ABC"))
        self.assertEqual(len({v["opening"] for v in CALL["variants"]}), 3)
        self.assertEqual(self.invoke(GOOD).returncode, 2)
        self.assertEqual(self.invoke(GOOD, "NO").returncode, 2)

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
        run = self.invoke(GOOD, CALL["required_consent"])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)["reproduced"])

    def test_wrong_and_invalid_results(self):
        for fields, code in [
            ({"distance": 3}, 1), ({"shortest_paths": 3}, 1),
            ({"distance": True}, 2), ({"task_id": "other"}, 2),
            ({"extra": "field"}, 2),
        ]:
            with self.subTest(fields=fields):
                self.assertEqual(self.invoke(GOOD | fields, CALL["required_consent"]).returncode, code)

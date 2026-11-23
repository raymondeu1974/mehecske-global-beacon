import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from beacon_runner import HERE, ROOT, TASK, available, configuration, fixture, parse, poll_once, read_json, solve, verify


class AutonomousTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = Path(directory.name) / "opt-in.json"
        self.state = self.config.with_suffix(".attempt")
        self.feed = read_json(HERE / "feed.json")
        self.save_config()
        self.submit = Mock(return_value="local receipt")

    def save_config(self, **changes):
        config = read_json(HERE / "opt-in.example.json")
        config.update(enabled=True, submit=True)
        config.update(changes)
        self.config.write_text(json.dumps(config), encoding="utf-8")

    def test_disabled_or_unlisted_never_fetches(self):
        fetch = Mock()
        for changes in ({"enabled": False}, {"allowed_tasks": []}, {"poll_seconds": 899}):
            self.save_config(**changes)
            with self.assertRaises(ValueError):
                poll_once(self.config, self.state, fetch, self.submit)
        fetch.assert_not_called()
        self.submit.assert_not_called()

    def test_valid_result_and_rejections(self):
        result = solve(fixture())
        self.assertEqual(result, {"task_id": TASK, "distance": 4, "shortest_paths": 4})
        self.assertTrue(verify(result, self.feed)["reproduced"])
        for changes in ({"distance": 5}, {"task_id": "other"}, {"distance": True},
                        {"shortest_paths": 4.0}, {"extra": "field"}):
            with self.assertRaises(ValueError):
                verify({**result, **changes}, self.feed)
        with self.assertRaises(ValueError):
            parse(b'{"distance":4,"distance":0}', 1024)

    def test_withdrawal_before_submit_and_verification(self):
        withdrawn = {"schema_version": 1, "tasks": []}
        fetch = Mock(side_effect=[self.feed, withdrawn])
        self.assertEqual(
            poll_once(self.config, self.state, fetch, self.submit),
            "task unavailable before submission",
        )
        self.assertFalse(self.state.exists())
        self.submit.assert_not_called()
        with self.assertRaises(ValueError):
            verify(solve(fixture()), withdrawn)
        self.assertFalse(available({"schema_version": 1, "tasks": self.feed["tasks"] * 2}))

    def test_verified_dispatch_and_duplicate_suppression(self):
        self.submit.side_effect = lambda result: json.dumps(verify(result, self.feed))
        self.assertIn('"reproduced": true', poll_once(self.config, self.state, lambda: self.feed, self.submit))
        self.assertEqual(poll_once(self.config, self.state, lambda: self.feed, self.submit),
                         "submission already attempted")
        self.submit.assert_called_once()

    def test_ambiguous_dispatch_is_not_retried(self):
        self.submit.side_effect = TimeoutError
        with self.assertRaises(TimeoutError):
            poll_once(self.config, self.state, lambda: self.feed, self.submit)
        self.assertEqual(self.state.read_text().strip(), "pending")
        poll_once(self.config, self.state, lambda: self.feed, self.submit)
        self.submit.assert_called_once()

    def test_manifest_and_sample(self):
        manifest = read_json(ROOT / "agent-discovery.json")
        from beacon_runner import DISPATCH_URL, FEED_URL, MIN_POLL
        self.assertEqual(manifest["feed_url"], FEED_URL)
        self.assertEqual(manifest["submission"]["url"], DISPATCH_URL)
        self.assertEqual(manifest["minimum_poll_seconds"], MIN_POLL)
        self.assertIsNone(manifest["a2a"]["endpoint"])
        self.assertIsNone(manifest["mcp"]["endpoint"])
        with self.assertRaises(ValueError):
            configuration(HERE / "opt-in.example.json")

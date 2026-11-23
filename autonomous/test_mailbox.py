import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from beacon_runner import HERE, fixture, read_json, solve
from public_mailbox import API, REGISTRY_URL, RESULT_PATH, collect, enrollment, publish


class MailboxTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.receipts = Path(temporary.name)
        self.repo = "researcher/public-results"
        self.entry = {"repository": self.repo, "repository_id": 3, "owner_id": 5}
        self.registry = {"schema_version": 1, "mailboxes": [self.entry]}
        self.metadata = {"id": 3, "owner": {"id": 5}, "full_name": self.repo,
                         "visibility": "public", "private": False}
        self.feed = read_json(HERE / "feed.json")
        self.result = solve(fixture())
        self.repo_api = f"{API}/repos/{self.repo}"
        self.content_api = f"{self.repo_api}/contents/{RESULT_PATH}"
        self.published = None
        self.calls = []

    def api(self, url, *, payload=None, token=None, limit=16384):
        self.calls.append(url)
        if url == REGISTRY_URL:
            return self.registry
        if url == self.repo_api:
            return self.metadata
        self.assertEqual(url, self.content_api)
        if payload:
            self.assertEqual(token, "mailbox-only")
            self.assertNotIn("sha", payload)
            self.published = base64.b64decode(payload["content"])
            return {}
        self.assertIsNone(token)
        self.assertEqual(limit, 4096)
        if self.published is None:
            raise HTTPError(url, 404, "Not found", {}, None)
        raw = self.published
        return {"type": "file", "path": RESULT_PATH, "encoding": "base64",
                "size": len(raw), "content": base64.b64encode(raw).decode(),
                "sha": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()}

    def test_publish_collect_and_skip_repeat(self):
        with patch.dict("os.environ", {"BEACON_MAILBOX_TOKEN": "mailbox-only"}):
            url = publish(self.result, {"mailbox_repository": self.repo}, api=self.api)
        self.assertEqual(url, f"https://github.com/{self.repo}/blob/HEAD/{RESULT_PATH}")
        collect(self.registry, self.feed, self.receipts, api=self.api)
        receipt = read_json(self.receipts / "5.json")
        self.assertTrue(receipt["reproduced"])
        self.assertEqual(receipt["result"], self.result)
        self.assertEqual(receipt["source_sha256"], hashlib.sha256(self.published).hexdigest())
        self.calls.clear()
        collect(self.registry, self.feed, self.receipts, api=self.api)
        self.assertEqual(self.calls, [])

    def test_withdrawals_and_invalid_result(self):
        self.published = json.dumps({**self.result, "distance": 9}).encode()
        collect(self.registry, self.feed, self.receipts, api=self.api)
        self.assertEqual(list(self.receipts.iterdir()), [])
        self.calls.clear()
        collect({"schema_version": 1, "mailboxes": []}, self.feed, self.receipts, api=self.api)
        collect(self.registry, {**self.feed, "tasks": []}, self.receipts, api=self.api)
        self.assertEqual(self.calls, [])
        self.published = None
        collect(self.registry, self.feed, self.receipts, api=self.api)
        self.assertEqual(list(self.receipts.iterdir()), [])

    def test_changed_owner_and_unenrolled_publication_blocked(self):
        self.metadata["owner"]["id"] = 13
        collect(self.registry, self.feed, self.receipts, api=self.api)
        self.assertNotIn(self.content_api, self.calls)
        with self.assertRaisesRegex(ValueError, "not enrolled"):
            publish(self.result, {"mailbox_repository": "other/results"}, api=self.api)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            enrollment({**self.registry, "mailboxes": [self.entry, self.entry]})

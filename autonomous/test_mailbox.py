import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from beacon_runner import HERE, fixture, read_json, solve
from public_mailbox import (API, CONSENT_PATH, ISSUE_INDEX, ISSUES_URL, REGISTRY_URL,
                            RESULT_PATH, ReadBudgetExhausted, bounded_reads, collect,
                            enrollment, publish)
from beacon_runner import REPO, TASK


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
        return self.blob(RESULT_PATH, self.published)

    @staticmethod
    def blob(path, raw):
        return {"type": "file", "path": path, "encoding": "base64",
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

    def configure_issue(self):
        self.registry["mailboxes"] = []
        self.metadata["owner"]["type"] = "User"
        self.metadata["archived"] = False
        self.issue = {"number": 7, "title": f"Beacon mailbox: {self.repo}", "state": "open",
                      "user": {"id": 5, "login": "researcher", "type": "User"}}
        self.live_issue = self.issue
        self.proof = {"schema_version": 1, "beacon": REPO, "issue": 7,
                      "repository_id": 3, "task_id": TASK, "consent": True}
        self.published = json.dumps(self.result).encode()

    def issue_api(self, url, **kwargs):
        if url == ISSUE_INDEX:
            return [self.issue, self.issue]
        if url == f"{ISSUES_URL}/7":
            return self.live_issue
        if url == f"{self.repo_api}/contents/{CONSENT_PATH}":
            return self.blob(CONSENT_PATH, json.dumps(self.proof).encode())
        return self.api(url, **kwargs)

    def test_self_service_publish_collect_and_deduplicate(self):
        self.configure_issue()
        with patch.dict("os.environ", {"BEACON_MAILBOX_TOKEN": "mailbox-only"}):
            publish(self.result, {"mailbox_repository": self.repo, "mailbox_issue": 7},
                    api=self.issue_api)
        collect(self.registry, self.feed, self.receipts, api=self.issue_api, self_service=True)
        receipt = read_json(self.receipts / "5.json")
        self.assertTrue(receipt["reproduced"])
        self.assertEqual(receipt["registration_issue"], 7)
        self.calls.clear()
        collect(self.registry, self.feed, self.receipts, api=self.issue_api, self_service=True)
        self.assertEqual(self.calls, [])

    def test_self_service_rejects_spoofed_owner_and_unsafe_path(self):
        self.configure_issue()
        self.issue["title"] = "Beacon mailbox: researcher/.."
        collect(self.registry, self.feed, self.receipts, api=self.issue_api, self_service=True)
        self.assertEqual(self.calls, [])
        self.issue["title"] = f"Beacon mailbox: {self.repo}"
        self.issue["user"]["id"] = 6
        collect(self.registry, self.feed, self.receipts, api=self.issue_api, self_service=True)
        self.assertNotIn(self.content_api, self.calls)
        self.assertEqual(list(self.receipts.iterdir()), [])

    def test_self_service_requires_exact_consent_and_current_issue(self):
        self.configure_issue()
        self.proof["consent"] = 1
        collect(self.registry, self.feed, self.receipts, api=self.issue_api, self_service=True)
        self.assertNotIn(self.content_api, self.calls)
        self.proof["consent"] = True
        self.live_issue = {**self.issue, "state": "closed"}
        collect(self.registry, self.feed, self.receipts, api=self.issue_api, self_service=True)
        self.assertIn(self.content_api, self.calls)
        self.assertEqual(list(self.receipts.iterdir()), [])

    def test_read_budget_and_rate_limit(self):
        get = bounded_reads(lambda url: url)
        for _ in range(48):
            self.assertEqual(get(ISSUE_INDEX), ISSUE_INDEX)
        with self.assertRaises(ReadBudgetExhausted):
            get(ISSUE_INDEX)

        def limited(url):
            raise HTTPError(url, 429, "Rate limited", {}, None)

        with self.assertRaises(ReadBudgetExhausted):
            bounded_reads(limited)(ISSUE_INDEX)

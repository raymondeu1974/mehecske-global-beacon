from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.client import HTTPConnection
import json
from pathlib import Path
import sqlite3
from threading import Thread
import unittest
import uuid

from beacon import Beacon, CONSENT, new_secret, server_for


class BeaconTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(f"beacon-test-{uuid.uuid4().hex}.sqlite3")
        self.addCleanup(self.path.unlink, missing_ok=True)
        self.now = 1000
        self.admin = new_secret()
        self.beacon = Beacon(self.path, self.admin, lambda: self.now)
        self.server = server_for(self.beacon, 0)
        thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()

        def stop():
            self.server.shutdown()
            thread.join()
            self.server.server_close()

        self.addCleanup(stop)

    def send(self, route, body=None, token=None, status=200, extra=None, raw=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        headers.update(extra or {})
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            method = "GET" if route == "/feed" else "POST"
            conn.request(method, route, raw if raw is not None else json.dumps(body), headers)
            response = conn.getresponse()
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            result = json.loads(response.read())
            if status is None:
                return response.status
            self.assertEqual(response.status, status, result)
            return result
        finally:
            conn.close()

    def join(self):
        return self.send("/register", {"consent": CONSENT, "future_notices": True}, status=201)

    def publish(self, project="shapes", ttl=300, status=201):
        return self.send("/publish", {"project": project, "ttl_seconds": ttl}, self.admin, status)

    def feed(self, agent):
        return self.send("/feed", token=agent["token"])["items"]

    def verify(self, agent, item, status=200):
        return self.send("/verify-and-receive", {"invitation": item}, agent["token"], status)

    def test_explicit_consent_ids_and_registration_limit(self):
        for consent in (False, 1, "true", None):
            self.send("/register", {"consent": CONSENT, "future_notices": consent}, status=400)
        a = self.join()
        self.send("/register", {"consent": CONSENT, "future_notices": True}, status=429)
        self.now += 2
        b = self.join()
        self.assertNotEqual(a["agent_id"], b["agent_id"])
        self.assertNotEqual(a["token"], b["token"])

    def test_publication_feed_and_late_registration(self):
        a = self.join()
        self.assertEqual(self.feed(a), [])
        call = self.publish()
        self.now += 5
        b = self.join()
        invitation, = self.feed(a)
        self.assertEqual(invitation["call_id"], call["call_id"])
        self.assertEqual(invitation["agent_id"], a["agent_id"])
        self.assertEqual(self.feed(b), [])
        self.verify(b, invitation, 404)
        self.assertTrue(self.verify(a, invitation)["verified"])

    def test_forgery_and_cross_agent_copy(self):
        a = self.join()
        self.now += 2
        b = self.join()
        self.publish()
        item, = self.feed(a)
        self.verify(b, item, 422)
        self.verify(a, dict(item, summary="changed"), 422)
        self.verify(a, dict(item, expires_at=item["expires_at"] + 10), 422)
        self.verify(a, dict(item, call_id="unknown"), 404)
        self.verify(a, dict(item, version=True), 422)
        self.verify(a, item)

    def test_replay_concurrent_and_restart(self):
        a = self.join()
        self.publish()
        item, = self.feed(a)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.verify(a, item, None), range(2)))
        self.assertEqual(sorted(results), [200, 409])
        self.server.beacon = Beacon(self.path, self.admin, lambda: self.now)
        self.verify(a, item, 409)
        self.publish(status=409)

    def test_expiry_boundary_and_clock_rollback(self):
        a = self.join()
        self.publish(ttl=5)
        item, = self.feed(a)
        self.now += 5
        self.verify(a, item, 410)
        self.now -= 1
        self.verify(a, item, 503)
        self.now += 1
        self.assertEqual(self.feed(a), [])

    def test_revoke_stale_copy_and_feed(self):
        a = self.join()
        call = self.publish()
        item, = self.feed(a)
        for _ in range(2):
            self.send("/revoke", {"call_id": call["call_id"]}, self.admin)
        self.verify(a, item, 410)
        self.now += 5
        self.assertEqual(self.feed(a), [])

    def test_unsubscribe_invalidates_credential(self):
        a = self.join()
        self.publish()
        item, = self.feed(a)
        self.send("/unsubscribe", {}, a["token"])
        self.send("/feed", token=a["token"], status=401)
        self.verify(a, item, 401)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertIsNone(db.execute("SELECT token FROM agents").fetchone()[0])

    def test_roles_and_no_plaintext_tokens(self):
        a = self.join()
        self.send("/feed", token=self.admin, status=403)
        self.send("/feed", status=401)
        self.send("/publish", {"project": "shapes", "ttl_seconds": 2}, a["token"], 403)
        self.send("/revoke", {"call_id": "fake"}, a["token"], 403)
        data = self.path.read_bytes()
        self.assertNotIn(a["token"].encode(), data)
        self.assertNotIn(self.admin.encode(), data)

    def test_publish_and_poll_limits(self):
        agent = self.join()
        self.publish()
        self.feed(agent)
        self.send("/feed", token=agent["token"], status=429)
        self.publish("graphs", status=429)
        self.now += 59
        self.publish("graphs", status=429)
        self.now += 1
        self.publish("graphs")
        self.publish("unknown", status=400)
        self.publish("words", ttl=True, status=400)
        self.publish("words", ttl=86401, status=400)
        self.assertEqual(len(self.feed(agent)), 2)

    def test_transport_guardrails(self):
        self.send("/register", {}, status=400, extra={"Host": "elsewhere"})
        self.send("/register", {}, status=400, extra={"Origin": "null"})
        self.send("/register", {}, status=400, raw=b'{"consent":0,"consent":1}')
        self.send("/register", {}, status=413, raw=b" " * 4097)
        self.send("/feed?token=invalid", {}, status=404)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()

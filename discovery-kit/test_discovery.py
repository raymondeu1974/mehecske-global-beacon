"""Offline checks for discovery data and the stdio transport."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
META = "io.modelcontextprotocol/"
VERSION = "2026-07-28"
URI = "beacon://discovery/feed.json"


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def request(request_id, method, version=VERSION, **params):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {
            "_meta": {META + "protocolVersion": version, META + "clientCapabilities": {}},
            **params,
        },
    }


def exchange(*messages):
    lines = [msg if isinstance(msg, str) else json.dumps(msg) for msg in messages]
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / "mcp_stdio.py")],
        input="\n".join(lines) + "\n", text=True, encoding="utf-8",
        capture_output=True, timeout=10, check=True, cwd=ROOT.parent,
    )
    if proc.stderr:
        raise AssertionError(proc.stderr)
    return [json.loads(line) for line in proc.stdout.splitlines()]


class DiscoveryTests(unittest.TestCase):
    def test_task_catalog_contract(self):
        feed = load("feed.json")
        schema = load("feed.schema.json")
        self.assertEqual(set(feed), set(schema["required"]))
        self.assertEqual(feed["call"], "DISCOVER THE UNKNOWN. PROVE IT. GO BEYOND.")
        self.assertFalse(feed["participation"]["automaticExecution"])
        self.assertFalse(feed["participation"]["automaticContact"])
        task_fields = schema["$defs"]["task"]
        ids = set()
        for task in feed["tasks"]:
            self.assertEqual(set(task), set(task_fields["required"]))
            self.assertNotIn(task["id"], ids)
            ids.add(task["id"])
            self.assertTrue(task["operatorAuthorizationRequired"])
            self.assertEqual(task["mode"], "offline-manual")
            for field in ("fixtureUrl", "instructionsUrl"):
                self.assertRegex(task[field], task_fields["properties"][field]["pattern"])
            self.assertEqual(task["fixtureUrl"].rsplit("/", 1)[0],
                             task["instructionsUrl"].rsplit("/", 1)[0])
            self.assertEqual(task["id"], load(task["resultSchema"])["properties"]["task_id"]["const"])
        self.assertTrue(ids)

    def test_offline_agent_card(self):
        card = load("examples/agent-card.example.json")
        self.assertEqual(set(card), {
            "name", "description", "supportedInterfaces", "version", "documentationUrl",
            "capabilities", "defaultInputModes", "defaultOutputModes", "skills",
        })
        self.assertEqual(card["supportedInterfaces"], [{
            "url": "https://beacon.example.invalid/a2a",
            "protocolBinding": "JSONRPC", "protocolVersion": "1.0",
        }])
        self.assertTrue(all(value is False for value in card["capabilities"].values()))
        self.assertIn("No live endpoint", card["description"])

    def test_resource_round_trip(self):
        replies = exchange(
            request(1, "server/discover"), request(2, "resources/list"),
            request("read", "resources/read", uri=URI),
            request(4, "resources/templates/list"), request(5, "ping"),
        )
        self.assertEqual([item["id"] for item in replies], [1, 2, "read", 4, 5])
        results = [reply["result"] for reply in replies]
        for result in results:
            self.assertEqual(result["resultType"], "complete")
            self.assertIn(META + "serverInfo", result["_meta"])
        for result in results[:4]:
            self.assertEqual((result["ttlMs"], result["cacheScope"]), (0, "private"))
        self.assertEqual(results[0]["supportedVersions"], [VERSION])
        self.assertEqual(results[0]["capabilities"], {"resources": {}})
        self.assertEqual(results[1]["resources"][0]["uri"], URI)
        content, = results[2]["contents"]
        self.assertEqual(content["uri"], URI)
        self.assertEqual(content["mimeType"], "application/json")
        self.assertEqual(json.loads(content["text"]), load("feed.json"))
        self.assertEqual(results[3]["resourceTemplates"], [])

    def test_rejects_execution_external_reads_and_bad_metadata(self):
        replies = exchange(
            request(1, "tools/call"),
            request(2, "resources/read", uri="file:///private.json"),
            request(3, "resources/read", uri="https://beacon.example.invalid/feed.json"),
            request(4, "ping", version="2025-11-25"),
            request(5, "resources/list", _meta=None),
            request(6, "resources/list", cursor="unexpected"),
            request(7, "initialize"),
        )
        self.assertEqual([reply["error"]["code"] for reply in replies],
                         [-32601, -32602, -32602, -32022, -32602, -32602, -32601])
        self.assertEqual(replies[3]["error"]["data"]["supported"], [VERSION])

    def test_autonomous_resource_round_trip(self):
        uri = "beacon://discovery/autonomous-feed.json"
        listing, read = exchange(request(1, "resources/list"), request(2, "resources/read", uri=uri))
        self.assertIn(uri, [item["uri"] for item in listing["result"]["resources"]])
        content, = read["result"]["contents"]
        self.assertEqual(content["uri"], uri)
        self.assertEqual(json.loads(content["text"]), load("../autonomous/feed.json"))

    def test_bad_frames_and_notification_do_not_stop_stdio(self):
        replies = exchange(
            "{", "[1]", '{"jsonrpc":"2.0","method":"notifications/cancelled"}',
            "x" * 70000, request(1, "ping"),
        )
        self.assertEqual([item["error"]["code"] for item in replies[:-1]],
                         [-32700, -32600, -32600])
        self.assertEqual(replies[-1]["id"], 1)


if __name__ == "__main__":
    unittest.main()

"""Exercise the gateway through a real bidirectional MCP stdio session."""
import json
from queue import Queue
import subprocess
import sys
from threading import Thread
import unittest

from test_arena import RESULTS, ROOT, run

VERSION = "2025-11-25"
SERVER = ROOT / "discovery-kit/gateway_stdio.py"


class GatewayTests(unittest.TestCase):
    def start(self, approved=()):
        command = [sys.executable, "-B", str(SERVER)]
        for task_id in approved:
            command.extend(("--approve-task", task_id))
        process = subprocess.Popen(command, cwd=ROOT.parent, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.process = process
        self.responses = Queue()
        self.request_id = 0

        def read_responses():
            for line in process.stdout:
                self.responses.put(line)
            self.responses.put(b"")

        def finish():
            process.stdin.close()
            try:
                process.wait(timeout=10)
                self.assertEqual(process.stderr.read(), b"")
                self.assertEqual(process.returncode, 0)
                self.assertEqual(self.responses.get(timeout=10), b"")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                reader.join(timeout=10)
                process.stdout.close()
                process.stderr.close()

        reader = Thread(target=read_responses, daemon=True)
        reader.start()
        self.addCleanup(finish)

    def send(self, message):
        self.process.stdin.write(json.dumps(message).encode("utf-8") + b"\n")
        self.process.stdin.flush()

    def receive(self):
        response = json.loads(self.responses.get(timeout=10))
        self.assertEqual(response["jsonrpc"], "2.0")
        return response

    def request(self, method, **params):
        self.request_id += 1
        self.send({"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params})
        response = self.receive()
        self.assertEqual(response["id"], self.request_id)
        return response

    def initialize(self, version=VERSION):
        init = self.request("initialize", protocolVersion=version,
                            capabilities={}, clientInfo={"name": "wire-test", "version": "1"})["result"]
        self.assertEqual(init["protocolVersion"], VERSION)
        self.assertEqual(init["serverInfo"]["name"], "mehecske-agent-gateway")
        self.assertEqual(init["capabilities"], {"tools": {}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name, **arguments):
        return self.request("tools/call", name=name, arguments=arguments)["result"]

    def content(self, name, **arguments):
        result = self.call(name, **arguments)
        self.assertFalse(result.get("isError"), result)
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
        return result["structuredContent"]

    def test_manifest_and_default_discovery(self):
        discovery = json.loads((ROOT / "agent-discovery.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / discovery["agent_gateway"]["manifest_path"]).read_text(encoding="utf-8"))
        for key in ("guide_path", "skill_path", "arena_manifest_path"):
            self.assertTrue((ROOT / manifest[key]).is_file())
        self.assertEqual(ROOT / manifest["mcp"]["args"][-1], SERVER)
        self.assertEqual(manifest["mcp"]["protocol_version"], VERSION)
        self.assertIsNone(manifest["mcp"]["endpoint"])
        self.assertFalse(manifest["participation"]["automatic_publication"])

        self.start()
        self.assertEqual(self.request("tools/list")["error"]["code"], -32000)
        self.initialize("2025-06-18")
        self.assertEqual(self.request("ping")["result"], {})
        tools = self.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], manifest["mcp"]["tools"])
        self.assertTrue(all(tool["inputSchema"]["type"] == "object" for tool in tools))
        tasks = self.content("list_tasks")
        self.assertEqual(tasks["approved_task_ids"], manifest["participation"]["default_approved_task_ids"])
        self.assertEqual([task["id"] for task in tasks["tasks"]], [item["task_id"] for item in RESULTS])
        self.assertTrue(self.call("get_task", task_id=RESULTS[0]["task_id"])["isError"])
        self.assertTrue(self.call("verify_result", result=RESULTS[0])["isError"])

    def test_all_tasks_and_cli_receipt_interoperability(self):
        self.start(item["task_id"] for item in RESULTS)
        self.initialize()
        for answer in RESULTS:
            with self.subTest(task=answer["task_id"]):
                task = self.content("get_task", task_id=answer["task_id"])
                self.assertEqual(task["id"], answer["task_id"])
                self.assertEqual(set(task["result_fields"]), set(answer))
                self.assertTrue(task["fixture"])
                receipt = self.content("verify_result", result=answer)
                cli = run("verify", answer, "--operator-approved")
                self.assertEqual(cli.returncode, 0, cli.stderr)
                self.assertEqual(receipt, json.loads(cli.stdout))
                self.assertEqual(self.content("recheck_receipt", receipt=receipt), receipt)
                self.assertTrue(self.call("recheck_receipt", receipt=receipt | {"receipt_sha256": "0" * 64})["isError"])

    def test_invalid_input_and_allowlist(self):
        answer = RESULTS[0]
        self.start([answer["task_id"]])
        self.initialize()
        self.assertEqual(self.request("tools/call", name="missing")["error"]["code"], -32602)
        self.assertEqual(self.request("tools/list", cursor="unexpected")["error"]["code"], -32602)
        self.assertEqual(self.request("missing")["error"]["code"], -32601)
        for invalid in (answer | {"distance": True}, answer | {"distance": 999},
                        answer | {"task_id": "../call"}, answer | {"extra": "a" * 1024},
                        RESULTS[1], []):
            with self.subTest(value=invalid):
                self.assertTrue(self.call("verify_result", result=invalid)["isError"])
        self.assertTrue(self.call("get_task", task_id=RESULTS[1]["task_id"], operator_approved=True)["isError"])
        self.assertTrue(self.call("recheck_receipt", receipt={"result": RESULTS[1]})["isError"])
        for line, code in ((b"{\n", -32700), (b'{"id":1,"id":2}\n', -32700),
                           (b" " * 65536 + b"\n", -32600)):
            self.process.stdin.write(line)
            self.process.stdin.flush()
            self.assertEqual(self.receive()["error"]["code"], code)
        self.assertEqual(self.content("list_tasks")["approved_task_ids"], [answer["task_id"]])

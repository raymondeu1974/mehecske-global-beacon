"""Smoke-test the gateway with the official MCP Python SDK."""
import asyncio
import json
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from test_arena import RESULTS, ROOT, run


@asynccontextmanager
async def connect(manifest, approved=()):
    installed = os.environ.get("MEHECSKE_CONNECT_TEST_ENTRYPOINT")
    command = str(Path(installed).resolve()) if installed else sys.executable
    args = [] if installed else ["-B", str(ROOT / manifest["mcp"]["args"][-1])]
    for task_id in approved:
        args.extend((manifest["participation"]["operator_approval_flag"], task_id))
    with tempfile.TemporaryDirectory() as cwd:
        server = StdioServerParameters(command=command, args=args, cwd=cwd)
        async with stdio_client(server) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=10)) as session:
                yield session


class SDKInteropTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "discovery-kit/gateway.json").read_text(encoding="utf-8"))

    async def content(self, session, name, arguments=None):
        result = await session.call_tool(name, arguments)
        self.assertFalse(result.isError, result)
        self.assertEqual(json.loads(result.content[0].text), result.structuredContent)
        return result.structuredContent

    async def test_official_client(self):
        task_ids = [answer["task_id"] for answer in RESULTS]
        receipts = []
        async with connect(self.manifest, task_ids) as session:
            init = await session.initialize()
            self.assertEqual(init.protocolVersion, self.manifest["mcp"]["protocol_version"])
            self.assertEqual(init.serverInfo.name, self.manifest["id"])
            self.assertIsNotNone(init.capabilities.tools)
            tools = await session.list_tools()
            self.assertEqual([tool.name for tool in tools.tools], self.manifest["mcp"]["tools"])
            self.assertIsNone(tools.nextCursor)
            tasks = await self.content(session, "list_tasks")
            self.assertEqual(tasks["approved_task_ids"], sorted(task_ids))
            self.assertEqual([task["id"] for task in tasks["tasks"]], task_ids)
            for answer in RESULTS:
                task_id = answer["task_id"]
                with self.subTest(task=task_id):
                    task = await self.content(session, "get_task", {"task_id": task_id})
                    self.assertEqual(task["id"], task_id)
                    self.assertEqual(set(task["result_fields"]), set(answer))
                    self.assertTrue(task["fixture"])
                    receipt = await self.content(session, "verify_result", {"result": answer})
                    cli = await asyncio.to_thread(run, "verify", answer, "--operator-approved")
                    self.assertEqual(cli.returncode, 0, cli.stderr)
                    self.assertEqual(receipt, json.loads(cli.stdout))
                    self.assertEqual(await self.content(session, "recheck_receipt", {"receipt": receipt}), receipt)
                    tampered = dict(receipt, receipt_sha256="0" * 64)
                    self.assertTrue((await session.call_tool("recheck_receipt", {"receipt": tampered})).isError)
                    receipts.append(receipt)

        for approved in ([], task_ids[:1]):
            async with connect(self.manifest, approved) as session:
                await session.initialize()
                tasks = await self.content(session, "list_tasks")
                self.assertEqual(tasks["approved_task_ids"], approved)
                for answer, receipt in zip(RESULTS, receipts, strict=True):
                    task_id = answer["task_id"]
                    if task_id in approved:
                        await self.content(session, "get_task", {"task_id": task_id})
                        continue
                    for name, arguments in (
                        ("get_task", {"task_id": task_id}),
                        ("verify_result", {"result": answer}),
                        ("recheck_receipt", {"receipt": receipt}),
                    ):
                        with self.subTest(approved=approved, task=task_id, tool=name):
                            self.assertTrue((await session.call_tool(name, arguments)).isError)


if __name__ == "__main__":
    unittest.main()

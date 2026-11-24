"""Serve the offline Arena over MCP 2025-11-25 stdio."""
import argparse
import json
import sys

from arena import MAX_INPUT_BYTES, canonical, check_receipt, make_receipt
from beacon_runner import TASK, fixture, unique_object
from mcp_stdio import MAX_LINE, reject_constant
from verify_benchmark import HERE, read_json

VERSION = "2025-11-25"
SERVER_INFO = {"name": "mehecske-agent-gateway", "version": "1.0.0"}
TASKS = {
    task["id"]: {key: task[key] for key in ("id", "title", "summary", "result_fields")}
    for task in read_json(HERE / "catalog.json")["tasks"]
}
OBJECT = {"type": "object"}
TASK_ID = {"type": "string", "enum": list(TASKS)}


def tool(name, description, **properties):
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    }


TOOLS = {entry["name"]: entry for entry in (
    tool("list_tasks", "List bundled offline task descriptions and result fields."),
    tool("get_task", "Read the bundled fixture for an operator-approved task.", task_id=TASK_ID),
    tool("verify_result", "Reproduce an approved task result and return a local Arena receipt.",
         result=OBJECT),
    tool("recheck_receipt", "Recompute and compare an Arena receipt for an approved task.",
         receipt=OBJECT),
)}


def failure(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def result_content(value, *, error=False):
    result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=True)}]}
    if error:
        result["isError"] = True
    else:
        result["structuredContent"] = value
    return result


class Gateway:
    def __init__(self, approved, allowed_tools):
        self.approved = frozenset(approved)
        self.allowed_tools = frozenset(allowed_tools)
        self.negotiated = False
        self.ready = False

    def call(self, name, arguments):
        schema = TOOLS[name]["inputSchema"]
        if not isinstance(arguments, dict) or arguments.keys() != set(schema["required"]):
            raise ValueError("Invalid tool arguments")
        if name == "list_tasks":
            return {"tasks": list(TASKS.values()), "approved_task_ids": sorted(self.approved)}
        if name == "get_task":
            task = arguments["task_id"]
        else:
            value = next(iter(arguments.values()))
            if not isinstance(value, dict) or len(canonical(value)) > MAX_INPUT_BYTES:
                raise ValueError("Expected a JSON object of at most 1024 bytes")
            answer = value if name == "verify_result" else value.get("result")
            task = answer.get("task_id") if isinstance(answer, dict) else None
        if not isinstance(task, str) or task not in self.approved:
            raise ValueError("Task requires operator approval at server launch")
        if name == "get_task":
            data = (fixture() if task == TASK
                    else read_json(HERE / "fixtures" / f"{task}.json"))
            return {**TASKS[task], "fixture": data}
        if name == "verify_result":
            return make_receipt(value, "local-reproduction")
        return check_receipt(value)

    def handle(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return failure(None, -32600, "Invalid request")
        method = request.get("method")
        request_id = request.get("id")
        if not isinstance(method, str):
            return failure(None, -32600, "Invalid request")
        if "id" not in request:
            if method == "notifications/initialized" and self.negotiated:
                self.ready = True
            return None
        if type(request_id) not in (str, int):
            return failure(None, -32600, "Invalid request ID")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return failure(request_id, -32602, "Expected an object for params")
        if method == "initialize":
            client_info = params.get("clientInfo")
            if self.negotiated:
                return failure(request_id, -32600, "Session already initialized")
            if (not isinstance(params.get("protocolVersion"), str)
                    or not isinstance(params.get("capabilities"), dict)
                    or not isinstance(client_info, dict)
                    or any(not isinstance(client_info.get(key), str) for key in ("name", "version"))):
                return failure(request_id, -32602, "Invalid initialization parameters")
            self.negotiated = True
            result = {"protocolVersion": VERSION, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
        elif method == "ping":
            result = {}
        elif not self.ready:
            return failure(request_id, -32000, "Session has not completed initialization")
        elif method == "tools/list":
            if "cursor" in params:
                return failure(request_id, -32602, "Unknown pagination cursor")
            result = {"tools": [tool for name, tool in TOOLS.items() if name in self.allowed_tools]}
        elif method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or name not in self.allowed_tools:
                return failure(request_id, -32602, "Unknown tool")
            try:
                result = result_content(self.call(name, params.get("arguments", {})))
            except (ValueError, RecursionError) as exc:
                result = result_content({"error": str(exc)}, error=True)
            except OSError:
                return failure(request_id, -32603, "Bundled Arena files unavailable")
        else:
            return failure(request_id, -32601, "Method not found")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-task", choices=TASKS, action="append", default=[],
                        help="Enable one task for this session after explicit operator approval")
    parser.add_argument("--allow-tool", choices=TOOLS, action="append",
                        help="Restrict this session to the named tool(s); repeat to enable more")
    options = parser.parse_args()
    gateway = Gateway(options.approve_task, TOOLS if options.allow_tool is None else options.allow_tool)
    while line := sys.stdin.buffer.readline(MAX_LINE + 1):
        if len(line) > MAX_LINE:
            while line and not line.endswith(b"\n"):
                line = sys.stdin.buffer.readline(MAX_LINE + 1)
            response = failure(None, -32600, "Request exceeds the server size limit")
        else:
            try:
                request = json.loads(line.decode("utf-8"), object_pairs_hook=unique_object,
                                     parse_constant=reject_constant)
            except (ValueError, RecursionError):
                response = failure(None, -32700, "Parse error")
            else:
                response = gateway.handle(request)
        if response is not None:
            sys.stdout.buffer.write(json.dumps(response, ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n")
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()

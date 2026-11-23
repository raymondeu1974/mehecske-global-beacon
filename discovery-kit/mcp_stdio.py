"""Expose the bundled discovery feed as a read-only MCP stdio resource."""
import json
from pathlib import Path
import sys

VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"
SERVER_INFO = {"name": "mehecske-discovery", "version": "1.0.0"}
RESOURCE = {
    "uri": "beacon://discovery/feed.json",
    "name": "Beacon discovery feed",
    "mimeType": "application/json",
}
FEED = Path(__file__).with_name("feed.json")
MAX_LINE = 65536


def error(request_id, code, message, data=None):
    details = {"code": code, "message": message}
    if data is not None:
        details["data"] = data
    response = {"jsonrpc": "2.0", "error": details}
    if request_id is not None:
        response["id"] = request_id
    return response


def handle(request):
    if not isinstance(request, dict):
        return error(None, -32600, "Invalid request")
    request_id = request.get("id")
    valid_id = type(request_id) in (str, int)
    method = request.get("method")
    if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return error(request_id if valid_id else None, -32600, "Invalid request")
    if "id" not in request:
        return None
    if not valid_id:
        return error(None, -32600, "Invalid request ID")
    if method == "initialize":
        return error(request_id, -32601, f"Legacy initialize is unsupported. Use MCP {VERSION}.")

    params = request.get("params")
    meta = params.get("_meta") if isinstance(params, dict) else None
    version = meta.get(META + "protocolVersion") if isinstance(meta, dict) else None
    if not isinstance(version, str) or not isinstance(meta.get(META + "clientCapabilities"), dict):
        return error(request_id, -32602, "Missing or invalid MCP request metadata")
    if version != VERSION:
        return error(request_id, -32022, "Unsupported protocol version",
                     {"requested": version, "supported": [VERSION]})

    result = {"resultType": "complete", "_meta": {META + "serverInfo": SERVER_INFO}}
    if method == "server/discover":
        result.update(supportedVersions=[VERSION], capabilities={"resources": {}})
    elif method in ("resources/list", "resources/templates/list"):
        if "cursor" in params:
            return error(request_id, -32602, "Unknown pagination cursor")
        if method == "resources/list":
            result["resources"] = [RESOURCE]
        else:
            result["resourceTemplates"] = []
    elif method == "resources/read":
        if params.get("uri") != RESOURCE["uri"]:
            return error(request_id, -32602, "Unknown resource URI")
        try:
            feed = FEED.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return error(request_id, -32603, "Bundled feed unavailable")
        result["contents"] = [{
            "uri": RESOURCE["uri"], "mimeType": RESOURCE["mimeType"], "text": feed
        }]
    elif method != "ping":
        return error(request_id, -32601, "Method not found")

    if method != "ping":
        result.update(ttlMs=0, cacheScope="private")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def reject_constant(_value):
    raise ValueError("Invalid JSON constant")


def main():
    while line := sys.stdin.buffer.readline(MAX_LINE + 1):
        if len(line) > MAX_LINE:
            while line and not line.endswith(b"\n"):
                line = sys.stdin.buffer.readline(MAX_LINE + 1)
            response = error(None, -32600, "Request exceeds the adapter size limit")
        else:
            try:
                request = json.loads(line.decode("utf-8"), parse_constant=reject_constant)
            except (ValueError, RecursionError):
                response = error(None, -32700, "Parse error")
            else:
                response = handle(request)
        if response is not None:
            sys.stdout.buffer.write(json.dumps(response).encode("utf-8") + b"\n")
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()

# Méhecske Agent Gateway

Use a stdio MCP client to discover and complete the [three offline Arena tasks](ARENA.md).
Start with [agent-discovery.json](../agent-discovery.json), then read the
[gateway manifest](gateway.json) and [Agent Skill](../skills/mehecske-agent-gateway/SKILL.md)
from the same Git revision. The manifest uses repository-relative paths.

## Connect a client

1. Obtain and review a clean checkout pinned to a full Git commit containing
   this guide. Use Python 3.11 or newer. The gateway uses the standard library.
2. Register the command below in a client that supports MCP `2025-11-25` over
   stdio. Replace both paths with absolute paths on your machine. Run the
   executable directly from the client. Windows users can use forward slashes
   in JSON paths and the full path to `python.exe`.
3. With no approval flags, the client can use `list_tasks`. When the operator
   explicitly approves a task for this session, add `"--approve-task", "<task-id>"`
   to the argument array and restart the server. Repeat the pair for each
   approved task. Remove the pair and restart to revoke access.
4. To install the skill, copy the entire `skills/mehecske-agent-gateway`
   directory into the client's skills directory, or import that directory
   through its skills interface. For Codex, the project-level location is
   `.agents/skills/mehecske-agent-gateway`. The operator configures the MCP
   server separately from installing the skill.

Example client configuration for read-only discovery before task opt-in.

```json
{
  "mcpServers": {
    "mehecske-arena": {
      "command": "/absolute/path/to/python",
      "args": ["-B", "/absolute/path/to/checkout/discovery-kit/gateway_stdio.py"]
    }
  }
}
```

| Tool | Arguments | Result |
| --- | --- | --- |
| `list_tasks` | `{}` | Task descriptions, answer field names, session allowlist |
| `get_task` | `{"task_id":"interval-schedule-v1"}` | Bundled fixture and task metadata |
| `verify_result` | `{"result":{...}}` | Deterministic Arena receipt |
| `recheck_receipt` | `{"receipt":{...}}` | Matching receipt recomputed from bundled fixtures |

Success includes JSON in `structuredContent` and text content. Invalid task
inputs and rejected results use `isError`. Protocol errors use JSON-RPC
error responses. Requests are limited to 64 KiB per line, and compact answer
and receipt objects are limited to 1 KiB. Receipt output stays with the client.

The launch allowlist controls the gateway's tools for the process lifetime.
Treat every client sharing that process as equally authorized. Someone with
filesystem or command access to the checkout can use the public fixtures and
Arena CLI directly. The gateway has no network listener or publication tools.
See [Arena receipt semantics and public evidence rules](ARENA.md) for what
local checks establish and how separate operator-approved sharing works.

## Test

Run from the repository root.

```sh
python -B -m unittest discover -s discovery-kit -p 'test_gateway.py' -v
python -B -m unittest discover -s discovery-kit -v
python -B -m unittest discover -s autonomous -v
python -B -m unittest discover -s mission-pilot -v
python -B -m unittest -v
```

The gateway test starts a real subprocess and exchanges newline-delimited
MCP requests and responses. It exercises initialization, tool discovery,
all three tasks, invalid requests, approval and receipt rechecks. It uses
an in-repository test client. Independent external agent participation
requires an operator to connect their own client and reproduce a task.

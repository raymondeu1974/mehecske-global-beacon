# Méhecske Agent Gateway

Use a stdio MCP client to discover and complete the [three offline Arena tasks](ARENA.md).
Start with [agent-discovery.json](../agent-discovery.json), then read the
[gateway manifest](gateway.json) and [Agent Skill](../skills/mehecske-agent-gateway/SKILL.md)
from the same Git revision. The manifest uses repository-relative paths.

## Connect a client

1. Obtain and review a clean checkout pinned to a full Git commit containing
   this guide. Use Python 3.11 or newer. The gateway uses the standard library.

   ```sh
   git clone https://github.com/raymondeu1974/mehecske-global-beacon.git
   cd mehecske-global-beacon
   git checkout --detach <reviewed-full-commit-sha>
   ```

   For a PR preview, take the full commit SHA from its Commits tab. Use that
   revision for the server, manifest and Skill. On public GitHub, start at the
   [project landing page](https://raymondeu1974.github.io/mehecske-global-beacon/)
   or the repository README to find all three.
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

For the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
check, create an isolated environment. Activate it with `source .venv/bin/activate`
on macOS or Linux, or use `.venv/Scripts/python.exe` in place of `python`
for the install and test commands on Windows.

```sh
python -m venv .venv
# Activate the environment, or use its Python executable for both commands.
python -m pip install "mcp==1.26.0"
python -B discovery-kit/check_gateway_sdk.py -v
```

This check starts the gateway as a local stdio subprocess, negotiates the
protocol with `ClientSession.initialize`, lists tools, and calls them for all
three tasks. It compares receipts with the Arena CLI, rejects altered receipts
and checks denial with empty and partial allowlists. The SDK is a test-only
dependency. A separate wire-level test covers invalid JSON-RPC requests.
Independent participation requires a separate operator to connect their own
client and reproduce a task.

## Official MCP Registry

A future listing can preserve local stdio. One option is a versioned public
PyPI package containing the launch entry point and bundled fixtures.
Use a name such as `io.github.raymondeu1974/mehecske-agent-gateway` if
publishing with authorization for that GitHub namespace. Include the matching
`mcp-name:` marker in the package README and describe the published version
and stdio transport in a schema-valid `server.json`. An authorized publisher
then authenticates the namespace and submits the metadata with
`mcp-publisher`. The [package requirements](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx)
and [publishing quickstart](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
describe the validation and submission steps. This gateway is distributed
as a source checkout. Its discovery manifest and Agent Skill are project
discovery files. Neither publishes a Registry entry.

To limit a session further, pass repeatable `--allow-tool <name>` options in
the operator-controlled server command. The Gateway advertises and accepts
only the named tools in that session. A tool grant never grants a task; pass
`--approve-task <id>` separately for fixture access, verification, or rechecks.
For example, combine `--allow-tool list_tasks --allow-tool get_task` to allow
discovery and fixture access with no verification tools.

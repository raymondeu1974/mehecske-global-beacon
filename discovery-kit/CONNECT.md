# Méhecske Connect

Connect installs the offline Arena Gateway as a local MCP stdio command.
Version `0.1.0` is a release candidate for review. The PyPI package and MCP
Registry entry are unpublished. Use a reviewed, pinned checkout or a wheel
built from that checkout.

## Install and launch

From the root of the pinned checkout, with Python 3.11+ and uv installed,
create a temporary tool environment and start the server in one command:

```sh
uvx --from . mehecske-connect
```

Source builds may download the build backend. uv may also fetch a compatible
Python if one is unavailable. Once the wheel is on disk, you can start it
offline with an installed Python 3.11+:

```sh
uvx --offline --no-python-downloads --from ./dist/mehecske_connect-0.1.0-py3-none-any.whl mehecske-connect
```

To build and install the local wheel with Python, use an active virtual
environment at the checkout root:

```sh
python -m pip install build
python -m build
python -m pip install --no-index --no-deps ./dist/mehecske_connect-0.1.0-py3-none-any.whl
mehecske-connect --help
```

An MCP client should launch the installed executable, using its absolute
path if the client does not inherit the environment's PATH. On Windows it
is `Scripts/mehecske-connect.exe` in the virtual environment; on Unix it is
`bin/mehecske-connect`. Example command and argument fields:

```json
{
  "command": "mehecske-connect",
  "args": ["--approve-task", "interval-schedule-v1"]
}
```

Start with empty arguments for discovery. After reviewing a task, the operator
adds one `--approve-task <task-id>` per approved task and restarts the session.
`list_tasks` reports the allowed IDs. `get_task`, `verify_result`, and
`recheck_receipt` enforce that allowlist. Each launch uses a fresh allowlist.
The Gateway reads bundled files and exchanges MCP messages over stdio. Its tool
paths make no network calls, accept no foreign code, and perform no publication
or outreach.

Use the [Gateway guide](GATEWAY.md) for the protocol and tool details.
The public [discovery manifest](https://raw.githubusercontent.com/raymondeu1974/mehecske-global-beacon/main/agent-discovery.json)
and [Agent Skill](https://raw.githubusercontent.com/raymondeu1974/mehecske-global-beacon/main/skills/mehecske-agent-gateway/SKILL.md)
are entry points for operators and clients. Local SDK interoperability and
Arena receipts demonstrate offline execution. Independent external agent
participation has yet to be demonstrated.

## Release only after separate approval

1. Verify the release commit and confirm distribution rights before PyPI
   publication. The source repository currently has no explicit license file.
   Recheck the normalized [PyPI project name](https://pypi.org/project/mehecske-connect/)
   and confirm control of the project or eligibility to create it. A 404
   means there is no public project at that URL and does not reserve the name.
2. Build both distributions with `python -m build`, run
   `python -m twine check --strict dist/*`, and run the installed-wheel SDK
   checks. Keep the distribution name and package version in sync with
   [server.json](../server.json). The PyPI description must carry the
   `mcp-name: io.github.raymondeu1974/mehecske-connect` marker from the README.
3. After explicit PyPI approval, upload the exact reviewed wheel and sdist
   using `python -m twine upload dist/*` from a clean release directory.
   Confirm the published version and the description marker in PyPI metadata.
   Only then use the index-based command `uvx mehecske-connect@0.1.0`.
4. After separate MCP Registry approval, authenticate the official
   `mcp-publisher login github` as the owner of the `raymondeu1974` GitHub
   namespace. Validate the manifest against its declared schema and the official
   Registry's validation API, then run `mcp-publisher publish` from the checkout
   root. Verify the server entry and version before updating the discovery
   release status. The CI workflow builds and tests artifacts only.

References: [MCP Registry publishing](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx),
[namespace authentication](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/authentication.mdx),
[PyPA packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/),
[uv tool execution](https://docs.astral.sh/uv/concepts/tools/).

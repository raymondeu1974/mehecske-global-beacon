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

### Resolve distribution rights

The repository has no explicit license file. Before building a public release,
the rights holder must confirm permission to distribute every file in both
the wheel and the sdist, including the Gateway, verifiers, fixtures, skill,
and documentation. Review the contributor history and source of bundled files,
including files included only in the sdist. Record the applicable license and
required notices in the repository, declare the corresponding package license
metadata, and inspect both archives for the expected license and notice files.
If any item cannot be cleared, obtain permission or remove or replace it in a
reviewed change before any upload.

### PyPI

1. Check the [normalized PyPI project name](https://pypi.org/project/mehecske-connect/).
   If the project exists, its owner must configure Trusted Publishing or grant
   the required access. For a new project, a PyPI account holder can configure
   a [pending Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
   A missing public project page does not reserve the name.
2. Review a separate GitHub Actions release workflow, for example
   `.github/workflows/publish-pypi.yml`. Use manual dispatch from the reviewed
   release ref and bind the publisher to
   `raymondeu1974/mehecske-global-beacon`, the exact workflow filename, and
   the `pypi` environment. A repository administrator configures the environment
   and its branch or tag restrictions. Build and test in a job with read-only
   repository access. Grant `id-token: write` only to the publish job, which
   uploads the tested wheel and sdist using
   [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
3. On the reviewed release commit run `python -m build`,
   `python -m twine check --strict dist/*`, and the installed-wheel MCP SDK
   checks outside the checkout. Verify the archive contents and record their
   SHA-256 hashes. Keep the package name and version aligned with
   [server.json](../server.json). The PyPI description must carry the
   `mcp-name: io.github.raymondeu1974/mehecske-connect` marker from the README.
4. After explicit PyPI approval, run the reviewed workflow and verify the public
   version, description marker, and artifact hashes. Test an MCP initialization
   using `uvx mehecske-connect@0.1.0` from a clean environment.

### MCP Registry

1. After verifying the public PyPI release, validate the same release's
   `server.json` against its declared schema. Confirm the Registry name,
   package version, and current Registry listing for that name.
2. After separate MCP Registry approval, authenticate as the owner of the
   `raymondeu1974` personal GitHub namespace using the official
   `mcp-publisher login github` device flow. The Registry also supports
   GitHub Actions OIDC from an authorized repository. Publish the reviewed
   manifest using `mcp-publisher publish`.
3. Verify the exact server name and version via the public Registry API, then
   update the discovery manifest and installation guide to reflect the confirmed
   release.

References: [MCP Registry publishing](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx),
[namespace authentication](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/authentication.mdx),
[PyPA packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/),
[uv tool execution](https://docs.astral.sh/uv/concepts/tools/).

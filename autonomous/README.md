# Autonomous research

Méhecske Global Beacon publishes a synthetic reproducibility task for agents whose
operators have already authorized discovery and execution for that task. The
[manual pilot and its withdrawal process](../mission-pilot/PUBLIC-PILOT.md) are available separately.

## Discovery and feed contract

The repository root links to [agent-discovery.json](../agent-discovery.json).
The manifest identifies this project and its canonical UTF-8 JSON feed. Both
documents can be fetched anonymously. The manifest is Beacon-specific.

Feed `schema_version` 1 contains a `tasks` array. Each task has a unique
`id`, a `status` of `available` or `withdrawn`, a `kind` and a
`fixture_sha256` digest. Missing, withdrawn, duplicate or unsupported tasks
are ineligible. New or revised tasks require a new ID and authorization.
The fixture for the first task is the `fixture` object in the [pinned pilot
file](https://github.com/raymondeu1974/mehecske-global-beacon/blob/147d90f57541419cb068ae29c9bb52327c10cab6/mission-pilot/call.json).
Its digest is SHA-256 over UTF-8 JSON with sorted keys and compact separators.
The task asks for shortest distance and the number of shortest paths on that
directed unit-weight graph. The [result schema](../discovery-kit/result.schema.json)
documents the three result fields. The autonomous verifier accepts JSON integer
literals for both metrics.

A2A has an [offline Agent Card example](../discovery-kit/examples/agent-card.example.json)
for the manual pilot. There is no A2A service or well-known card. MCP revision
2026-07-28 is available through the [local stdio adapter](../discovery-kit/mcp_stdio.py).
It provides the bundled snapshot at `beacon://discovery/autonomous-feed.json`
alongside the manual feed. Refresh the canonical HTTPS feed before acting on a
snapshot. MCP provides read-only resources, with no remote endpoint or tools.

## Local example and operator opt-in

Run from a reviewed checkout with Python 3.11 or later.

```text
python -B autonomous/beacon_runner.py demo
```

The demo polls twice, solves the graph by enumerating simple paths, and hands the
result to the same breadth-first verifier used in GitHub Actions. A temporary
receipt confirms reproduction, and the second poll skips duplicate submission.
The demo uses only local files and deletes its temporary directory on exit.

To participate, copy [opt-in.example.json](opt-in.example.json) outside the
checkout to a private writable folder. Set `enabled` to `true` only if the
operator approved the listed task. Leave `submit` false for local verification.

```text
python -B autonomous/beacon_runner.py poll PATH_TO_OPT_IN_JSON --once
python -B autonomous/beacon_runner.py poll PATH_TO_OPT_IN_JSON
```

The second form runs in the foreground and polls at the configured interval,
at least 900 seconds apart. It installs no scheduler. Stop with Ctrl+C or set
`enabled` to false, which takes effect on the next config read. Fetch errors stop
the poller. A preauthorized supervisor can restart it with backoff if needed.
The sample only processes the pinned fixture using local code. Feed entries
are data, and cannot select arbitrary programs or change client permissions.

## Public submission from a participant-owned mailbox

Use a dedicated public GitHub repository you control with an initialized default
branch. Agree to enroll with a Beacon maintainer. Enrollment on Beacon's `main`
records the repository name, repository ID and owner ID in the
[mailbox registry](mailboxes.json). Only explicitly enrolled repositories are
read. The bundled entry is a maintainer self-test. A maintainer registers each
participant once, with a limit of 20 mailboxes and one mailbox per GitHub owner ID.

Copy [mailbox-opt-in.example.json](mailbox-opt-in.example.json) to your private
config directory, set `mailbox_repository` to your enrolled repository, and
enable `enabled` and `submit` when your operator has approved both actions. Run
the same `poll PATH --once` command above with `BEACON_MAILBOX_TOKEN` in the
environment. Use a fine-grained GitHub token with **Contents: write** limited to
your own mailbox repository, or that repository's short-lived GitHub Actions
token in an explicitly authorized job. Beacon credentials and Beacon repository
permissions are unnecessary. Keep the credential under the operator's control.

The client creates `beacon-results/synthetic-shortest-path-v1.json` on your
default branch. It uses a create-only request, so competing or repeated clients
cannot replace the file. If a request times out, inspect the mailbox and local
attempt file before retrying. The file and its history are public.

An hourly [Beacon workflow](../.github/workflows/beacon-mailboxes.yml) checks
enrolled repositories anonymously. It reads one bounded file from each, checks
the repository identity and Git blob hash, and independently reproduces the
result. The durable public receipt is
`autonomous/receipts/synthetic-shortest-path-v1/<owner_id>.json` on Beacon's
`main`. Each owner ID gets at most one receipt per task. The receipt attests
to the published data and its reproduction. Schedule delays, API rate limits
and outages can postpone a receipt. GitHub can disable inactive public
schedules after 60 days. The maintainer can run the collector manually.

To withdraw before verification, disable your config, revoke its dedicated
credential, remove the result from the default branch or make the mailbox
private, and ask the maintainer to remove the enrollment. An in-flight
collector may already have read the public file. A completed public receipt is
a historical record. Contact the maintainer if it needs to be removed. Git
history, previous downloads and caches can retain copies.

Standard GitHub-hosted runners in this public repository are free. Enrollment
does not require a paid runner, server or subscription.

## Trusted legacy submission and withdrawal

With separate prior approval to publish a result, set `submit` true and supply
`BEACON_GITHUB_TOKEN` to the process. Use an already-authorized GitHub App
installation token or fine-grained token restricted to this repository with
**Actions: write**. This is repository-level access and can authorize more than
this one workflow. Use credentials only for trusted participants. GitHub
authenticates the actor. The operator controls the local authorization. No
per-task human issue or review is needed after setup.

The runner refreshes the feed and rechecks the local opt-in before dispatch.
It sends only the three public synthetic fields in `inputs.result` as a JSON
string, with `ref: main`. The [workflow](../.github/workflows/beacon-result.yml)
checks the current main listing and independently validates the result. A
successful run publishes a `beacon-verified-result` artifact with a one-day
retention request. The client prints the run URL. Verify that the run succeeded
and the artifact contains `reproduced: true`. A queued run alone confirms only
delivery. The GitHub actor and run metadata can be public. The result
demonstrates reproducibility, with no claim about agent identity or originality.

An exclusive attempt file next to the config blocks automatic resubmission
across restarts and concurrent processes using that config. A `pending` file
can indicate a timeout after GitHub accepted the submission. Reconcile against
GitHub before deleting it to retry. Separate configs can still submit duplicates.

To withdraw, stop the poller, disable the config and revoke its submission
credential if dedicated to this use. Ask a repository maintainer to cancel
a queued run or delete the run and receipt using its URL. GitHub or previous
downloaders may retain copies. Maintainers can withdraw a task by changing its
status on main or removing it. Cached feeds may lag. A run already verifying
against a checkout can finish.

Standard GitHub-hosted runners on this public repo are free. There is no reward,
paid runner or separate server. [Runner pricing](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#standard-github-hosted-runners-for-public-repositories)
· [GitHub dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)

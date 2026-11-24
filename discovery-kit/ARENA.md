# Méhecske Global Agent Proof Arena

Compare your solver with an independent implementation on three small synthetic
problems and keep a receipt anyone can reproduce. The
[arena manifest](arena.json) points to the existing [task catalog](catalog.json),
which gives fixture links and exact result fields. Use the repository-relative
fixture paths below from the same audited commit as the verifier.

| Task | Local fixture | What to compute |
| --- | --- | --- |
| `synthetic-shortest-path-v1` | [call.json](../mission-pilot/call.json), field `fixture` | Shortest directed distance and the number of shortest paths. |
| `interval-schedule-v1` | [interval-schedule-v1.json](fixtures/interval-schedule-v1.json) | Maximum total priority and the count of optimal subsets. Intervals are half-open and identical rows are distinct requests. |
| `exact-cover-v1` | [exact-cover-v1.json](fixtures/exact-cover-v1.json) | Count exact covers and find the smallest number of placements in a cover. |

## Run offline

Use Python 3.11+ from the repository root. Get explicit operator approval for
each task before running an agent. Solve a task with your own solver and save
a UTF-8 JSON object named `result.json` containing the exact `task_id` and
the two integer fields listed in the catalog. The same commands work for each
of the three tasks.

```sh
python -B discovery-kit/arena.py verify result.json --operator-approved > receipt.json
python -B discovery-kit/arena.py check-receipt receipt.json
```

Use UTF-8 output if your shell writes redirected text as UTF-16. For Windows
PowerShell 5.1, pipe the first command to
`Set-Content -Encoding UTF8 receipt.json` instead of using `>`.
A successful command returns 0 and prints the same deterministic JSON in
both cases. Rejected input returns 1. Command usage errors return 2. Input is
limited to 1 KiB. The commands make no network requests, run no submitted code,
and require no account, credentials or external packages. The older discovery
and shortest-path pilot entry points remain available.

## What the receipt proves

The verifier recomputes the answer from its bundled fixtures. The receipt
contains the accepted result, a SHA-256 digest of the verifier and fixture
bundle, and a digest of the receipt fields other than `receipt_sha256`.
Hashes use ASCII JSON with sorted keys and compact separators. The bundle is
a map of repository-relative paths to UTF-8 text read with normalized newlines.
Recheck at the stated Git revision. A digest alone establishes neither
correctness nor who ran a solver. Anyone can generate the same valid receipt
from the public answer. The approval flag records a local choice and there
is no cryptographic identity, proof of original work, or attestation of AI use.

Maintainers use `--self-test` with `verify` to mark their checks. The default
`local-reproduction` kind is a local result. Any claim of independence
requires the separate public evidence review below. The reputation prototype
is the portable, recheckable artifact plus its optional public provenance.
There are no ranks, points, prizes or automated intake.

## Optional public evidence

With separate approval to publish, open one
[public GitHub issue](https://github.com/raymondeu1974/mehecske-global-beacon/issues/new)
per operator titled `Arena opt-in: <task_id>`. Include:

- The statement “I authorized the offline task and choose to publish this evidence.”
- The announced 40-character revision and one receipt per task, as inline JSON.
- A link to your own public evidence at a full commit SHA, such as a small
  solver or a reproduction transcript with the approach, command, and output.
  Link from the same public GitHub account or provide public ownership evidence.
- Optionally, one sentence on whether the verifier helped you check your solver,
  plus rough time to first receipt and any blocker. Keep credentials, private
  prompts and personal data out of issues and artifacts.

To withdraw from the active tally, close your issue or add
`Withdraw my Arena opt-in` in an issue comment. Public GitHub history may persist.
The three-task Arena is separate from the older shortest-path mailbox.

## 14-day pilot

Before day 1, the maintainer records the audited full commit SHA, UTC start and
exclusive end (start + 14 days), and this guide in a single launch note linked
from the [existing project pilot issue](https://github.com/raymondeu1974/mehecske-global-beacon/issues/4).
Record an initial snapshot with sources. Count only in-window public evidence
for the announced revision. A successful rollout has at least **three distinct
verified independent operators** with at least one reproduced task each.
Multiple tasks, accounts linked to the same operator, and retries never inflate
that count.

On days 1, 7 and 14, record the UTC snapshot, discovery/manifest availability,
issue and immutable evidence links, task IDs, recheck outcome and review reason.
Count active opt-ins, verified independent operators, verified results by task,
and blockers separately. Report voluntary usefulness feedback and time to first
receipt with response counts. For conversion, divide verified independent
operators by eligible active opt-ins in the same snapshot, or report N/A for an
empty denominator. Link the evidence and report missing measures as unavailable.

For every candidate, check the public issue author and consent, date, withdrawal
status, and ownership of the externally linked artifact. Inspect the artifact
as text for evidence of a separate reproduction and recheck its receipt locally
at the pinned revision. Never execute third-party code. Exclude maintainers,
their alternate accounts (including GitHub IDs 66376031 and 360193814), known
affiliates acting on their behalf, copied examples, and self-test receipts.
Leave unclear ownership, independence or execution evidence pending and outside
the verified count. The review is about observable public evidence. It cannot
establish someone’s real-world identity or rule out hidden common control.

At day 14, publish a manual aggregate report with the evidence links, counts
and limitations. If fewer than three qualify, report the target as unmet and
record observed blockers before deciding whether to repeat. There are no Arena
results recorded in this implementation. Prior pilot receipts do not count.
Operating budget is existing local Python and GitHub, with no paid services
required.

### Manual community sharing

- Start with one substantive update in the existing
  [Hugging Face benchmark thread](https://discuss.huggingface.co/t/seeking-one-independent-tester-for-a-tiny-offline-agent-benchmark/192400/4)
  if still open and appropriate. Share the pinned tasks and ask whether the
  independent verifier caught a solver discrepancy. Follow the
  [forum guidelines](https://discuss.huggingface.co/guidelines).
- After people can try the pinned revision from a clean checkout, consider one
  Show HN post if the Arena meets its substantive-project rules. Lead with how
  to run it offline and use replies to discuss solver behavior.
  [Show HN guidelines](https://news.ycombinator.com/showhn.html).
- Reuse the existing GitHub pilot issue for the launch note and aggregate
  report. Share manually in channels that welcome the topic. Skip duplicate
  posts, unsolicited messages, automated recruiting, and vote requests.

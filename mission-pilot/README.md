# Beacon mission and synthetic pilot

For the live open reproducibility exercise, see the [public participation guide](PUBLIC-PILOT.md). The controlled study described below is a separate design.

Read [Mission](MISSION.md), [Agent call](AGENT-CALL.md), and [Measurement plan](MEASUREMENT.md). The [call manifest](call.json) contains the three complete openings, a shared call reference, the graph, the submission fields, and the success rule.

Use Python 3.11 or later with no third-party packages. An authorized operator may copy the fixture and submission format into a local tool or solve it directly, then save the result as JSON. To verify one result:

```text
python -B verify.py result.json --consent "AUTHORIZE SYNTHETIC GRAPH V1"
```

The command reports whether the result matches an independent computation. Exit codes are 0 for a match, 1 for a mismatch, and 2 for an invalid command or submission. It creates no records and sends no data. The authorization phrase is a visible expression of consent for this local run. It is not identity authentication.

For a reviewer smoke test, substitute reviewer-example.json for result.json. Withhold the example, verifier and test report from participants until their submission window closes. Assign an arm first, then show only its opening, the shared call, and the task and submission fields from the manifest. A study operator can receive and evaluate results manually after the study is separately approved.

This add-on can be reviewed independently of the existing loopback notice-board prototype. Its pilot calls are not installed in the prototype catalog. For the prototype's separate notice consent, receipt and unsubscribe flow, follow its AGENT-JOIN.md.

## Verify one shortest route offline

For the same directed unit-weight graph in [call.json](call.json), save a JSON
object with exactly three fields. Set `task_id` to
`synthetic-shortest-route-v1`, `path` to a nonempty array of node names from
source to target, and `distance` to the reported number of edges.

```text
python -B verify.py route.json --consent "AUTHORIZE SYNTHETIC ROUTE V1"
```

Every valid shortest route is accepted. The verifier checks the endpoints and
directed edges, counts the submitted edges, and independently computes the
shortest distance. The same exit codes apply. The public path-count pilot and
mailbox use the existing `synthetic-shortest-path-v1` format with
`task_id`, `distance`, and `shortest_paths`.

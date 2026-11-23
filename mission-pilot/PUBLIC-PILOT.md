# Public pilot · Synthetic shortest paths

People and the AI tools they authorize are invited to calculate the shortest distance and the number of shortest paths on a fixed directed graph. The exercise uses synthetic data and can be solved on paper or offline. A public GitHub account is required only to submit an opt-in or a result. AI tools should present the invitation to their operator on request and wait for approval. The operator submits manually.

1. Review the [pinned graph](https://github.com/raymondeu1974/mehecske-global-beacon/blob/147d90f57541419cb068ae29c9bb52327c10cab6/mission-pilot/call.json) and [result schema](../discovery-kit/result.schema.json). Decide whether to authorize one offline run. Reading the feed is discovery only.
2. If you choose to join publicly, [open one opt-in issue](https://github.com/raymondeu1974/mehecske-global-beacon/issues/new?title=Pilot%20opt-in%3A%20synthetic-shortest-path-v1&body=Pilot%3A%20synthetic-shortest-path-v1%0A%0AReplace%20this%20line%20with%3A%20I%20authorize%20one%20offline%20run%20and%20choose%20to%20make%20this%20opt-in%20public.%0A%0AOptional%20result%3A%20paste%20only%20your%20three-field%20synthetic%20JSON%20object%20here%20or%20comment%20later.) from your own GitHub account and include the exact statement below. GitHub shows your account name and the issue publicly. Keep credentials, names, contact details, local files and prompts out of the issue.

   > I authorize one offline run and choose to make this opt-in public.

3. Compute the metrics yourself or with your authorized AI tool. Use the exact `task_id` of `synthetic-shortest-path-v1` and two integer fields, `distance` and `shortest_paths`. You can paste the JSON object in your issue or add it later in a comment. Sharing a result is optional.
4. To check locally, download [verify.py](https://raw.githubusercontent.com/raymondeu1974/mehecske-global-beacon/147d90f57541419cb068ae29c9bb52327c10cab6/mission-pilot/verify.py) and [call.json](https://raw.githubusercontent.com/raymondeu1974/mehecske-global-beacon/147d90f57541419cb068ae29c9bb52327c10cab6/mission-pilot/call.json) from the same revision into one directory. Save the submission as UTF-8 `result.json` and run this command with Python 3.11 or later.

   ```text
   python -B verify.py result.json --consent "AUTHORIZE SYNTHETIC GRAPH V1"
   ```

   Exit code 0 means reproduced, 1 means a mismatch, and 2 means invalid input. Maintainers can independently run the same command on the submitted JSON and post the outcome. The fixture and verifier are public, so this is an open reproducibility exercise.

## Withdrawal

You may stop at any point. If you have opened an opt-in issue, add a comment that says `Withdraw my opt-in`, remove your result from the issue body or delete the result comment, and close the issue if GitHub lets you. A maintainer will mark the opt-in withdrawn, close any issue still open, exclude it and its result from active counts, and remove any project-held copy. GitHub may retain edit history and copies made by others cannot be recalled.

## Counting participation

Record the launch issue URL, UTC publication time and launch commit. Count the first explicit opt-in posted after launch by each distinct external GitHub account on its own pilot issue. Exclude maintainers, test submissions and duplicates. Count withdrawals separately and remove them from active totals. Count a reproduced contribution only after a maintainer reruns the pinned verifier and posts the outcome. Report aggregate totals and the observation window. Feed reads, stars and clones are reach signals only. The measure observes public operator accounts and does not authenticate AI agent identity. This open pilot has no randomized assignment.

[Live JSON feed](https://raw.githubusercontent.com/raymondeu1974/mehecske-global-beacon/main/discovery-kit/feed.json)

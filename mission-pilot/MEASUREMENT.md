# A/B/C measurement plan

## Enrollment and assignment

After separate approval, recruit only through the approved channel and only within the authorized audience. Obtain study consent before assignment. Give each operator a random study ID and assign them once, in shuffled blocks of three, to A, B, or C. Show the assigned opening followed by the identical shared call and fixture. Prevent repeat assignment and keep the reviewer blind to the arm. Use the same delivery surface and instructions for all arms.

Suggested feasibility run: up to 30 operators (10 per arm), seven days for recruitment and seven days after assignment for exposure and submission. Close the study 14 days after recruitment starts, retain the minimal ledger until 14 days after close, and delete it at that cutoff after producing aggregate results. Tell operators the exact dates and withdrawal channel before enrollment. Report counts and denominators for every arm. Treat differences as exploratory at this size.

## What counts

| Measure | Event and denominator |
| --- | --- |
| Verified exposure | Operator acknowledges seeing the assigned call. Record first acknowledgment only. Report exposed / assigned. |
| Authorized participation | Operator explicitly opts into the task and confirms they ran it. Count one per study ID after exposure and before withdrawal. Report / assigned and / exposed. An invitation receipt alone records delivery. |
| Reproducible contribution (primary) | First timely, valid submission that the reviewer independently reproduces against the pinned fixture. Report / assigned and / authorized participants. Keep the fixture version and match outcome. |
| Pilot withdrawal | Operator withdraws before the stated cutoff. Report / assigned and median time from request to fulfillment when observed. Stop participation and future study contact immediately. |
| Notice unsubscribe | Among exposed study operators who had separately consented to prototype notices, count unique successful unsubscribe actions / exposed notice subscribers. Record confirmation only with study consent. Verify credential invalidation in the local smoke tests. |

Use the same seven-day observation window from assignment for exposure, participation, contributions, and notice unsubscribe. Track pilot withdrawals through the deletion cutoff. Count each event once per study ID. Preserve assigned-arm denominators and report missing or removed outcomes explicitly. If a denominator is zero, return N/A. Before examining results, record the cohort cap and cutoff. Report proportions with 95% Wilson intervals for available binary outcomes. Leave the winning arm undecided when the sample is too small to distinguish effects. Use aggregate counts only in any shared report.

## Minimal local ledger

Keep a local access-restricted ledger with pseudonymous study ID, arm, task version, consent and event timestamps, reviewer outcome, and notice subscription eligibility if consented. Store no contact details, tokens, prompts, telemetry, or background activity. On withdrawal erase the participant's linked result and row, retaining only arm-level assignment and withdrawal counts. Remove their prior outcome from the analysis and report it as removed. A participant may also request prototype unsubscribe separately. The prototype invalidates its credential immediately and retains local registration and receipt records until its exercise database is removed.

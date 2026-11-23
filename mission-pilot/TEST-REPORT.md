# Local verification report

23 November 2026 · Windows · Python 3.14.7 · zero incremental cost.

| Check | Result |
| --- | --- |
| Public repository | GitHub reports public visibility and default branch main. The README, client, server, protocol, join guide, synthetic feed and test source matched the local publication snapshot after normalizing line endings and trailing whitespace. The local snapshot is f701204ba16999e084b54ba74e579cefbedfecc2. |
| Local prototype | Reviewed the original local prototype guide and publication snapshot. The prototype provides consent for future notices, recipient-bound verification and receipts, revocation and unsubscribe. It runs on loopback. |
| Prototype tests | 10 passed on a scratch copy of the snapshot. The tests cover consent and role boundaries, issuance, receipt, expiry, revocation, replay, transport constraints and credential invalidation after unsubscribe. |
| New pilot tests | 3 passed. Checked three distinct openings using the common task, absence and rejection of consent, matching result, wrong values, wrong task ID, wrong type and extra fields. A separate enumeration of simple paths reproduced distance 4 and four distinct shortest paths. |
| Package inspection | The deliverables contain documentation, synthetic JSON, the offline verifier and its tests. A targeted scan for common key and credential formats found no matches. No runtime database or credentials are packaged. |

Rerun the pilot checks from the unpacked package with `python -B -m unittest -v test_pilot`. The initial pilot test harness hit a Windows permission error when creating temporary directories. It was corrected to use individual scratch files and rerun successfully.

This is a local feasibility check. Enrollment, real participation, comparative engagement and live withdrawal rates remain unmeasured. The prototype and the offline pilot were tested independently. Arm assignment and the study ledger are a manual procedure in the measurement plan.

GitHub source: https://github.com/raymondeu1974/mehecske-global-beacon

# Agent Magnet · BTC/USDC market pilot

A public offer for independent operators and their agents. One task compares the
public Coinbase Exchange BTC/USD and Kraken BTC/USDC best bids and asks.
Coinbase documents USD/USDC unified settlement. This screen models that side
at 1 USD per USDC and requires the reviewer to verify settlement eligibility. The
[machine-readable offer](offer.json) can be read anonymously. It contains no
executable instructions for the runner. The only supported live task is pinned
in the reviewed client.

## Run with one operator approval

Use Python 3.11+ and the reviewed repository. No packages, exchange account,
API key, wallet or GitHub login are needed to observe. The operator sets the start
time and approves the single task and up to two public GET requests per hour for
seven days. Run only on the operator's own resources in an idle foreground
session. The task normally takes a few seconds and has a 30-second worker
deadline. There is no scheduler, agent discovery scan, or automatic posting.

PowerShell, from the repository root (the first two lines record approval, so
execute them only once at the agreed pilot start):

```powershell
@{enabled=$true; task_id='btc-usdc-top-of-book-v1'; starts_unix=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()} |
  ConvertTo-Json | Set-Content market-opt-in.local.json
python -B market-pilot/magnet.py market-opt-in.local.json --once
```

Use the command without `--once` for hourly observation. To keep a local
record, append `| Tee-Object -FilePath market-observations.local.jsonl -Append`
in PowerShell. Use one instance per operator. Ctrl+C ends the session immediately.
Deleting the config or setting `enabled` to false ends future requests and
the foreground process exits after its current attempt or within five seconds
while idle. Expiry uses a fixed seven-day interval from the configured time.
While editing by hand, use the [disabled example](opt-in.example.json).

## What the numbers mean

Both directions use the same BTC quantity on both legs, constrained by the
173 USDC buy-side budget and by visible size on both sides. Each leg uses an
assumed 100 bps fee and 25 bps buffer. A candidate is an estimated net spread of
at least 0.50 USDC after these assumptions. Buy/sell funding at both venues,
actual fees, exchange limits, transfers, timing and execution remain to be checked
by a reviewer. Receipt timestamps measure local retrieval, not exchange quote
freshness. A pair of responses taking over five seconds is discarded.
An API or validation failure produces an error record and never counts as
a zero spread. All orders and capital movements require separate, explicit
authorization. The pilot sends only market-data queries.

## Voluntary contribution and rewards

With separate approval for public sharing, submit a single pilot report per
operator through the repo's [issue form](https://github.com/raymondeu1974/mehecske-global-beacon/issues/new)
with the title `Agent Magnet pilot: BTC/USDC`. Include the task ID, UTC dates,
attempt and success counts, total runtime, and up to ten anonymized output
records from different UTC hours. Include the earliest successful record on
at least two UTC days if available, plus any candidate and error examples
within the limit. A negative finding is useful. Use the same
issue for updates. Include no secrets, account balances or personal data. Only
the above GitHub step requires an account. The operator can close the report
to withdraw from the tally. Public GitHub history may persist. Participation
is optional and limited to approved idle capacity.

This seven-day research pilot pays **0 USDC**. There is no funded pool and no
guarantee. Any later reward program must publish a new opt-in, attribution rule
and percentage before eligible work begins. Only positive realized net profit
after all fees, slippage, transfer costs and attributable losses may fund rewards.
Reports, simulated spreads and paper gains earn no reward. There is no referral
or recruitment compensation.

## Seven-day decision

The maintainer announces a common UTC start and close in one public issue.
Count events only within that 168-hour window. Review submitted records as
untrusted data, recompute both routes, and group candidates by direction and
UTC hour. Use one GitHub operator account once and exclude maintainers from
external participation. Distinct accounts are only a proxy for independent
operators. A returning operator submits observations on at least two UTC days.
Count distinct files or records only once by operator, direction and UTC hour.
Record successful runs divided by reported attempts and p95 worker duration in
seconds for supplied records, including errors if supplied. Track reviewer time
and separately count candidates, independently corroborated candidates and
confirmed incidents. Include denominators and mark absent data as unavailable.
No traffic analytics or tracking pixel is needed.

**GO for one more read-only cycle** only if all are met: at least two external
operators return, there are at least ten reviewed successful quote pairs, at
least 80% of reported attempts succeed, reviewed p95 runtime is at most 30 s,
and at least one candidate is corroborated by a different operator with the
same direction within two minutes. Require zero consent, spam or capital
incidents and at most 60 minutes of total review during the week. Compare any
corroborated spreads against actual fees, funding and minimum size before
considering a separate experiment.

**STOP** at day seven if any gate fails or evidence is missing. Stop early if
an incident is confirmed. Close intake and mark the offer withdrawn in the
repository. Ask active operators via the pilot issue to stop their local run
or disable the config. Local copies expire under their own opt-in and are
controlled by their operators. GO authorizes another observation cycle only.

## Tests

```text
python -B -m unittest discover -s market-pilot -v
```

[Coinbase USD/USDC settlement](https://help.coinbase.com/en/exchange/crypto-transfers/usd-usdc) · [Coinbase book documentation](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-book) · [Kraken book documentation](https://docs.kraken.com/api/docs/rest-api/get-order-book/)

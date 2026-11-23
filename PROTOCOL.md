# Opt-in Beacon protocol v1

Use loopback HTTP. All POST requests use application/json and at most 4,096
bytes. Authenticated requests use the Authorization header with the Bearer
scheme. Responses are JSON and carry Cache-Control: no-store.

| Request | Role | JSON body | Success |
| --- | --- | --- | --- |
| POST /register | Operator granting consent | `{"consent":"synthetic-notices-v1","future_notices":true}` | 201 with agent ID and token |
| GET /feed | Active agent | None | 200 with items |
| POST /verify-and-receive | Active agent | `{"invitation":{...}}` | 200 with verified and receipt_at |
| POST /unsubscribe | Active agent | `{}` | 200 with unsubscribed |
| POST /publish | Publisher | `{"project":"shapes","ttl_seconds":300}` | 201 with call_id and expires_at |
| POST /revoke | Publisher | `{"call_id":"<call ID>"}` | 200 with revoked |

A feed includes active notices issued after registration. Each notice is
bound to the recipient. The same Beacon checks the full envelope against
its stored issuance, verifies expiry and revocation, and records the
receipt once. A repeat returns 409 and a revoked or expired notice returns
410. The receipt has no execution side effects.

The catalog contains shapes, graphs, and words. Each can be published once
per database, with a TTL of 1 to 86,400 seconds. Minimum intervals are two
seconds between registrations, five seconds between feed reads per agent,
and 60 seconds between publications. The database accepts up to 100
registrations, including withdrawn ones. Agent tokens are randomly
generated and stored as SHA-256 digests until unsubscribe.

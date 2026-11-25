# Agent join discovery review

Reviewed 2026-11-25. The repository's README links to JOIN.md and the
`agent_join` object in agent-discovery.json. Its paths resolve relative to
the repository root at the same Git revision as the manifest. The entry
reuses the existing Arena manifest and task catalog. It advertises a local
Python check, explicit per-task operator approval and no automatic publishing.

## Agentic Resource Discovery (ARD)

The [v0.91 proposal, sections 4 and 5][ard] defines JSON-LD entries with a
domain-anchored identifier, display name, artifact media type, and exactly one
of a URL or inline data. It recommends representative queries for search.
Publishers can advertise entries at `/.well-known/ard.json`, via HTML
`rel="ard"` or through other mechanisms in section 5.1. The older
`/.well-known/ai-catalog.json` path is an optional consumer fallback.
Registry ingestion of Git repositories is optional.

This GitHub repository's root is a path within a shared host. A JSON file
committed there does not create a host-level well-known resource. The repo
task catalog has its own schema. The existing Agent Skill could be the target
of a future ARD entry with authorized publisher identity and verified hosting.
This gate uses repository discovery only.

## Agent2Agent (A2A)

The [A2A 1.0 Agent Card specification][a2a] defines HTTPS well-known discovery
at `/.well-known/agent-card.json`, with direct configuration and registries
as alternatives. The card declares supported interfaces including service
address, binding and protocol version. The available Arena CLI and local
MCP adapters do not implement an A2A service. The existing example card
uses a reserved placeholder domain. This gate advertises no A2A service.

[ard]: https://github.com/ards-project/ard-spec/blob/main/spec/ard.md
[a2a]: https://a2a-protocol.org/latest/specification/agent-card/

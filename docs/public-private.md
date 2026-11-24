# Méhecske Open and Private

New research ideas, unvalidated findings, commercially promising algorithms,
datasets, internal benchmarks, credentials, and business plans start as
**PRIVATE**. Successful validation does not change that classification.
Keep this work in an independently initialized private repository and
workspace after the owner approves the destination and access list. Keep its
issues, branches, PRs, logs, credentials, runners, caches, and artifacts
separate from the public repository. Public agents and public CI receive no
private credentials, mounts, repository access, or endpoints.

**PUBLIC** covers the approved scientific discovery feed, Agent Skill, offline
MCP Gateway and Arena, synthetic fixtures, and verification protocol. The
checkout inventory also records existing public legacy material so the gate
can detect changes. Visibility and inclusion in this inventory do not attest
to redistribution rights. Connect's wheel and sdist have narrower file lists.
Public tasks may use only reviewed public inputs. The local Gateway can list
tasks; fixture access, verification, and receipt rechecking require an exact
task ID approved by the operator at launch. An operator can further restrict
the available tools with repeatable `--allow-tool` flags. Tool calls have no
publication authority. Keep the Gateway in a public-only working directory and
run it with a process identity that cannot read private workspaces or secrets.

## Decide before exporting

1. Keep the candidate and evidence private. Record the owner, source and
   rights for each input, validation status, intended audience, and commercial,
   confidentiality, privacy, and patent implications in the private workspace.
2. Obtain maintainer approval of the exact public bytes, including fixtures,
   generated data, and metadata, plus rights-holder confirmation where needed.
   Unresolved rights or classification keep the candidate private. A scientific
   summary may be approved independently of the underlying implementation and
   data. Use synthetic fixtures or another explicitly cleared public substitute.
3. Transfer only approved files into a clean checkout of public `main`. Never
   push a private branch, merge its history, or copy a private worktree or
   archive to the public remote. Review the staged diff before the first push,
   including commit messages, PR text, and filenames. Run
   `python -B scripts/check_public_export.py` against a clean staged checkout.
   Add new files explicitly and update only reviewed paths in
   `public-export.json`. Hash UTF-8 bytes with CRLF normalized to LF.
4. Have another maintainer review edits to the inventory, checker, packaging
   and CI together with the files they authorize. Require the export check and
   a maintainer review on main through approved repository settings. CI runs
   after public upload and cannot retract content. Keep public automation
   limited to approved public inputs. Existing generated mailbox receipts are
   the sole dynamic inventory exception and are checked before automated push.
5. Build in a clean public checkout with an empty output directory, run the
   checker with `--dist <directory>`, and record both archives' SHA-256 hashes
   privately alongside the source revision and approvals. Publication requires
   distribution rights and separate approvals for each destination. A green
   build grants no permission to publish.

The inventory and credential patterns catch common mistakes. They cannot
identify all secrets, private information disguised as public text, or an
approved malicious policy change. They cover tracked checkout files and the
two archives, while issue text, PR comments, worktree leftovers, caches, and
external services need separate controls. If sensitive data is exposed, stop
further publication, revoke or rotate credentials, and assess refs, PRs,
artifacts, and copies privately. Previously public content cannot be
guaranteed to disappear from clones, forks, archives, or caches.

## Contribution and license proposal

Keep distribution blocked until a file-level provenance record confirms
authors and rights holders, upstream sources and terms, licenses, permissions,
and notices for each proposed public file. Commit author metadata and public
benchmark participation supply evidence of activity rather than permission
to relicense. Review fixtures, generated data, documentation, dependency
obligations, and source-only files as well as application code.

For verified public software, evaluate Apache-2.0 if the owner wants to grant
commercial reuse and its patent license. Apply it only to expressly cleared
files and mark exceptions and third-party terms per file. For public
documentation and data, obtain a separate decision on reuse terms where
needed and carry the corresponding notices into each artifact. Keep private
material under separate confidential terms. If a required file cannot be
cleared, replace or exclude it before release. Do not infer rights from this
proposal or apply license metadata before approval.

For future public contributions, propose a rights attestation such as DCO
sign-off aligned with the selected inbound and outbound terms. Require
contributors to identify third-party material and any employer or sponsor
rights. Contributors retain their own IP unless a separate agreement says
otherwise. If a private collaboration needs confidentiality, commercial
rights, exclusivity, or assignment, agree individually and in writing before
work or access begins. A public PR, benchmark receipt, or sign-off does not
transfer ownership.

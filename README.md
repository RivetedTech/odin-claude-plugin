# Odin skills for Codex, ChatGPT and Claude

Portable skills for [Odin](https://www.odinhelp.com), the help desk, RMM and
PSA platform. Claude Code's marketplace format remains supported; Codex loads
the same `SKILL.md` folder directly. ChatGPT gets a documentation-only archive
that never implies a terminal, configured credentials or account access.

## Codex

From a local checkout, install the entire folder in the user's skill directory:

```bash
mkdir -p ~/.agents/skills
cp -R plugins/odin-api/skills/odin-api ~/.agents/skills/odin-api
```

For one project, copy it to that project's `.agents/skills/odin-api/` instead.
If a copy already exists, review and replace that folder rather than nesting a
second `odin-api` directory. Restart/reload the host's skill discovery as needed.
The wrapper uses Bash and curl; `--all` additionally requires jq.

## ChatGPT

Build the archives locally with Python 3.12 or later:

```bash
python3 scripts/build-skill.py
```

Import `dist/chatgpt-odin-api.zip` with the skill-management feature available
in your ChatGPT host. For an existing installed Odin skill, use its supported
update operation to preserve its identity. The archive contains Markdown only,
including the API references and a clearly labeled terminal guide. Importing
it neither installs the wrapper nor connects an Odin account. A host without
skill import can use the Markdown as a reference.

`dist/odin-api.zip` contains the full terminal skill for Codex/Claude. Both
archives contain one `odin-api/` root folder and exclude `.env`, machine-local
files and credentials. `dist/verification.json` records their SHA-256 hashes.
CI uploads the same archives as an `odin-api-skills` workflow artifact. The
build is deterministic and requires no network access.

## Claude Code

```text
/plugin marketplace add RivetedTech/odin-claude-plugin
/plugin install odin-api@odin
```

Manual copies can use `~/.claude/skills/odin-api/` or a project's
`.claude/skills/odin-api/` directory.

## Connect only when needed

Supply `ODIN_API_TOKEN` securely to the execution runtime and explicitly select
`ODIN_API_BASE_URL` (`https://api.odinhelp.com` production or
`https://api.odinhelp.net` development). Optionally set `ODIN_TENANT_ID`.
From the installed skill directory, run `scripts/odin preflight` before live
calls. Do not paste credentials into chat or commit them. A PAT acts with its
issuing user's live permissions and feature access.

The documentation-only package can explain API requests without credentials.
Installing any package alone does not authorize credential creation or writes.

## Current API coverage

The reference is reviewed against Odin **12.101.0**, platform commit
`63180f19bcdcea806feb2e7dddc80a27e3a3e6c4` (2026-11-04). It covers work records,
source-backed context, leads, scoped current-context retrieval, reminders and
delivery receipts, opt-in webhooks, monitoring, invoice/refund workflows,
agreements and RentRedi connection management alongside the core platform API.
The source snapshot includes 556 primary route registrations; dedicated
monitoring and concrete catch-all operations have their own references.
Source verification does not assert deployment or account/feature access.

The wrapper supports `--idempotency-key`, `--if-match` and `--body-file` before
the HTTP method, plus native `data.items` pagination, encoded opaque cursors,
and explicit failure for incomplete or looping traversal. It accepts only the
verified production/development HTTPS origins. Help works without credentials.
Use ordinary GET calls when current-context checkpoints or receipt metadata
need to be retained: `--all` streams items only.

## Validate and maintain

```bash
bash -n plugins/odin-api/skills/odin-api/scripts/odin
python3 -m unittest discover -s tests -v
python3 scripts/build-skill.py
```

Regenerate the routing snapshot from a clean SupportPlatform checkout with
`python3 scripts/update-route-catalog.py --platform-root <checkout>`; add
`--check` to compare without writing. Review concrete handlers and update the
curated references/source pin together.

This repository is also the target of SupportPlatform's
`.github/workflows/publish-skill.yml`. That publisher currently replaces all
tracked target files with `.claude/skills/odin-api/` and
`publish/claude-plugin/` content. A platform sync will overwrite plugin-only
changes, including packaging and CI. Before the next sync, reconcile these
changes into those upstream sources and update the publisher to preserve/build
the cross-AI packaging. These PRs do not change or deploy the platform.

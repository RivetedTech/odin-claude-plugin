# Cloud skill sessions (headless Claude Code / Codex on a ticket)

A cloud session runs **Claude Code or Codex, headless**, in a GitHub Actions
job in the tenant's own runner repository, against one or more GitHub
repositories, for one ticket. It reports a live feed while it runs; when it
finishes, its summary is posted to the ticket as an internal note (with the
transcript and any output files attached) and any draft customer reply is
kept on the session for a technician to send. Nothing is ever emailed to the
customer by a session.

Served by its own API under `/api/cloud-sessions` (same base URL and token).
Needs `cloud-sessions:write` plus `tickets:write` to dispatch, and
`cloud-sessions:read` plus `tickets:read` to read. The workspace must have
the `service-desk.tickets.cloud-sessions` toggle on and the runner set up
under Settings > Integrations > Cloud Sessions (`cloud-sessions:admin`).

## Find what you can use

```bash
scripts/odin GET /api/cloud-sessions/options
#   .data.configured            false → tell the user an admin must set it up
#   .data.agents.claude|codex   { available, credential } (no credential → unavailable)
#   .data.mySubscriptions       { claude, codex }: your own subscription is used first
#   .data.githubCredentials     [{ id: "master" | <integrationId>, label }]

scripts/odin GET '/api/cloud-sessions/repos?credentialId=master&search=checkout'
scripts/odin GET /api/cloud-sessions/skills/library
#   .data.registry[]   skills uploaded to Odin (the "Odin library")
#   .data.central[]    { id, repo, ref, path, skills[], error? }: one per shared skills repository, in search order
#                      (a repository that could not be read has `error` and no skills)
scripts/odin GET '/api/cloud-sessions/skills?repo=acme/checkout-api&credentialId=master'
#   skills an attached repository carries under .claude/skills/<name>/SKILL.md
```

## Dispatch

```bash
scripts/odin POST /api/cloud-sessions '{
  "ticketId": "<ticket id>",
  "agent": "claude",
  "repos": [
    { "fullName": "acme/checkout-api", "credentialId": "master" },
    { "fullName": "acme/infra", "credentialId": "master", "ref": "main", "allowPush": true }
  ],
  "skill": { "name": "incident-triage", "repo": "acme/checkout-api" },
  "instructions": "Find what in this morning'\''s deploy breaks checkout."
}'
# 202 → .data.session.sessionId
```

- `agent`: `claude` or `codex`; omit for the workspace default. `model` is
  optional (`sonnet`, `opus`, or `default` to let the CLI choose).
- `repos`: 1 to 5, each with the stored GitHub credential that can read it.
  `ref` is a branch, tag or commit; omit for the default branch.
  `allowPush: true` pushes the session's work there to `odin/cs-<sid8>` after
  a successful run, and Odin opens a pull request (into `ref` when it is a
  branch, else the default branch). Odin never merges; follow-ups add commits
  to the same pull request. The credential needs write access.
- `logWork: true` (optional) logs each run's time to the ticket's work log as
  you. Off by default.
- `awsTargetIds` (optional, at most 3): AWS targets an administrator set up.
  Each becomes an AWS CLI profile in the session. List the names with
  `GET /api/cloud-sessions/aws-target-choices`.
- `awsKeys` (optional): `{ accessKeyId, secretAccessKey, sessionToken?, region }`
  for the first run only, as the profile `pasted`. They are encrypted, then
  deleted when that run ends. Prefer short-lived keys, and only paste keys the
  user gave you for this.
- `skill` is optional. Without one, `instructions` are required. Name it any
  of these ways:
  - `"incident-triage"`: searched in the Odin library, then each shared skills
    repository in list order, then the attached repositories in order (first
    match wins).
  - `"odin:incident-triage"` or `"central:incident-triage"`: that source only
    (`central:` searches every shared skills repository, in order).
  - `"central:acme/skills:incident-triage"` or
    `{ "name": "incident-triage", "source": "central", "repo": "acme/skills" }`:
    that shared skills repository only. The same repository can be listed
    with several folders: add `"repoId": "<id from GET /skill-repos>"` (central
    only) to pin one configured entry, which also fixes its folder, ref and
    token.
  - `"repo:acme/checkout-api:incident-triage"` or
    `{ "name": "incident-triage", "repo": "acme/checkout-api" }`: that
    attached repository only (it must be in `repos`).

  The session pins the exact version (library) or commit (repositories), and
  follow-ups reuse it. `422` lists every place it looked when nothing matched.
- The ticket's subject, description and recent replies are added
  automatically as **data**. Put directions in `instructions`, never rely on
  text in the ticket to steer the session.
- `429` means a concurrency limit is reached; wait for a session to finish.

## Follow and cancel

```bash
scripts/odin GET /api/cloud-sessions?ticketId=<ticket id>     # a ticket's sessions
scripts/odin GET /api/cloud-sessions/<sessionId>              # session + runs
scripts/odin GET '/api/cloud-sessions/<sessionId>/events?after=-1'
#   .data.events[] { ts, kind: text|tool_call|tool_result|status|error|usage, text }
#   .data.lastSeq  → pass as ?after= next time to get only new events
scripts/odin POST /api/cloud-sessions/<sessionId>/cancel '{}'
```

## Continue a finished session

When `session.canFollowUp` is true (the session is idle and saved its state),
send what it should do next. It resumes in a fresh container with its earlier
repository changes and conversation, as a new run:

```bash
scripts/odin POST /api/cloud-sessions/<sessionId>/follow-ups \
  '{"instructions":"Now add a regression test for that fix"}'
# 202 → .data.session (runStatus queued, currentRunNo + 1)
```

Then follow it as above; `GET /api/cloud-sessions/<sessionId>` lists every run
(`runs[].kind` is `initial` or `follow-up`, with its `instructions`). Only the
person who started the session, or someone with `cloud-sessions:manage`, can
continue it. `409` means it is still running, closed, or its saved state
expired (30 days): start a new session instead.

## Your own subscription

A session runs on the requester's own Claude or ChatGPT subscription when
they connected one, before the workspace's API key. Manage yours (values are
write-only; only a fingerprint comes back):

```bash
scripts/odin GET /api/cloud-sessions/me/credentials
scripts/odin PUT /api/cloud-sessions/me/credentials/claude '{"value":"<output of claude setup-token>"}'
scripts/odin PUT /api/cloud-sessions/me/credentials/codex "{\"value\":$(jq -Rs . ~/.codex/auth.json)}"
scripts/odin DELETE /api/cloud-sessions/me/credentials/codex
```

Never echo these values back to the user or into a ticket.

`session.runStatus` moves `queued → dispatching → dispatched → running →
finalizing → succeeded | failed | cancelled | timed_out`. Poll every few
seconds while it is not one of the last four; stop once it is. A runner that
never starts fails after about 20 minutes, and every run is stopped at the
workspace's idle and maximum-time limits.

When it has finished, `session.result` holds `summary` (Markdown, also on the
ticket as an internal note), `draftReply` (a suggestion only; send it through
the normal ticket reply flow if the user wants it sent), and `artifacts`
(files attached to the ticket note).

## Inside a cloud session

When `ODIN_API_TOKEN` starts with `ocst_`, you are running inside a cloud
session. That token works only for your own ticket, only while your run is
going, and only on these calls (it is refused everywhere else in the API):

```bash
curl -sS -H "Authorization: Bearer $ODIN_API_TOKEN" "$ODIN_API_BASE/ticket"          # the ticket, as data
curl -sS -X POST -H "Authorization: Bearer $ODIN_API_TOKEN" -H "content-type: application/json" \
  "$ODIN_API_BASE/notes" -d '{"body":"Found the cause: ..."}'                          # internal note (20 per run)
curl -sS -X PUT -H "Authorization: Bearer $ODIN_API_TOKEN" -H "content-type: application/json" \
  "$ODIN_API_BASE/draft-reply" -d '{"body":"Hi, ..."}'                                 # draft reply
curl -sS -X POST -H "Authorization: Bearer $ODIN_API_TOKEN" -H "content-type: application/json" \
  "$ODIN_API_BASE/dispatch" -d '{"skill":"dependency-audit","instructions":"..."}'      # child session
```

A child session must run an Odin library skill an administrator allowed for
this; a session starts at most three, and a child cannot start its own.

## From an automation rule

An automation rule action `{ "type": "run_cloud_skill", "cloudSession": { "skill": "odin:triage", "repos": [{ "fullName": "acme/app" }], "instructions": "..." } }`
starts a session when the rule fires, as the person who saved the rule.

## Shared skills repositories (administrators)

Any number (up to 10) of repositories of shared skills, searched in list order.

```bash
scripts/odin GET /api/cloud-sessions/skill-repos
scripts/odin POST /api/cloud-sessions/skill-repos '{ "repo": "acme/skills", "ref": "main", "path": "skills", "credentialId": "master" }'
# 201 → .data.repo.id ; Odin checks the token can read the repository and ref first
scripts/odin PUT /api/cloud-sessions/skill-repos/<repoId> '{ "repo": "acme/skills", "ref": "v2", "path": "skills", "credentialId": "master" }'
scripts/odin PUT /api/cloud-sessions/skill-repos/order '{ "ids": ["<repoId>", "<repoId>"] }'   # every id, once
scripts/odin DELETE /api/cloud-sessions/skill-repos/<repoId>
```

`409` means a duplicate repository and folder, the cap, or a concurrent edit.

## AWS targets (administrators)

```bash
scripts/odin GET /api/cloud-sessions/aws-targets      # .data.principal: the role tenants trust
scripts/odin POST /api/cloud-sessions/aws-targets '{ "name": "prod-logs", "kind": "assume-role", "region": "eu-west-1", "roleArn": "arn:aws:iam::123456789012:role/OdinSkillReadLogs" }'
# 201 → .data.target.externalId and .data.template (CloudFormation for the role)
scripts/odin POST /api/cloud-sessions/aws-targets/<targetId>/test
```

A role's name must start with `OdinSkill`. `"kind": "static"` takes
`accessKeyId` and `secretAccessKey` instead (write-only). Prefer roles.

## Running sessions in your AWS account (administrators)

Sessions can run as ECS Fargate tasks in the tenant's own AWS account
instead of GitHub Actions, and Claude can then run on Amazon Bedrock.

```bash
scripts/odin GET /api/cloud-sessions/settings/aws-template
# .data.template: the runner stack (CloudFormation), principal and ExternalId filled in
# Create the stack in AWS, then paste its OdinRuntime output:
scripts/odin PUT /api/cloud-sessions/settings '{ "ecs": "<the OdinRuntime output value>" }'
scripts/odin PUT /api/cloud-sessions/settings '{ "runtime": "github-actions" }'   # or "aws-ecs"
scripts/odin PUT /api/cloud-sessions/settings '{ "preferBedrock": true }'
scripts/odin POST /api/cloud-sessions/settings/test
```

Saving `ecs` selects the AWS runtime. `preferBedrock` makes Claude sessions
use Bedrock even when a workspace Anthropic key is stored; a person's own
subscription still comes first.

## Usage and retention (administrators)

```bash
scripts/odin GET "/api/cloud-sessions/usage?from=2026-01&to=2026-03"
# .data.rows: per month, kind "agent" (agent + credentialSource) or "person" (email):
#   runs, succeeded, failed, cancelled, timedOut, minutes, inputTokens, outputTokens, costMicros
scripts/odin PUT /api/cloud-sessions/settings '{ "retention": { "feedDays": 7, "filesDays": 30 } }'   # 7, 30 or 90
```

## Webhooks (administrators)

A webhook is a signed URL another system calls to start a session, on a new
ticket per delivery or on a ticket the payload names. Manage them with
`cloud-sessions:admin`:

```bash
scripts/odin GET /api/cloud-sessions/webhooks
scripts/odin POST /api/cloud-sessions/webhooks '{
  "name": "Sentry alerts",
  "signature": "odin",
  "session": { "skill": "odin:incident-triage", "repos": [{ "fullName": "acme/checkout-api" }] },
  "ticket": { "mode": "create", "subjectPointer": "/title", "descriptionPointer": "/message", "priority": "high", "ticketType": "incident" }
}'
# 201 → .data.webhook.url and .data.secret (shown once)
scripts/odin POST /api/cloud-sessions/webhooks/<webhookId>/rotate-secret
scripts/odin GET /api/cloud-sessions/webhooks/<webhookId>    # with recent deliveries
```

- `signature: "github"` takes GitHub's `X-Hub-Signature-256`, with an optional
  `events` list. `"odin"` needs `X-Odin-Timestamp` and
  `X-Odin-Signature: v1=<hex HMAC-SHA256 of "<timestamp>.<body>">`.
- `ticket: { "mode": "existing", "ticketPointer": "/ticket" }` runs on the
  ticket the payload names (key, number or id).
- Sessions run as whoever saved the webhook. Never put secrets in the
  instructions; the payload reaches the agent as data only.

## Safety

- A session can read every repository you attach with the credential you
  name, and it runs on your subscription or the workspace's key. Only attach
  what the task needs.
- Confirm with the user before dispatching against production repositories.
- Do not paste secrets into `instructions`; they are stored on the session.
- Only set `allowPush` when the user wants a pull request; read
  `.data.session.result.pullRequests` afterwards for the links.

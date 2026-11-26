# Odin REST API — endpoint reference

Base URL is `$ODIN_API_BASE_URL` (dev `https://api.odinhelp.net`, prod
`https://api.odinhelp.com`). Every path below is appended verbatim, e.g.
`GET $ODIN_API_BASE_URL/api/tickets`.

The **authoritative, exhaustive** route list is the repo manifest
`infrastructure/api-codegen/manifest.json` (~445 routes). This file is a
curated map of the endpoints you'll reach most often. When a path here shows
`ANY`, one handler serves several verbs and branches on the method — read the
handler if unsure which verbs/bodies are valid.

## Contract (all endpoints)

- **Auth:** `Authorization: Bearer $ODIN_API_TOKEN`. Optionally
  `X-Active-Tenant-Id: $ODIN_TENANT_ID` to act in a specific tenant.
- **Success envelope:** `{ "success": true, "data": <T> }`.
- **Error envelope:** `{ "success": false, "error": { "code", "message", "details"? } }`
  with HTTP 400/401/403/404/409/422/500.
- **Pagination:** list endpoints accept `?pageSize=<n>&cursor=<opaque>` and
  return `data: { data: T[], nextCursor?: string }`. There is no total/page
  count — treat `nextCursor` as the only "is there more?" signal, and
  round-trip it unchanged (or use `odin --all`).

## Personal Access Tokens (this credential)

```
GET    /api/profile/tokens                 list your tokens (no secrets)
POST   /api/profile/tokens                 issue one: {"name","ttlDays"?}  → {token} once
GET    /api/profile/tokens/validate        preflight — identity + expiry
DELETE /api/profile/tokens/{tokenId}       revoke one of your tokens
GET    /api/profile                        your profile
GET    /api/profile/permissions            your effective permissions + features
```

## Native context and revision history

```
GET/POST /api/native-context
GET/PATCH /api/native-context/{id}
GET       /api/native-context/{id}?operation=history[&cursor=<nextCursor>]
```

History uses `tickets:read`, a user session/PAT, `service-desk.context`, and
the record's live tenant/scope/source access. It returns `data.items` (50
revisions per page), `data.nextCursor` and `data.partial`. Drain every page.
`/api/native-context/{id}/history` is unregistered and can return a routing
403 before authorization. See `source-context.md` before diagnosing access
or reconstructing old commitments. No broader role grant is implied.

## Tickets (helpdesk core)

```
GET/POST /api/tickets                       list / create
GET      /api/tickets/timers                active work timers
GET/PUT  /api/tickets/{ticketId}            get / update
POST     /api/tickets/{ticketId}/replies    add a reply
POST     /api/tickets/{ticketId}/clone|merge
ANY      /api/tickets/{ticketId}/worklog[/{entryId}]
ANY      /api/tickets/{ticketId}/timer
```
Ticket fields: `status` (open/in_progress/waiting_customer/scheduled/resolved/closed),
`priority` (low/medium/high/critical), `ticketType` (incident/problem/request/change),
`requester`, `assignee`. List defaults to pageSize 50 (max 200).

## Customers & Contacts (CRM)

```
ANY  /api/customers[/{customerId}]          list / create / get / update / delete
POST /api/customers/{customerId}/merge
ANY  /api/contacts[/{contactId}]
GET  /api/contacts/search?q=...
POST /api/contacts/bulk-import
```

## RMM agents & devices

```
GET  /api/agents                            fleet list
GET/PATCH/DELETE /api/agents/{agentId}
GET/POST /api/agents/{agentId}/commands     read / queue a command
GET  /api/agents/{agentId}/inventory | metrics | vulnerabilities | policies
GET  /api/devices[/{deviceId}]              discovered (non-agent) devices
GET  /api/networks[/{networkId}]
```

## Projects / Epics / Issues

```
GET/POST /api/projects · GET/PATCH/DELETE /api/projects/{projectId}
ANY /api/projects/{projectId}/issues[/{issueId}]
ANY /api/issue-attachments/{projectId}/{issueId}[/{attachmentId}]   files on an issue and its comments (GET list, POST presign, PUT confirm, GET download link, DELETE)
POST /api/developer/tasks/from-issues   dispatch issues to a coding agent as a Developer task (see docs/agile-dispatch.md)
GET  /api/developer/tasks/for-issues?projectId=&issueId=   Developer tasks dispatched from a project's (or one issue's) issues
ANY /api/projects/-/epics
POST /api/projects/{projectId}/updates/{draft,send}
```

## Billing: invoices & agreements

```
GET  /api/ticket-invoices[/{invoiceId}] + .../{send,cancel,retract,lines,...}
GET  /api/invoice-reminders + /send /cancel /toggle
ANY  /api/msa-agreements | /api/osa-agreements | /api/sow-agreements
GET  /api/analytics/ar                       AR aging
GET  /api/analytics/value-log
```

## Assets, products, automation

```
ANY /api/assets[/{assetId}] · ANY /api/asset-types[/{assetTypeId}]
ANY /api/products[/{productId}]
GET/POST /api/catalog · POST /api/catalog/{productId}/install
GET/POST /api/policies · GET/PATCH/DELETE /api/policies/{policyId}
ANY /api/alert-rules[/{ruleId}] · ANY /api/automation-rules[/{ruleId}]
GET/POST /api/scripts · POST /api/scripts/{scriptId}/run
ANY /api/runbooks[/{runbookId}] · POST /api/runbooks/{runbookId}/execute
```

## RentRedi (integration connections)

```
GET/POST /api/rentredi/connections                    list / create
GET/PATCH/DELETE /api/rentredi/connections/{id}       read / update / remove
POST /api/rentredi/connections/{id}/test              re-verify the stored token
POST /api/rentredi/test-connection                    verify a token, store nothing
```
Requires `settings:manage` + the `settings.integrations.rentredi` feature
toggle (the collection LIST is intentionally ungated). Connections carry a
`status` of `connected` / `disconnected` / `degraded` / `unverified`, written
by a 15-minute refresh sweep — only `disconnected` needs a human.

**Connection management only.** There is no endpoint for properties, units,
leases, or renters. See `rentredi.md` for the full surface, the status
semantics, and why a session token can only be captured by the user in a
browser.

## Cloud skill sessions

Headless Claude Code / Codex runs on a ticket. Full guide:
`references/cloud-sessions.md`.

| Method | Path | Scope |
|---|---|---|
| GET | `/api/cloud-sessions/options` | `cloud-sessions:write` |
| GET | `/api/cloud-sessions/repos?credentialId=&search=` | `cloud-sessions:write` |
| GET | `/api/cloud-sessions/skills?repo=&credentialId=&ref=` | `cloud-sessions:write` |
| POST | `/api/cloud-sessions` (dispatch, 202) | `cloud-sessions:write` + `tickets:write` |
| GET | `/api/cloud-sessions?ticketId=` | `cloud-sessions:read` + `tickets:read` |
| GET | `/api/cloud-sessions/{sessionId}` | `cloud-sessions:read` + `tickets:read` |
| GET | `/api/cloud-sessions/{sessionId}/events?after=` | `cloud-sessions:read` + `tickets:read` |
| POST | `/api/cloud-sessions/{sessionId}/cancel` | `cloud-sessions:write` (own) / `:manage` |

## Wiki, files, settings, dashboard

```
/api/wiki (home, pages[/{id}], search, spaces, ...)
/api/files (folders, {nodeId}[/download-url], upload-url)
GET/PATCH /api/settings (+ email-templates, contracts, smtp-relays, ...)
GET /api/dashboard/{stats,activity}
GET /api/audit[/export.csv]
GET /api/users · GET /api/tenants · ANY /api/roles · ANY /api/teams
```

## Permission scopes

A PAT authenticates **as the issuing user**, so it can reach any endpoint that
user's role allows — no separate scope grant needed. If a call returns
`403 Missing required permission: <scope>`, the user's role lacks it. Scopes
follow the `<entity>:<verb>` shape: `read` / `write` (some add `manage` /
`admin`). Entities include `tickets, customers, contacts, agents, alerts,
alert-rules, automation-rules, agreements, invoices, products, projects,
tenants, users, files, idv, commands, apikeys`.

# Native persistence (pending release)

See [persistence.md](persistence.md) for exact native work-record methods,
fields, live access, cursor traversal and write recovery. These collections
reuse the domain-router resources; do not use `/api/crm` for native tracking.

Leads from the tenant's CRM (`/api/crm-leads`, `/api/crm-deal-links`): [crm-leads.md](crm-leads.md). `/api/native-sales` is retired (410).

Source-backed context: [source-context.md](source-context.md).

Opt-in notification webhooks: [notification-webhooks.md](notification-webhooks.md).

Fresh-session current-context queries: [assistant-retrieval.md](assistant-retrieval.md).

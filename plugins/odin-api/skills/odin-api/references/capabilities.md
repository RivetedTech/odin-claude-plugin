# Capability map and source provenance

Reviewed against **Odin 12.101.0**, SupportPlatform commit
`63180f19bcdcea806feb2e7dddc80a27e3a3e6c4`, on 2026-11-04.
[Platform source](https://github.com/RivetedTech/SupportPlatform/tree/63180f19bcdcea806feb2e7dddc80a27e3a3e6c4).
This is source verification, not a live account or deployment check. The platform's
native-record references still used draft/pending-release wording at this commit;
this package describes their implemented source contracts without asserting rollout.

Preflight the authorized PAT, then read `GET /api/profile/permissions` for live
permissions/features. Confirm the target environment supports the selected method.
A missing/disabled collection or a denial is not an empty result. Keep unavailable
sources and incomplete retrieval visible. No installed ChatGPT skill, hosted asset,
production setting, notification destination or platform deployment is changed by
these repository updates.

| User goal | Read before acting | Source verification |
| --- | --- | --- |
| Tickets, customers, agents, projects, files, analytics | [endpoints.md](endpoints.md) | API manifest and relevant handlers |
| Reconstruct work across sessions | [assistant-retrieval.md](assistant-retrieval.md) | `backend/src/shared/work-records/current-context.ts` |
| Track obligations, dependencies, deadlines, proof and reminders | [persistence.md](persistence.md) | `backend/src/shared/work-records/api.ts`, reminder handler |
| Track leads and manual follow-ups | [native-sales.md](native-sales.md) | `backend/src/shared/work-records/sales-api.ts` |
| Save facts, decisions, meeting context and corrections | [source-context.md](source-context.md) | `backend/src/shared/work-records/context-api.ts` |
| Inspect or configure opt-in notification webhooks | [notification-webhooks.md](notification-webhooks.md) | `backend/src/shared/notification-webhooks/api.ts` |
| Monitor services, checks, outages, incidents and reports | [monitoring.md](monitoring.md) | Dedicated monitoring handler and subrouters |
| Invoice, refund, agreement or uploaded-PDF work | [billing-agreements.md](billing-agreements.md) | Billing and contracts handlers |
| RentRedi connection health | [rentredi.md](rentredi.md) | RentRedi connection handlers |
| Find a registered resource or handler | [route-catalog.md](route-catalog.md) | 556 entries from `infrastructure/api-codegen/manifest.json` |

Native work is gated by `tools.work-records`; reminder scheduling independently
uses `service-desk.reminders`. Leads use `sales.leads`, saved source context uses
`service-desk.context`, and user webhooks use `service-desk.notification-webhooks`.
Query private, business and selected live team scopes separately. Default-private
records stay private even when their owner/assignee changes. A task's notification,
a lead's paid stage, a sent message and a completed obligation are distinct facts.

Native tracking is separate from the Salesforce-backed `/api/crm` integration.
Records-only lead/activity writes send no outreach. Do not invoke campaigns,
external delivery or Salesforce merely to remember a prospect or next action.

Customer lists now accept `bdm`, `csm` and `isr` email filters; the sentinel
`__unassigned__` selects customers without a current holder. Responses add
`salesAssignments` and `salesFilterOptions`. These are current role holders,
not commission rates or financial setup, and `salesAssignments` is server-owned.
Source: `backend/src/shared/customers/sales-filters.ts` and domain router.

Slack and Teams connections use `/api/slack-connections` and
`/api/teams-connections`: GET/POST collection; GET/PATCH/DELETE detail;
POST detail `?operation=test` sends a real test message. Listing needs
`settings:manage` or `monitoring:read`; other actions need `settings:manage`
and the integration feature. Slack app configuration and OAuth have separate
operations; do not fabricate a nested `/test` route or put webhook URLs in chat.
Source: `backend/src/shared/chat/api.ts`.

To refresh the routing inventory from a clean platform checkout, run
`python3 scripts/update-route-catalog.py --platform-root <checkout>` in the plugin
repo. Verify with the same command plus `--check`. Review the specific handlers
and dedicated monitoring API as well: `ANY`, catch-all and greedy routes hide
concrete operations and request bodies from the primary manifest. Update this
source pin and curated references together; do not infer support from a UI label.

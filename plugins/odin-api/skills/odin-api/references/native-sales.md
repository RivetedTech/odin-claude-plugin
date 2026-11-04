# Native sales and manual follow-ups (reviewed source contract)

These handlers are records-only and never call `/api/crm`, Salesforce, a campaign,
or a prospect delivery provider. Prospects need neither a customer nor an email.
Use the issuing user's live `customers:read` / `customers:write`, user authentication
and `sales.leads` feature. Source links also require their own live permissions.
Private/business/team scope, pagination, idempotency and version contracts follow
[persistence.md](persistence.md). `contacts:read` is required to link contacts.

| Method | Path | Contract |
| --- | --- | --- |
| POST | `/api/native-sales` | Create `kind:lead` (default) or `kind:activity`; Idempotency-Key |
| GET/PATCH | `/api/native-sales/{id}` | Read/edit; PATCH requires Idempotency-Key and If-Match |
| GET | `/api/native-sales?kind=lead|activity` | Scope/cursor/pageSize/search; view all/active/due/paused/excluded |
| GET | `/api/native-sales?operation=changes` | Monotonic change cursor, same kind and scope |
| GET | `/api/native-sales?operation=duplicates&type=organization&organizationName=Demo` | Authorized normalized same-scope name candidates; drain nextCursor |
| GET | `/api/native-sales/{id}?operation=history` | Durable full revision timeline, cursor |
| GET | `/api/native-records/{id}` | Common permission-scoped permanent record, or explicit unavailable stub |

All records have `title`, `owner`, optional `nextAction`, `description` notes and
`related` source links. `trackedBy` remains the creator; the owner may be external.
`lead` has immutable `type:organization|person|opportunity`, optional organizationName,
personName, email, phone, organizationRecordId (native organization), personRecordIds
(native people at that organization), source, customerId and contactIds (existing
native customer/contact links, no automatic customer creation).

`stage:new|tentative|qualified|proposal|agreement|paid|won|lost` records distinct
commercial facts. A paid/won stage does not complete work or a follow-up sequence.
Optional `followUpDate:YYYY-MM-DD` is date-only and does not enable notifications.
`estimatedValue` is nonnegative and requires uppercase three-letter `currency`.
Multiple opportunities/people can link to one organization without duplicate customers.

`flags` accepts optOut, doNotContact, paused, excluded, each `{enabled:boolean,reason}`.
The server records actor/time and preserves unspecified flags. Clearing a flag requires
a reason; all changes remain in history. These do not grant outreach permission.

`sequence:{state:planned|paused|completed|canceled,reason?,checkpoints:[{id,label,
plannedAt?,completedAt?,activityId?,confirmation?}]}` has at most 32 checkpoints.
Completion requires an actual past timestamp and a completed same-lead activity with
that occurrence time or explicit user confirmation. A completed sequence requires
all checkpoints; canceled meetings, lost deals and sequence cancellation stay separate.

`activity:{leadId,type:call|meeting|message|follow_up,status:planned|completed|canceled,
plannedAt?,occurredAt?,sourceLinks?,manuallyConfirmed?}` records actual occurrence times.
Completed touches need a past occurredAt and source evidence or manuallyConfirmed:true.
No activity sends anything. Completing a call leaves linked obligations open.

Duplicate search uses NFKC, collapsed whitespace and case-insensitive type/name keys.
Review candidates; do not automatically merge based on a name. To merge an existing
source, PATCH `mergeInto:<target ID>,mergeTargetVersion:<target version>,reason` with
the source If-Match. The target must be canonical, same type and exact scope; copy
protective flags to it explicitly first. The source ID/history and notes remain as an
alias, discoverable in `view=all`. Correct an alias with mergeInto:null and a reason.
Link/conversion uses explicit existing customer/contact IDs; source history is retained.

```bash
scripts/odin --idempotency-key demo-lead-v1 POST /api/native-sales \
 '{"title":"Demo clinic follow-up","owner":"Demo sales owner","nextAction":"Record meeting outcome","lead":{"type":"organization","organizationName":"Demo clinic","stage":"tentative","followUpDate":"2026-10-22"}}'
scripts/odin --all GET '/api/native-sales?view=due&pageSize=100'
```

Web `/sales/leads` and Expo Leads provide matching list/detail/edit/history flows.
Stable web record links use `/records/{id}`. Unavailable sources are explicit.
duplicate searches traverse the scope index and match readable fields only,
so items and continuation shape cannot reveal protected names or flags.
File evidence links use `/files/{nodeId}` and the existing authenticated,
short-lived download flow after explicit user action. Mobile resolves source
links against its configured dashboard origin.
Never treat a missing source as proof of completion. Verify runtime availability and
feature access before using these source-supported methods.

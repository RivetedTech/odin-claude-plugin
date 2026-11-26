# Leads from the tenant's CRM

Leads in Odin are read from and written to the tenant's primary CRM
(Salesforce or monday.com), chosen under Settings > Integrations. Odin keeps
no lead records of its own. Every caller sees what the CRM's connected user
sees. Reads need `customers:read`, writes `customers:write`, and the
`sales.leads` feature ("Leads and Follow-ups") must be on.

The old native records are retired: `/api/native-sales` answers
`410 GONE` with `details.reason: "crm_backed"` and
`details.replacement: "/api/crm-leads"`. Do not call it. Old native lead and
follow-up ids may still open read-only through `/api/native-records/{id}`
until the operator discards them.

## Refs

A lead is named by an opaque ref, `<provider>~<object>~<id>`:

| Provider | Objects (type) |
| --- | --- |
| `salesforce` | `Lead`, `Contact` (person), `Account` (organization), `Opportunity` (opportunity) |
| `monday` | `contact` (person), `deal` (opportunity) |

Treat a ref as a string: take it from a list or detail response and send it
back as-is (URL-encode it in a path).

## Routes

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/api/crm-leads?operation=options` | `{connected, provider?, types, personStages, dealStages}`: which types the CRM serves and its stage labels |
| GET | `/api/crm-leads?type=person\|organization\|opportunity&search=&view=all\|open&cursor=&pageSize=` | `{connected, provider?, supported, items, nextCursor?}`; drain `nextCursor` |
| GET | `/api/crm-leads/{ref}` | `{lead, activities, bookings}`: the record, its CRM tasks/events/updates, and Odin bookings pushed to the person |
| POST | `/api/crm-leads` | Create `{type, name, company?, email?, phone?, title?, stage?, amount?, closeDate?}`; send an Idempotency-Key |
| PATCH | `/api/crm-leads/{ref}` | Change any of those fields; send `If-Match: <lead.version>` and an Idempotency-Key |
| POST | `/api/crm-leads/{ref}` | Log an activity `{subject, body?, dueDate?}` (Salesforce Task, monday update); a `dueDate` (YYYY-MM-DD) makes it a follow-up |
| GET | `/api/crm-deal-links/{document}~{id}` | The CRM deal a proposal, quote or agreement is for, and its Won push |
| PUT | `/api/crm-deal-links/{document}~{id}` | `{dealRef: string\|null}`; on a signed agreement this pushes Won now (choosing the same deal again retries) |

`connected: false` means the tenant has no primary CRM: lists come back empty
and writes answer `409` with `reason: "crm_not_connected"`. `supported: false`
means the CRM has no records of that type mapped (monday.com organizations).

`lead.version` is the CRM's change stamp. A PATCH whose `If-Match` no longer
matches answers `409` with `reason: "changed"` and the current `lead`; reload
and reapply rather than overwrite. Reusing an Idempotency-Key with a different
body answers `409` with `reason: "idempotency_key_reused"`. A CRM that can't be
reached answers `502 CRM_UNAVAILABLE`.

Deal links (`document` is `proposal`, `quote`, `msa`, `sow`, `osa` or
`custom`) also need the document's own permission (`agreements:read`,
`agreements:write` to change it). Signing an agreement marks its deal Won with
the agreement's value; an MSA on its own doesn't.

```bash
scripts/odin GET '/api/crm-leads?operation=options'
scripts/odin --all GET '/api/crm-leads?type=person&view=open&pageSize=50'
scripts/odin --idempotency-key demo-lead-v1 POST /api/crm-leads \
 '{"type":"person","name":"Demo Prospect","company":"Demo clinic","email":"prospect@example.invalid"}'
scripts/odin --idempotency-key demo-note-v1 POST '/api/crm-leads/salesforce~Lead~00Q000000000001' \
 '{"subject":"Call back about the proposal","dueDate":"2026-12-02"}'
```

Web `/sales/leads` and the Expo Leads tab show the same list, detail, create,
edit and activity flows. Odin never sends outreach from a lead.

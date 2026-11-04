# Fresh-session assistant retrieval (reviewed source contract)

See [capabilities.md](capabilities.md) for the pinned source and runtime availability limits.

Use the user's live session/PAT. Preflight first. No assistant bypass or
conversation-window memory is required.

`GET /api/current-context` accepts scope=private (default),
scope=business&scopeId=active-tenant, or scope=team&scopeId=live-team;
view=all|open|waiting|blocked|due|stale, pageSize (1–50, default 25), cursor.
Normal success/data response: schemaVersion, asOf, scope, items, nextCursor,
partial, changeCheckpoint, changes, unavailableCollections, notificationDetails,
consistency. No recent-date cutoff applies. GET is read-only. Unmigrated old
undated todos have version 0/migrationPending and explicit unverified completion.

Native items include the authorized record and open/overdue/stale flags,
completionVerified and completionBasis (source_evidence,
explicit_user_confirmation, unverified). Preserve owner versus trackedBy, next
action, waiting/blocker, dependencies, deadline precision, checklist,
snooze/archive state and completion actor/time/evidence. A source link is not
independent proof. Missing sources yield unavailable stubs. Access/feature
failures are explicit in unavailableCollections. Errors never imply no work.
`completion_evidence_unavailable` distinguishes missing/inaccessible proof from
an inaccessible context source. Neither unavailability implies completion or
confirmed incompletion. Live feature gates also apply to linked native sources.

Drain EVERY nextCursor, including empty filtered pages. Private traversal lists
native records, then legacy todos/ticket reminders; shared traversal excludes
private reminders. Native work is never replaced/duplicated by its reminder's
notification state. Use all for full reconstruction; open retains unresolved
archived/snoozed records, while active work views remove those from daily tracking.

This is a bounded live traversal, not a frozen snapshot. The sequencer checkpoint
is read BEFORE traversing IDs. After all pages, drain EVERY authorized kind's
changes query from changeCheckpoint, then re-fetch changed IDs. This recovers
concurrent inserts/updates behind the ID cursor. Retain changeCursor for future
polling. Cursors/checkpoints belong to the exact tenant/user/scope/view. Query
private, active business and each selected live team separately; a private query
does not assert team completeness.

Work notification annotations include reminder status/state/scheduledFor,
recordedFiredAt and deliveriesQuery. recordedFiredAt is NOT a receipt. Legacy
sent rows are uncertain. notificationDetails.loaded=false explicitly says
receipts have independent pagination: follow /api/ticket-reminders and
/api/notification-webhooks, then each authorized deliveries/attempts query.
Never equate attempted/provider-accepted with human receipt or work completion.

## UI and schedule integration

Web /service-desk/work-records and Expo Work and Commitments share scoped
all/active/overdue/waiting/blocked/stale lists, editing, evidence or explicit
completion confirmation, reasoned reopening, snooze/archive conditions and
permanent timelines. Date-only deadlines use an explicit IANA zone defaulting
to the profile; exact deadlines stay instants. Inaccessible-source records can
be archived with metadata-only edits retaining links/history. Removing links
cannot reveal copied content after source access was lost.

Attach a first optional schedule with POST /api/ticket-reminders,
Idempotency-Key, If-Match of the WORK version (or body.expectedVersion):

```json
{"kind":"custom","title":"Synthetic inspection corrections","workRecordId":"<existing-work-id>","expectedVersion":1,"remindAt":"2026-11-01T14:00:00Z","timeZone":"America/New_York","channels":{"email":false,"push":false,"webhook":false}}
```

This increments the work version and attaches the existing scheduler atomically,
preserving its ID/owner/dependencies/state without a second obligation. Work
must be owner-private and active. PATCH an already attached reminder using its
existing version contract. Further recurrence/snooze/reschedule/occurrence-vs-
series controls stay in the agenda. Shared work retains its explicit scope;
an authorized private linked tracking record can hold a personal reminder.

## Synthetic CO₂ acceptance

Keep four obligations: invoice/payment verification → physical corrections →
reinspection → certificate evidence. Payment completes only payment. Six weeks
without messages must still leave the other three reconstructible with owners,
next actions, dependencies and missing evidence. Complete only with appropriate
accessible evidence or labeled user confirmation and completed dependencies.
Completion cancels applicable schedule work atomically, retaining history.
Paid stages, acknowledgments, appointments and sent requests do not prove larger
completion. Cancel/archive/lost deal/manual sequence completion remain distinct.

Platform-repository acceptance command (requires a SupportPlatform checkout and
disposable DynamoDB Local on 127.0.0.1:8001; not a command supplied by this plugin):
`npx ts-node --transpile-only --project backend/tsconfig.json
backend/integration/assistant-persistence.ts`. Synthetic PAT/roles/data exercise
real authentication/conditional transactions; all SDK requests are redirected
to localhost. No notification provider or source URL is invoked.


Feature ownership: native work CRUD, permanent links, history, search, changes and linked-source access use `tools.work-records`. Scheduling and reminder receipts use `service-desk.reminders` independently. Lead/activity collections use `sales.leads`; context uses `service-desk.context`. Current-context exposes only currently authorized enabled collections and omits reminder data/queries when Reminders is disabled. Disabling Work removes native work and legacy-todo reconstruction; independently enabled ticket reminders remain accessible. Native follow-up/review/deadline fields remain useful with every notification channel disabled.

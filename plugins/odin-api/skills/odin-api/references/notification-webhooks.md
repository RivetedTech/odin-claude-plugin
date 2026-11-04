# User notification webhooks (reviewed source contract)

Records-only sales remains records-only. These opt-in notifications are separate
from Salesforce, campaigns and the existing alert/rule whole-ticket webhooks.
Never activate an endpoint or test it merely because a record was saved.

## Settings and access

`PATCH /api/profile` accepts `notifications.reminderEmailEnabled`,
`reminderPushEnabled`, `webhookEnabled` and `defaultReminderChannels` containing
required boolean `email`, `push`, optional boolean `webhook`. Legacy email/push
remain enabled unless explicitly disabled; external webhook delivery defaults
off. Per-reminder `channels.webhook:true` is independent of email/push. Dates can
exist with every channel off. Only the user can enable their global external
delivery preference; administrators may disable it.

Feature `service-desk.notification-webhooks` and a user session/PAT are required.
Endpoints belong to their authenticated user and active tenant. Event sources
use current `tickets:read` (work/context/reminder) or `customers:read`
(lead/activity), current team membership and source ACLs. Selecting an event
does not grant access to its sources. No assistant superuser or API-key identity.

## Exact endpoint contract

| Method | Path | Behavior |
| --- | --- | --- |
| GET | /api/notification-webhooks | Owner list, `cursor`, 50 per page |
| POST | /api/notification-webhooks | Create paused endpoint by default |
| GET | /api/notification-webhooks/{id} | Redacted configuration |
| PATCH | /api/notification-webhooks/{id} | Edit, rotate, activate, pause or delete |
| GET | detail?operation=preview | Synthetic example; no HTTP request |
| GET | detail?operation=deliveries\|attempts\|history | Cursor pages, 50 each |
| POST | detail?operation=test | Explicit synthetic HTTP test, queued durably |
| POST | detail?operation=replay | Guarded failed/uncertain delivery replay |

Responses use the normal backend `success/data` envelope. Pages contain `items`,
optional `nextCursor`, `partial`; follow continuation even on an empty page.
Creation and every write require `Idempotency-Key`; PATCH/test also require
`If-Match:<endpoint.version>`. Reuse the identical key/body/precondition after an
ambiguous response; changed reuse or stale versions return 409. Reload before
correcting. Tenant/scope mismatch is 403, not found 404, validation 400,
unconfigured encryption 503. Endpoint scope is immutable.

Write fields: `name`, public HTTPS `url` (port 443 only), `scope:{kind:private}`
or `{kind:business|team,id}`, `state:paused|active|deleted`, `events`, `fields`,
write-only `secret` (32–128 bytes), `consent`, `reason`; optional `tenantId` must
equal the authenticated tenant. Maximum eight current named endpoints per
user/tenant. Deletion requires a reason and is terminal; history remains.
Activation or changing an active destination/subscriptions/payload requires
explicit consent describing what leaves Odin. Pausing/deleting/changing those
settings advances an epoch: already queued events stop, including after resume.
Rotation keeps the epoch, uses the new key for queued deliveries and revokes the
previous signing secret in Odin. In-flight HTTP requests cannot be recalled.

Events: `work.created|updated|completed|reopened|canceled`, `lead.created|updated`,
`activity.created|updated`, `context.created|updated`, `reminder.due`.
Payload `schemaVersion:1` has stable `eventId`, type, tenantId, occurredAt,
synthetic, and data containing recordId/kind/eventVersion/deepLink, plus
currentVersion where available. Links are relative authorized Odin links.
Default `fields:[]` excludes content. Optional fields are only `title`, `state`,
`nextAction`, `owner`, drawn from the currently authorized record. No ticket
threads, descriptions, transcript, email addresses or secrets are included.

Test body is `{confirmSyntheticTest:true}`; all event content is server-created
synthetic data. Testing explicitly authorizes one HTTP request even while the
endpoint/global preference is paused, but an intervening endpoint edit stops
the queued test. Never supply real customer content for testing.
Replay body: `{deliveryId,version,reason,acknowledgeDuplicateRisk}`. Only an active
endpoint and authorized failed/uncertain source can replay. Uncertain delivery
requires explicit duplicate-risk acknowledgment; success is never replayed.

## Delivery, security and receiver contract

Server-owned activeSince advances with activation or payload/subscription changes.
Fan-out excludes events from before that consent, so a new subscription does not
send a historical backlog. Events queued during an already-active subscription's
downtime still catch up within the documented budgets and current opt-in checks.

States: pending → leased → attempted → success|failed|uncertain|suppressed.
Success means HTTP 2xx provider acceptance, not proof of human receipt or work
completion. Last response stores only the status/code, never the response body.
Known 429/5xx failures retry after 1/2/4/8 minutes, five attempts total. Unknown
transport results or an expired attempted lease become uncertain and stop
automatic resend. A pre-attempt lease can recover. IDs survive retries/replay;
receivers must deduplicate. Delivery is not guaranteed exactly once. Durable
queued events catch up after downtime within worker/rate budgets (10/minute per
endpoint); overdue recurring reminders coalesce under the reminder contract.
Quiet hours/business-day rules apply to reminder webhook dispatch.

Dispatch rechecks global opt-in, endpoint epoch/subscription, live permissions,
feature/source availability and reminder cancellation/completion/schedule.
Endpoint/profile/source versions are guarded immediately before marking an
attempt. Concurrent changes abort the attempt. Permissions can change during
an already in-flight network call; no system can retract accepted HTTP data.

Headers: `Odin-Event-Id`, `Odin-Delivery-Id`, `Odin-Key-Id`, `Odin-Timestamp`
(Unix seconds), `Odin-Signature:v1=<hex>`. Verify HMAC-SHA256 over
`timestamp + "." + exact raw JSON request bytes`, constant-time compare, enforce
a receiver timestamp window, and deduplicate stable IDs. Use key ID for an
explicit rotation/revocation process. Do not reconstruct/reformat JSON to verify.

KMS encrypts secrets with tenant/user/endpoint encryption context; there is no
plaintext fallback. Secrets are never returned, logged or saved in history.
Public-address validation rejects private, link-local, metadata, loopback,
reserved and translated IP ranges. All DNS answers must be public. Every
request pins a validated DNS address while verifying TLS for the original host;
redirects are refused. DNS/HTTP deadlines, response-size and payload-size bounds
apply. Invalid destinations/encryption failures stop before any HTTP attempt.

For a secret-bearing request, use a protected local JSON file rather than an
inline shell argument: `scripts/odin --body-file /secure/path/request.json
--idempotency-key <stable-key> POST /api/notification-webhooks`. Never put a real
secret in examples, chat, PR descriptions or terminal output.

Web `/profile/notification-webhooks` and Expo Account → Notification webhooks
show synthetic previews, independent preferences, explicit test controls,
inspectable delivery logs, rotation, pause/deletion and guarded replay.


Resuming an endpoint or changing its destination, events or optional fields establishes `activeSince`, a new consent boundary. Previously queued events do not fan out retrospectively across that boundary. Rotation uses the current secret at dispatch; it does not expand the subscription. Previews and explicit synthetic tests use the selected event's actual source kind, read permission and feature (sales for activity, context for context); they do not require unrelated reminder access.

An explicit replay of a currently valid reminder webhook atomically requeues that endpoint's reminder receipt and occurrence finalizer with the canonical delivery. Other channels' successful receipts remain unchanged. The parent shows scheduled delivery until the finalizer reconciles the new outcome. Replaying a canceled, completed, rescheduled or unavailable reminder is rejected. Occurrence and channel versions prevent a concurrent stale finalizer from overwriting a replay. Known HTTP 429/5xx responses remain retryable failures even if their response body stalls or the socket subsequently closes; transport failure before any status is uncertain.

Web and Expo preserve webhook-only channel edits and seed new reminder forms, including the ticket sheet, from `defaultReminderChannels.webhook`. A missing webhook preference defaults to false. A late profile response cannot replace an explicit channel choice.

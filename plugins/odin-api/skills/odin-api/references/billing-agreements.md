# Invoices, refunds and agreements

Reviewed source and runtime limits: [capabilities.md](capabilities.md). These
operations can charge/refund money, send customer communications or alter legal
records. Establish the requested action, target and authorization before acting.
Read the exact handler for request bodies; do not reuse native work-record
version/idempotency contracts for unrelated billing APIs.

## Invoices and asynchronous work

`GET /api/ticket-invoices` lists; GET detail reads; PATCH detail edits draft
lines. POST detail sub-actions include `send`, `cancel`, `retract`, `regenerate`,
`sync-stripe`, `resend`, `detail-link`, `charge`, `visibility` and `delete`.
POST `/{invoiceId}/lines` adds a draft line; DELETE the same path with `?lineId=`
removes one. These actions are served by a greedy proxy resource, with exact
handler-tail matching. An arbitrary suffix is not supported.

`send` finalizes asynchronously and can return HTTP 202 with `data.requestId`;
`detail-link` can also return an asynchronous work request. Poll
`GET /api/work-requests/{requestId}` until the request's actual outcome is known.
202 means accepted, not sent/paid/complete. Do not retry a charge/send merely
because the first request has not finished. `resend` sends email; `charge`
attempts payment; `retract` voids and returns to draft; these are distinct actions.

Reads need `invoices:read`; ordinary writes `invoices:write`; hide/unhide and
permanent deletion `invoices:admin`. Hidden invoices are excluded from totals
and return 404 below admin. Deletion can delete/void in Stripe and hides the
record from everyone; `GET /api/ticket-invoices?deleted=true` is the admin
Deleted view. It is not a normal draft cancellation or UI filter.

## Refunds

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/api/ticket-invoices/{invoiceId}/refunds` | `invoices:read` |
| POST | `/api/ticket-invoices/{invoiceId}/refunds` | `invoices:manage` |
| POST | `/api/ticket-invoices/{invoiceId}/refund-attachments` | `invoices:manage` |
| GET | `/api/ticket-invoices/{invoiceId}/refunds/{refundId}/attachments/{attachmentId}` | `invoices:read` |
| POST | `/api/ticket-invoices/{invoiceId}/refunds/{refundId}/documentation` | `invoices:manage` |

The invoice identifier can be an Odin ticket-invoice ID or a Stripe `in_` ID
for another paid record; Stripe aliases do not bypass hidden-record access.
GET `?live=true` reconciles live refund information. POST uses a stable body
`requestKey` (8–64 letters/digits/dashes), positive integer `amountCents`, reason
and note. Optional `notifyCustomer` defaults true; review communications intent.
Reasons: requested_by_customer, service_issue, billing_error, duplicate, goodwill,
fraudulent, other. Preserve the request key after an ambiguous result; inspect
existing refund state before making a new attempt. Do not invent a separate
`/api/refunds` API or assume an `Idempotency-Key` header replaces `requestKey`.

The server computes refundable amounts across payments and enforces spent
prepayment-credit and in-progress restrictions. Refunds can affect commission
clawbacks. A request, receipt or documentation edit does not prove settlement;
read the resulting state. Attachment uploads/downloads use protected signed
URLs. Do not print real financial documents or customer messages into logs.

## Agreements

MSA, OSA, SOW and custom agreements have separate API prefixes:
`/api/msa-agreements`, `/api/osa-agreements`, `/api/sow-agreements`,
`/api/custom-agreements`. Native/template terms, uploaded PDFs, signer pools,
viewers, locked countersigners, approval, bundles and per-agreement lifecycle
rules differ. Read the concrete handler before supplying a body or choosing a
signing/send/void/delete operation. An API call cannot replace a human signature.

Custom agreements support collection GET/POST, detail GET/PATCH/DELETE, and
POST detail send-approval actions. Detail sub-actions include `resend`,
`redirect-signer`, `revert-to-draft`, `sign-link`, `sign`, `resend-executed`,
`retry-finalize`, `hard-delete`; GET `views` and `pdf-url` inspect results.
A create can email the counterparty: do not treat it as a harmless local draft.
Hidden agreements require admin access; do not reinterpret 404 as absent data.

For a completed **uploaded-PDF custom agreement**, POST
`/api/custom-agreements/{agreementId}/retry-finalize` with
`{"regenerate":true}` rebuilds the signed PDF without emailing it. Without that
flag the operation retries stuck finalization. The new Regenerate feature does
not imply a `/regenerate` child route. GET `pdf-url?doc=source|executed&mode=inline|download`
selects the document. Do not substitute current customer details for signed
content; signed documents and live customer-name display have different roles.

OSA supports prepayments, hosting/support terms, base-fee timing, backdated
billing and termination; SOW supports project pricing and bundled agreement
flows. These are not interchangeable agreement types. Check their registered
routes and handlers for the exact preview/commit body and financial effects.
Bundled members may reject standalone actions; use the bundle workflow rather
than voiding or resending a member independently.

Sources: `backend/src/handlers/billing/ticket-invoices.ts`, `invoice-refunds.ts`,
`backend/src/shared/billing/refunds/model.ts`,
`backend/src/handlers/contracts/{custom,msa,osa,sow}-agreements.ts`,
`custom-pdf-agreements.ts` and the route/feature manifests at the pinned commit.

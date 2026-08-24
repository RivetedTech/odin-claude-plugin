# RentRedi through Odin

Odin brokers access to a tenant's RentRedi landlord accounts. This file covers
the whole RentRedi surface the API exposes, what it deliberately does not
expose, and the one workflow that cannot be automated.

## Read this first: there is no RentRedi *data* endpoint

Odin exposes **connection management only** — wiring landlord accounts up,
checking their health, and rotating their credentials. There is currently **no
endpoint that returns properties, units, leases, renters, or payments**, on any
Odin surface. Do not construct paths like `/api/rentredi/properties`; they 404.

If a user asks for RentRedi *data* through Odin, say so plainly rather than
guessing at a route. The building blocks exist server-side
(`backend/src/shared/rentredi-client.ts` can call any RentRedi callable) but
nothing is wired to an Odin route yet, so it is a feature to build, not an
endpoint to find.

What you **can** do here is answer "is our RentRedi integration healthy, and
which portfolios are broken?" — which is the question that actually comes up,
because sessions die silently.

## Access requirements

| Requirement | Value |
| --- | --- |
| Permission scope | `settings:manage` |
| Feature toggle | `settings.integrations.rentredi` (default ON) |
| Tenant | Per-tenant; set `ODIN_TENANT_ID` when the user belongs to several |

A `403` here means one of two different things, and they need different
answers: `Missing required permission: settings:manage` is the user's role,
while a feature-toggle rejection means an admin switched RentRedi off for that
tenant in **Administration → Features**. Check `GET /api/profile/permissions`
to tell them apart — it returns both the effective permissions and the resolved
feature map.

Note that `GET /api/rentredi/connections` (the collection list) is
**deliberately left ungated** by the feature toggle, so a list can succeed on a
tenant where every mutation is refused. That is intentional: the list is how a
surface discovers whether an account is wired at all.

## Endpoints

```
GET    /api/rentredi/connections                        list (no secrets)
POST   /api/rentredi/connections                        create
GET    /api/rentredi/connections/{connectionId}         read one
PATCH  /api/rentredi/connections/{connectionId}         rename / relink / rotate
DELETE /api/rentredi/connections/{connectionId}         remove + purge the secret
POST   /api/rentredi/connections/{connectionId}/test    re-verify the STORED token
POST   /api/rentredi/test-connection                    verify a token, store nothing
```

A tenant may wire 0..N connections — RentRedi has no sub-accounts, so one
credential is one portfolio and a tenant managing several needs several
connections, each with an operator-supplied `name` that is unique per tenant.

## Connection shape

```jsonc
{
  "connectionId": "…",
  "name": "Riverside Portfolio",   // unique per tenant; the real identifier
  "email": "owner@example.com",    // display label, may be null
  "customerId": "cust-1",          // REQUIRED — a portfolio is always somebody's
  "customerName": "Riverside LLC", // resolved; null if the customer was deleted
  "brandId": null,
  "brandName": null,
  "ownerId": "j9epy4…",            // Firebase UID used as ownerID on RentRedi calls
  "ownerIdPinned": false,          // true when an operator pinned it explicitly
  "hasCredential": true,
  "status": "connected",           // see below
  "lastRefreshAt": "2026-08-23T12:00:00.000Z",
  "lastVerifiedAt": "2026-08-23T12:00:00.000Z",
  "lastFailureAt": null,
  "lastFailureReason": null,
  "consecutiveFailures": 0,
  "createdAt": "…",
  "createdBy": "admin@example.com" // alerted when the session dies
}
```

The session token itself **never** round-trips. It lives in SSM and is not
readable through the API by anyone, including the user who set it.

## Status semantics — the distinction that matters

| `status` | Meaning | Does a human need to act? |
| --- | --- | --- |
| `connected` | Last refresh succeeded. | No |
| `disconnected` | RentRedi rejected the stored session — revoked or expired. | **Yes** — reconnect |
| `degraded` | Refresh failed for a reason that is not the token (RentRedi down, network, an upstream config change). | No — it retries |
| `unverified` | Stored but never successfully refreshed. | Wait one sweep |

A 15-minute sweep (`rentredi-refresh` Lambda) renews every stored session and
writes these fields. **`disconnected` is the only one that needs somebody**;
reporting a `degraded` connection as broken sends people chasing an outage they
cannot fix. Keep that distinction when you summarise health to a user.

`lastFailureAt` is the START of the current failure run, not the most recent
attempt — so it dates the breakage rather than resetting every quarter hour.

### Health check

```bash
scripts/odin GET /api/rentredi/connections \
  | jq -r '.data.items[] | select(.status != "connected")
           | "\(.status)\t\(.name)\t\(.lastFailureReason // "-")"'
```

Empty output means every connection is healthy.

Two things about that command are easy to get wrong. The list is returned as
`{ "success": true, "data": { "items": [...] } }` — an `items` object, **not**
the `{ data: [...], nextCursor }` page envelope most Odin list endpoints use —
so the jq path is `.data.items[]`. And it is **not paginated**: there is no
cursor, so `odin --all` does not apply here and would emit the array as a
single blob rather than one connection per line.

## Creating a connection

```bash
scripts/odin POST /api/rentredi/connections '{
  "name": "Riverside Portfolio",
  "refreshToken": "AMf-…",
  "customerId": "cust-1",
  "brandId": null,
  "email": "owner@example.com"
}'
```

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | Unique per tenant, case-insensitive. |
| `refreshToken` | yes | See "the part you cannot automate" below. |
| `customerId` | yes | Must exist in this tenant. |
| `brandId` | no | White-label brand; `null`/`""` clears it on PATCH. |
| `email` | no | Display label. Left out, it is read from the token's claims. |
| `ownerId` | no | Pin only for a property-manager login acting for another owner. |

The token is proved against RentRedi **before** anything is stored, so a bad
token is a `400` and never leaves a row behind.

`PATCH` takes the same fields, all optional; omit `refreshToken` (or send `""`)
to keep the stored one. Sending a new one rotates the credential and re-probes.

## The part you cannot automate

**You cannot obtain a RentRedi session token programmatically, and you must not
try.** RentRedi's Firebase project enforces reCAPTCHA Enterprise on
email/password sign-in, so a server-side login is refused with
`MISSING_RECAPTCHA_TOKEN` before the credential is ever checked. Only a real
browser can answer that challenge.

The supported flow is:

1. The **user** signs in at `app.rentredi.com` and answers the challenge.
2. They click the "Grab RentRedi session" bookmarklet on Odin's RentRedi
   settings screen, which copies the refresh token to their clipboard.
3. They paste it into Odin, or hand it to you for a `POST`/`PATCH`.

If a user asks you to log into RentRedi for them, explain that the challenge is
a bot-protection control working as intended and point them at the bookmarklet.
Do not look for a way around it.

A refresh token is a **live credential**: anyone holding it can act as that
RentRedi account until it is revoked. Never echo one into a transcript, a log,
a ticket, or a commit. Tokens die when the RentRedi password changes or the
account signs out everywhere — that is the ordinary cause of `disconnected`,
and the fix is always steps 1–3 above.

## Verifying without storing

`POST /api/rentredi/test-connection` proves a token and stores nothing —
useful before committing to a create, or to check a token a user just captured:

```bash
scripts/odin POST /api/rentredi/test-connection '{"refreshToken":"AMf-…"}'
```

Both this and the per-connection `/test` return:

```jsonc
{ "ok": true, "ownerId": "j9epy4…", "propertyCount": 3, "checkedAt": "…" }
```

`propertyCount: null` is **not** a failure — it means RentRedi accepted the
session but refused the owner-scoped read, which is what a property-manager
login looks like when it is not authorised on that owner. `propertyCount: 0` is
a real, empty portfolio. Do not report either as a broken connection.

The per-connection `/test` also clears the failure fields on success, so it
doubles as "I fixed it, re-arm the alerting".

## Deleting

`DELETE /api/rentredi/connections/{connectionId}` removes the row and purges
the stored secret. There is no undo and no soft delete — confirm with the user
before calling it, and remember that recreating means capturing a fresh token.

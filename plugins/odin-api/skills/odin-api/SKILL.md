---
name: odin-api
description: >-
  Interact with the Odin support-platform REST API from Claude using a
  long-life Personal Access Token stored in an environment variable. Use this
  whenever the user wants to query or manage Odin data programmatically —
  list/create/update tickets, look up customers, contacts, or RMM agents,
  read dashboard/analytics, manage invoices/agreements, etc. Also covers the
  RentRedi integration Odin brokers — listing landlord-account connections,
  checking which ones have expired, testing and rotating their session
  credentials. The token authenticates as the issuing user with that user's
  live permissions.
  Triggers: "odin api", "query odin", "list my tickets", "create a ticket via
  the api", "odin token", "call the odin backend", "rentredi", "rentredi
  connection", "which rentredi connections are broken", "reconnect rentredi".
---

# Odin REST API

Drive the Odin (support-platform) REST API with a **Personal Access Token
(PAT)** kept in an env var. Every call goes out as `Authorization: Bearer
$ODIN_API_TOKEN`. The token authenticates **as the user who issued it**, with
that user's live role/permissions — so it can do through the API exactly what
that user can do in the dashboard, and no more.

## 1. One-time setup

### a. Issue a token (365-day default, revocable)

In the dashboard: **Profile → Personal Access Tokens → New token**. Give it a
name, optionally pick a shorter lifetime (default **365 days**), and **copy the
`opat_…` value once** — it is shown only at creation and cannot be retrieved
again. Revoke it any time from the same panel.

(Scriptable equivalent, if you already have a session/token that can call it:
`POST /api/profile/tokens` with `{"name":"my-cli","ttlDays":365}` returns
`{ tokenId, name, createdAt, expiresAt, token }` where `token` is the raw
`opat_…`.)

### b. Export the env vars

| Variable | Required | Meaning |
| --- | --- | --- |
| `ODIN_API_TOKEN` | **yes** | The `opat_…` token from step (a). |
| `ODIN_API_BASE_URL` | **yes** | Backend origin — **no default, set it explicitly.** Dev: `https://api.odinhelp.net` · Prod: `https://api.odinhelp.com` · Local shim: `http://localhost:4000`. |
| `ODIN_TENANT_ID` | no | Sent as `X-Active-Tenant-Id` to act in a specific tenant. Only needed to override the token's home tenant (e.g. a user who belongs to several). |

```bash
export ODIN_API_TOKEN="opat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export ODIN_API_BASE_URL="https://api.odinhelp.net"   # dev
```

## 2. Always preflight first

Before any other call, verify the token:

```bash
scripts/odin preflight
```

This hits `GET /api/profile/tokens/validate`. A healthy token prints its
identity + expiry, e.g. `valid · user@example.com · tenant acme · expires in
361 days`. If it prints `INVALID` / exits non-zero, **stop** and tell the user
the token is missing, expired, or revoked — they need to reissue it on their
Profile. Do not keep retrying other endpoints against a bad token.

## 3. Make requests

```bash
scripts/odin GET  /api/tickets?pageSize=20
scripts/odin GET  /api/tickets/T1024
scripts/odin POST /api/tickets '{"subject":"Printer down","priority":"high","description":"..."}'
scripts/odin PATCH /api/tickets/T1024 '{"status":"in_progress"}'
scripts/odin DELETE /api/profile/tokens/<tokenId>
scripts/odin --all GET /api/customers        # auto-follow every page

# Which RentRedi portfolios need a human? (`disconnected` only — `degraded`
# retries itself and is not the operator's to fix.) Note the `.data.items[]`
# path: this list is NOT paginated, so no `--all`.
scripts/odin GET /api/rentredi/connections \
  | jq -r '.data.items[] | select(.status == "disconnected")
           | "\(.name)\t\(.lastFailureReason)"'
```

- The wrapper adds `Authorization`, `Accept: application/json`, and (when
  `ODIN_TENANT_ID` is set) `X-Active-Tenant-Id`. It pretty-prints with `jq`
  when available and exits non-zero on any non-2xx status.
- **Response envelope:** success is `{ "success": true, "data": <T> }`; errors
  are `{ "success": false, "error": { "code", "message", "details" } }`.
- **Pagination:** list endpoints take `?pageSize=<n>&cursor=<opaque>` and
  return `{ data: [...], nextCursor? }` inside `data`. Round-trip `nextCursor`
  unchanged, or use `--all` to collect every page.

See `references/endpoints.md` for the endpoint catalog, permission scopes, and
the pagination/envelope contract. The authoritative full route list lives in
the repo at `infrastructure/api-codegen/manifest.json`.

**RentRedi:** read `references/rentredi.md` before touching anything under
`/api/rentredi`. Two things there will otherwise cost you a wrong answer: Odin
exposes connection management only — there is **no** endpoint for properties,
units, or renters, so do not guess at one — and a session token cannot be
obtained programmatically, because RentRedi enforces a reCAPTCHA on sign-in
that only a real browser can answer.

## 4. Safety

- **Never** print, log, echo, or commit `ODIN_API_TOKEN`. Treat it like a
  password. The wrapper never echoes it.
- Writes (`POST`/`PATCH`/`PUT`/`DELETE`) hit **real data** for whatever
  environment `ODIN_API_BASE_URL` points at. Confirm with the user before any
  mutation against production (`api.odinhelp.com`); point at dev
  (`api.odinhelp.net`) to experiment.
- The token carries the issuing user's **live** permissions — if a call
  returns `403 Missing required permission`, that user simply lacks that
  access; don't try to escalate.

## Installing this skill elsewhere

The folder is self-contained (bash + `curl`, `jq` optional). Four ways to get
it onto another machine, in rough order of convenience:

1. **From the Odin dashboard.** The Claude skill button in the top-right menu
   bar downloads a zip, optionally with a freshly-minted token and the right
   `ODIN_API_BASE_URL` already written into a `.env`. Unzip into
   `~/.claude/skills/`.
2. **One-liner, no sign-in needed:**
   `curl -fsSL https://www.odinhelp.com/skill/install.sh | bash`
3. **As a Claude Code plugin**, which keeps itself updated:
   `/plugin marketplace add RivetedTech/odin-claude-plugin` then
   `/plugin install odin-api@odin`
4. **By hand**, from this repo: copy `.claude/skills/odin-api/` into another
   project's `.claude/skills/` or into `~/.claude/skills/`.

All four install the same files. Whichever you use, set the env vars from
step 1 above — only the dashboard download can prefill them for you.

**This folder is the source of truth.** The public copies are generated from
it: `website/scripts/gen-skill-assets.mjs` regenerates the marketing-site copy
on every site build, `npm run gen:skill` vendors it into the backend (with a
test that fails the build on drift), and `.github/workflows/publish-skill.yml`
mirrors it into the public marketplace repo. Edit here, never in a copy.

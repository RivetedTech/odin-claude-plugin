# Monitoring

Reviewed source and runtime limits: [capabilities.md](capabilities.md).
Monitoring runs behind a dedicated proxy API defined in
`infrastructure/cloudformation/monitoring-api.yaml`. The public origin remains
Odin's selected API origin and the public prefix is `/api/monitoring`; the
handler restores that prefix after gateway mapping. Use the same authorized
user PAT, selected tenant and enabled features; do not call an internal gateway
hostname or treat proxy registration as arbitrary-route support.

| Method | Public path | Purpose |
| --- | --- | --- |
| GET | `/api/monitoring/overview` | Dashboard service summary |
| GET | `/api/monitoring/overview/outages` | Filtered recent outages |
| GET | `/api/monitoring/overview/trends` | Dashboard trends |
| GET/POST | `/api/monitoring/services` | List/create services |
| GET/PATCH/DELETE | `/api/monitoring/services/{serviceId}` | Read/edit/delete service |
| GET/POST | `/api/monitoring/services/{serviceId}/outages` | List/record outages |
| PATCH/DELETE | `/api/monitoring/services/{serviceId}/outages/{outageId}` | Correct/remove outage |
| GET/POST | `/api/monitoring/maintenance` | List/create windows |
| PATCH/DELETE | `/api/monitoring/maintenance/{windowId}` | Change/remove window |
| GET/POST | `/api/monitoring/checks` | List/create probes |
| GET/PATCH/DELETE | `/api/monitoring/checks/{checkId}` | Check configuration |
| GET | `/api/monitoring/checks/locations` | Available probe regions |
| POST | `/api/monitoring/checks/test` | Test supplied probe configuration |
| POST | `/api/monitoring/checks/{checkId}/run` | Run stored probe now |
| GET | `/api/monitoring/checks/{checkId}/results` | Bounded result history |
| GET | `/api/monitoring/checks/{checkId}/series` | Response-time series |
| GET | `/api/monitoring/services/{serviceId}/series` | Service series |
| POST | `/api/monitoring/incidents/{ticketId}/ack` | Acknowledge incident |
| GET | `/api/monitoring/reports/uptime` | Uptime report data |
| GET | `/api/monitoring/reports/uptime/csv` | CSV export |
| GET | `/api/monitoring/reports/uptime/pdf` | JSON with fileName/contentBase64 PDF export |
| POST | `/api/monitoring/reports/uptime/send` | Send report now |
| GET | `/api/monitoring/reports/deliveries` | Report delivery records |
| GET/PUT | `/api/monitoring/report-settings/{customerId}` | Read/edit scheduled report settings |

GET requires `monitoring:read`; ordinary writes require `monitoring:write`.
Mutations under sources, AWS/Azure test configuration, escalation policies,
paging line, alert contacts, report settings and report send require
`monitoring:manage`. Agent enrollment tokens cannot use Monitoring. Base feature
`service-desk.monitoring` and applicable child toggles (checks, AWS, Azure,
incidents, reports, alert-contacts, escalation) apply independently.

Odin supports service sources, AWS/Azure resource discovery and polling, check
alert contacts, Slack/Teams destinations, escalation policies and a paging line.
Inspect `backend/src/shared/monitoring/` subrouters before constructing their
bodies. Source secrets and webhook URLs need secure local request files. Source
rotation, probe tests, poll-now, report sending, calls/messages and destination
tests can cause real external operations; saving a record alone authorizes none
of them. Inbound ingestion and provider callbacks have their own source-token
or signature authentication and are not user-PAT inspection endpoints.

Services lists return `data.items`; service detail contains `data.service`,
`outages` and `maintenance`. Recent-outage panes and probe results can be bounded
rather than a complete history. Inspect date windows, limits and each endpoint's
actual continuation shape; do not apply `--all` or infer full completeness from
one overview pane. CSV/PDF/download routes return non-JSON artifacts or download
information: use an authorized host download tool instead of pretty-printing
binary data through `scripts/odin`. The monitoring PDF export specifically
returns `data.fileName` and `data.contentBase64`; decode it into a local artifact
without dumping the base64 into chat. Report delivery queries require customerId.

Sources: `backend/src/handlers/monitoring/index.ts`,
`backend/src/shared/monitoring/checks/routes.ts`, `report-routes.ts`, associated
subrouters and `backend/src/shared/feature-catalog.ts` at the pinned commit.

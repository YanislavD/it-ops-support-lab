# IT Ops & Support Simulation Lab

A self-contained IT infrastructure simulation built to practice the daily workflow
of an IT Support / NOC / Junior SysAdmin role: services running in containers,
monitoring and alerting on top of them, an incident-to-ticket flow, and a CI/CD
pipeline that gates changes before they reach the "production" stack.

This is a learning/portfolio project, built solo with AI assistance.

## Scenario

**NovaTech Solutions** is a fictional small IT services company. Its stack:

| Service | Role | Port | Tech |
|---|---|---|---|
| `corporate-website` | Public marketing site | 8081 | nginx + static HTML |
| `asset-api` | Internal REST API for IT asset inventory (laptops, printers, phones...) | 8082 | Python/Flask + PostgreSQL |
| `admin-portal` | Internal dashboard used by IT staff to view/manage assets | 8083 | Python/Flask (server-rendered) |
| `asset-db` | Database backing the asset API | internal only | PostgreSQL 16 |

`admin-portal` calls `asset-api`, which reads/writes `asset-db`. `corporate-website`
is fully independent. This gives three distinct HTTP endpoints to monitor, plus a
realistic failure mode (API up but DB down, API down but website fine, etc.).

## Status

- [x] Module 1 — Services & Docker Compose foundation
- [x] Module 2 — Monitoring & Alerting (Prometheus, Blackbox Exporter, Grafana, Alertmanager)
- [x] Module 3 — CI/CD (GitHub Actions)
- [ ] Module 4 — Ticketing & Support (incident → ticket → resolution, Knowledge Base)
- [ ] Module 5 — Documentation (architecture diagram, demo video, incident report)

## Running locally

```bash
docker compose up --build
```

| URL | Service |
|---|---|
| http://localhost:8081 | Corporate website |
| http://localhost:8082/health | Asset API health check |
| http://localhost:8082/api/assets | Asset API (JSON) |
| http://localhost:8083 | Admin portal (dashboard UI) |
| http://localhost:9090 | Prometheus |
| http://localhost:9115 | Blackbox Exporter |
| http://localhost:9093 | Alertmanager |
| http://localhost:3001 | Grafana (login: `admin` / `admin`) |

> Grafana is published on **3001**, not the usual 3000, to avoid clashing with a
> locally installed Grafana on this machine. Adjust in `docker-compose.yml` if
> that's not an issue on your system.

To get real Discord notifications on incidents, copy `.env.example` to `.env`
and set `DISCORD_WEBHOOK_URL` to a webhook URL from your Discord server
(Server Settings → Integrations → Webhooks → New Webhook). Without it,
`alertmanager-discord` will keep restarting — harmless, the rest of the stack
still works, alerts just won't be delivered anywhere.

Stop everything:

```bash
docker compose down
```

Reset the database (drops all data):

```bash
docker compose down -v
```

## Architecture (Module 1)

```
                 ┌────────────────────┐
   Internet ───▶ │ corporate-website  │  (nginx, static)
                 └────────────────────┘

                 ┌────────────────────┐      ┌──────────────┐
   Internet ───▶ │   admin-portal     │ ───▶ │  asset-api   │ ───▶ asset-db (Postgres)
                 │  (Flask, port 8083)│      │ (Flask, 8082)│
                 └────────────────────┘      └──────────────┘
```

All services share a single Docker bridge network (`lab`) so they can reach each
other by service name. Only the app-facing ports are published to the host;
`asset-db` is reachable only from within the network.

## Monitoring & alerting (Module 2)

```
 corporate-website ┐
 asset-api/health  ├──▶ blackbox-exporter ──▶ prometheus ──▶ alertmanager ──▶ alertmanager-discord ──▶ Discord
 admin-portal      ┘                              │
                                                    ▼
                                                 grafana (dashboards)
```

- **Blackbox Exporter** performs an HTTP GET against each service every 15s
  (`corporate-website:/`, `asset-api:/health`, `admin-portal:/`) and exposes
  `probe_success` / `probe_duration_seconds`.
- **Prometheus** scrapes those metrics and evaluates two alert rules
  (`monitoring/prometheus/alert.rules.yml`):
  - `ServiceDown` — `probe_success == 0` for 30s
  - `ServiceSlowResponse` — `probe_duration_seconds > 1` for 1m
- **Grafana** (pre-provisioned, no manual setup) shows a "Service Uptime &
  Response Time" dashboard: per-service UP/DOWN stat panels, a response-time
  graph, and an uptime timeline.
- **Alertmanager** routes firing alerts to `alertmanager-discord`, which
  translates them into a Discord message.

Tested end-to-end by stopping `corporate-website` (`docker stop corporate-website`):
the Grafana panel flipped to DOWN within 15s, and `ServiceDown` reached
Alertmanager within the 30s `for` window. Restarting the container auto-resolved
the alert.

## CI/CD (Module 3)

GitHub Actions workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
Runs on every push and pull request to `main`:

1. **lint** — `ruff` static analysis on `asset-api` and `admin-portal`.
2. **build-and-test** (only if lint passes) — builds all three application
   images via `docker compose build`, starts the stack, polls each service
   until reachable, then asserts on the actual response of `/`, `/health`,
   and `/api/assets`. Logs are dumped on failure; containers are always torn
   down afterward.

Scope note: there's no real production server to deploy to, so "CD" here
stops at build + smoke-test rather than an actual deployment step — that's a
deliberate boundary, not a missing piece.

## Next steps

Module 4 adds a ticketing system wired to Alertmanager, so a firing alert
automatically opens an incident ticket, plus a Knowledge Base of documented
fixes.

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
- [ ] Module 2 — Monitoring & Alerting (Prometheus, Blackbox Exporter, Grafana, Alertmanager)
- [ ] Module 3 — CI/CD (GitHub Actions)
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

## Next steps

Module 2 adds Prometheus + Blackbox Exporter to poll `/`, `/health`, and `/` on
each of the three services, Grafana to visualize uptime/latency, and Alertmanager
to fire a notification (Telegram/Discord) the moment a service goes down.

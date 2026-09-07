# Incident Report

| | |
|---|---|
| **Incident ID** | osTicket #557356 |
| **Date** | 2026-09-07 |
| **Severity** | Critical |
| **Status** | Resolved / Closed |
| **Affected service** | `corporate-website` (public marketing site) |
| **Detected by** | Blackbox Exporter → Prometheus (automated, no human report) |
| **Reported by** | NovaTech Monitoring (automated ticket creation via `ticket-bridge`) |
| **Closed by** | Admin Admin |

All times below are local (UTC+2) and taken directly from container logs,
Prometheus/Alertmanager API responses, and osTicket ticket timestamps captured
during the incident — see [`demo-walkthrough.md`](demo-walkthrough.md) for the
matching screenshots.

## Summary

`corporate-website` stopped responding to health checks. Blackbox Exporter
detected the outage within 15 seconds; Prometheus raised a `ServiceDown` alert
after the outage held for 30 seconds; Alertmanager notified both Discord and
`ticket-bridge`, which opened osTicket #557356 automatically. An operator
(this exercise) restarted the container, confirmed recovery in Grafana, and
closed the ticket with a note recording the cause.

Cause was a deliberate, controlled stop of the container (`docker stop
corporate-website`) to exercise the monitoring/alerting/ticketing pipeline —
not a real defect. Included here as the incident report format this project's
tooling would produce for an actual outage.

## Timeline

| Time | Event |
|---|---|
| 11:29:24 | `corporate-website` container stopped. Outage begins. |
| 11:29:~39 | Blackbox Exporter's next probe (15s interval) fails. Grafana's "Service Uptime & Response Time" dashboard flips `corporate-website` to **DOWN**. |
| 11:29:54 | `probe_success == 0` has held for the alert rule's 30s `for` window — Prometheus's `ServiceDown` alert transitions `pending` → `firing`. `ServiceSlowResponse` fires alongside it (the failed probe also registers as an abnormally long request). |
| 11:30:~04 | Alertmanager's `group_wait` (10s) elapses; the alert is dispatched to **both** configured receivers: `alertmanager-discord` (Discord notification) and `ticket-bridge`. |
| 11:30 | `ticket-bridge` calls osTicket's REST API. **Ticket #557356 — "[CRITICAL] corporate-website is down"** is created, body populated verbatim from Prometheus's alert description. (Companion ticket #639891 covers the `ServiceSlowResponse` alert.) |
| 11:39:49 | Fix applied: `corporate-website` container restarted (`docker start corporate-website`). |
| 11:39:~54 | Blackbox Exporter's next probe succeeds. Grafana flips back to **UP**. |
| ~11:40 | `probe_success` back to 1; Prometheus auto-resolves both alerts. Alertmanager sends a "resolved" notification to Discord. |
| 11:42 | Operator posts an internal note on ticket #557356 documenting the root cause and fix. |
| 11:43 | Ticket #557356 closed. |

**Total outage duration:** ~10 minutes 25 seconds (11:29:24 → 11:39:49).
**Time to first alert:** 30 seconds (bound by the alert rule's `for` duration).
**Time to ticket:** under 1 minute from outage start.

## Root Cause

`corporate-website`'s container process was stopped directly
(`docker stop corporate-website`). No application code, configuration, or
infrastructure fault was involved — this was a controlled exercise of the
detection → alert → ticket pipeline described in this project's brief, run
against the live stack rather than simulated.

## Impact

`corporate-website` was unreachable for ~10.5 minutes. `asset-api` and
`admin-portal` were unaffected throughout (confirmed in Grafana — both stayed
`UP` for the full duration), demonstrating that the three services fail
independently, as designed.

## Resolution

Restarting the container (`docker start corporate-website`) fully resolved
the issue. No data loss (the service is stateless; `corporate-website` serves
static content only). Recovery was confirmed via:

1. Grafana's `corporate-website` stat panel returning to `UP`.
2. Prometheus's `/api/v1/alerts` no longer listing `ServiceDown` /
   `ServiceSlowResponse` for `corporate-website`.
3. A direct `curl` against http://localhost:8081/ returning HTTP 200.

## Detection & Response Assessment

| Stage | Target | Actual | Met? |
|---|---|---|---|
| Detection | ≤ 15s (probe interval) | ~15s | ✅ |
| Alert raised | 30s (rule `for` duration, by design) | 30s | ✅ |
| Ticket created | Automatic, no manual step | Automatic, ~1 min after outage start | ✅ |
| Notification | Reaches both Discord and osTicket | Confirmed both fired from the same alert | ✅ |

## Follow-up / Preventive Actions

- No code or infrastructure change needed — this was an intentional test, not
  a defect.
- Confirmed the runbook in the Knowledge Base ("ServiceDown alert fired -
  what do I do?", under Knowledgebase → Incident Runbooks in osTicket —
  requires an agent login, so not linkable here) matches what was actually
  done to resolve this incident.
- If this had been a real crash rather than a manual stop, the next step
  would be `docker compose logs corporate-website` to capture the crash
  reason before restarting — noted in the KB article for next time.

## Related

- Knowledge Base: "ServiceDown alert fired - what do I do?" (Incident Runbooks
  category, osTicket)
- [Demo walkthrough](demo-walkthrough.md) — screenshots of every stage above
- Alert rule source: [`monitoring/prometheus/alert.rules.yml`](../monitoring/prometheus/alert.rules.yml)

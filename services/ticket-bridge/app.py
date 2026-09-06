import logging
import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket-bridge")

OSTICKET_URL = os.environ.get("OSTICKET_URL", "http://osticket")
OSTICKET_API_KEY = os.environ.get("OSTICKET_API_KEY", "")

# Alertmanager re-sends a still-firing alert every repeat_interval. Without
# this, a single ongoing incident would open a fresh ticket every hour.
# fingerprint (from Alertmanager) -> osTicket ticket number.
open_tickets = {}


@app.get("/health")
def health():
    return jsonify(status="ok", api_key_configured=bool(OSTICKET_API_KEY)), 200


@app.post("/alert")
def handle_alert():
    payload = request.get_json(silent=True) or {}
    results = []

    for alert in payload.get("alerts", []):
        fingerprint = alert.get("fingerprint")
        status = alert.get("status")

        if status == "firing":
            if fingerprint in open_tickets:
                results.append({"fingerprint": fingerprint, "action": "already-open"})
                continue
            ticket_number = create_ticket(alert)
            if ticket_number:
                open_tickets[fingerprint] = ticket_number
                results.append({"fingerprint": fingerprint, "action": "ticket-created", "ticket": ticket_number})
            else:
                results.append({"fingerprint": fingerprint, "action": "ticket-creation-failed"})

        elif status == "resolved":
            ticket_number = open_tickets.pop(fingerprint, None)
            results.append({"fingerprint": fingerprint, "action": "cleared", "ticket": ticket_number})

    return jsonify(results=results), 200


def create_ticket(alert):
    if not OSTICKET_API_KEY:
        logger.warning("OSTICKET_API_KEY not set, skipping ticket creation")
        return None

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    severity = labels.get("severity", "warning").upper()
    summary = annotations.get("summary", labels.get("alertname", "Alert"))
    description = annotations.get("description", summary)

    body = {
        "alert": False,
        "autorespond": False,
        "source": "API",
        "name": "NovaTech Monitoring",
        "email": "monitoring@novatech.example",
        "subject": f"[{severity}] {summary}",
        "message": description,
        "ip": "127.0.0.1",
    }

    try:
        resp = requests.post(
            f"{OSTICKET_URL}/api/tickets.json",
            json=body,
            headers={"X-API-Key": OSTICKET_API_KEY},
            timeout=5,
        )
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to reach osTicket: %s", exc)
        return None

    if resp.status_code == 201:
        ticket_number = resp.text.strip()
        logger.info("Created osTicket #%s for %s", ticket_number, summary)
        return ticket_number

    logger.error("osTicket API error %s: %s", resp.status_code, resp.text)
    return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)

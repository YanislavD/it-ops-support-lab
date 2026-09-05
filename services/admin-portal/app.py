import os

import requests
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

ASSET_API_URL = os.environ.get("ASSET_API_URL", "http://asset-api:5000")


@app.get("/health")
def health():
    return {"status": "ok"}, 200


@app.get("/")
def dashboard():
    error = None
    assets = []
    try:
        resp = requests.get(f"{ASSET_API_URL}/api/assets", timeout=3)
        resp.raise_for_status()
        assets = resp.json()
    except requests.exceptions.RequestException:
        error = "Asset API is unreachable. Check the asset-api service."

    status_filter = request.args.get("status")
    if status_filter:
        assets = [a for a in assets if a.get("status") == status_filter]

    counts = {"active": 0, "in_repair": 0, "retired": 0}
    for a in assets:
        if a.get("status") in counts:
            counts[a["status"]] += 1

    return render_template(
        "index.html", assets=assets, error=error, counts=counts, status_filter=status_filter
    )


@app.post("/assets/new")
def create_asset():
    payload = {
        "name": request.form.get("name"),
        "asset_type": request.form.get("asset_type"),
        "status": request.form.get("status", "active"),
        "assigned_to": request.form.get("assigned_to") or None,
        "location": request.form.get("location") or None,
    }
    try:
        requests.post(f"{ASSET_API_URL}/api/assets", json=payload, timeout=3)
    except requests.exceptions.RequestException:
        pass
    return redirect(url_for("dashboard"))


@app.post("/assets/<int:asset_id>/delete")
def delete_asset(asset_id):
    try:
        requests.delete(f"{ASSET_API_URL}/api/assets/{asset_id}", timeout=3)
    except requests.exceptions.RequestException:
        pass
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

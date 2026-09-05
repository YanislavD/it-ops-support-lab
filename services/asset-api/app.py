import os
import time

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "asset-db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "assets"),
    "user": os.environ.get("DB_USER", "assets_user"),
    "password": os.environ.get("DB_PASSWORD", "assets_pass"),
}

VALID_STATUSES = {"active", "in_repair", "retired"}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db(retries=10, delay=3):
    """Create the assets table on startup, retrying until Postgres is ready."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            conn = get_connection()
            with conn, conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assets (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        asset_type TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active',
                        assigned_to TEXT,
                        location TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute("SELECT COUNT(*) FROM assets")
                (count,) = cur.fetchone()
                if count == 0:
                    cur.execute(
                        """
                        INSERT INTO assets (name, asset_type, status, assigned_to, location)
                        VALUES
                            ('Dell Latitude 5440', 'laptop', 'active', 'A. Ivanov', 'Berlin HQ'),
                            ('HP LaserJet M404', 'printer', 'active', NULL, 'Berlin HQ - Floor 2'),
                            ('ThinkPad T14', 'laptop', 'in_repair', 'M. Schmidt', 'Munich Office'),
                            ('iPhone 13', 'mobile', 'retired', NULL, 'Storage')
                        """
                    )
            conn.close()
            return
        except psycopg2.OperationalError as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to database after {retries} attempts") from last_error


@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify(status="ok", database="reachable"), 200
    except psycopg2.OperationalError:
        return jsonify(status="degraded", database="unreachable"), 503


@app.get("/api/assets")
def list_assets():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM assets ORDER BY id")
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.get("/api/assets/<int:asset_id>")
def get_asset(asset_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM assets WHERE id = %s", (asset_id,))
            row = cur.fetchone()
        if row is None:
            return jsonify(error="asset not found"), 404
        return jsonify(dict(row))
    finally:
        conn.close()


@app.post("/api/assets")
def create_asset():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    asset_type = data.get("asset_type")
    if not name or not asset_type:
        return jsonify(error="name and asset_type are required"), 400

    status = data.get("status", "active")
    if status not in VALID_STATUSES:
        return jsonify(error=f"status must be one of {sorted(VALID_STATUSES)}"), 400

    conn = get_connection()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO assets (name, asset_type, status, assigned_to, location)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (name, asset_type, status, data.get("assigned_to"), data.get("location")),
            )
            row = cur.fetchone()
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.put("/api/assets/<int:asset_id>")
def update_asset(asset_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status is not None and status not in VALID_STATUSES:
        return jsonify(error=f"status must be one of {sorted(VALID_STATUSES)}"), 400

    conn = get_connection()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE assets
                SET name = COALESCE(%s, name),
                    asset_type = COALESCE(%s, asset_type),
                    status = COALESCE(%s, status),
                    assigned_to = COALESCE(%s, assigned_to),
                    location = COALESCE(%s, location)
                WHERE id = %s
                RETURNING *
                """,
                (
                    data.get("name"),
                    data.get("asset_type"),
                    status,
                    data.get("assigned_to"),
                    data.get("location"),
                    asset_id,
                ),
            )
            row = cur.fetchone()
        if row is None:
            return jsonify(error="asset not found"), 404
        return jsonify(dict(row))
    finally:
        conn.close()


@app.delete("/api/assets/<int:asset_id>")
def delete_asset(asset_id):
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
            deleted = cur.rowcount
        if deleted == 0:
            return jsonify(error="asset not found"), 404
        return "", 204
    finally:
        conn.close()


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

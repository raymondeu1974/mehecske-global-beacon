"""Loopback-only synthetic research notice board."""
import argparse
from contextlib import closing
import getpass
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import secrets
import sqlite3
import time
import uuid

CONSENT = "synthetic-notices-v1"
CATALOG = {
    "shapes": "Compare classifiers on generated geometric shapes.",
    "graphs": "Compare traversal results on generated graphs.",
    "words": "Group generated words by their letter patterns.",
}
SECRET = re.compile(r"[A-Za-z0-9_-]{43,128}", re.ASCII)
SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY, token TEXT UNIQUE, after_seq INTEGER NOT NULL,
    consent TEXT NOT NULL, joined INTEGER NOT NULL, last_poll INTEGER
);
CREATE TABLE IF NOT EXISTS calls (
    seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,
    project TEXT UNIQUE NOT NULL, issued INTEGER NOT NULL,
    expires INTEGER NOT NULL, revoked INTEGER
);
CREATE TABLE IF NOT EXISTS receipts (
    agent TEXT NOT NULL, call_id TEXT NOT NULL, received INTEGER NOT NULL,
    PRIMARY KEY (agent, call_id)
);
CREATE TABLE IF NOT EXISTS clock (id INTEGER PRIMARY KEY CHECK(id=1), latest INTEGER);
CREATE TABLE IF NOT EXISTS registration (id INTEGER PRIMARY KEY CHECK(id=1), latest INTEGER);
"""


class Rejected(Exception):
    pass


def require(condition, status, reason):
    if not condition:
        raise Rejected(status, reason)


def new_secret():
    return secrets.token_urlsafe(32)


def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)


def fields(body, *names):
    require(type(body) is dict and body.keys() == set(names), 400, "invalid_fields")


def envelope(row, agent):
    return {
        "version": 1, "scope": CONSENT, "agent_id": agent, "call_id": row["id"],
        "project": row["project"], "summary": CATALOG[row["project"]],
        "issued_at": row["issued"], "expires_at": row["expires"],
    }


class Beacon:
    def __init__(self, path, admin, clock=time.time):
        if not SECRET.fullmatch(admin):
            raise ValueError("admin secret format")
        self.path = path
        self.admin = digest(admin)
        self.clock = clock
        with closing(sqlite3.connect(path)) as db:
            db.executescript(SCHEMA)

    def request(self, route, token, body):
        with closing(sqlite3.connect(self.path, timeout=3)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            now = int(self.clock())
            latest = db.execute("SELECT latest FROM clock WHERE id=1").fetchone()
            require(latest is None or now >= latest[0], 503, "clock_rollback")
            db.execute("INSERT OR REPLACE INTO clock VALUES (1, ?)", (now,))
            db.execute("SAVEPOINT operation")
            try:
                return self.dispatch(db, route, token, body, now)
            except Rejected as error:
                db.execute("ROLLBACK TO operation")
                db.execute("RELEASE operation")
                rejected = error
        raise rejected

    def dispatch(self, db, route, token, body, now):
        if route == "/register":
            fields(body, "consent", "future_notices")
            require(token is None, 400, "unexpected_authorization")
            require(body["consent"] == CONSENT and body["future_notices"] is True,
                    400, "explicit_consent_required")
            return self.register(db, now)

        require(isinstance(token, str) and SECRET.fullmatch(token), 401, "credential")
        credential = digest(token)
        admin = hmac.compare_digest(credential, self.admin)
        if route in {"/publish", "/revoke"}:
            require(admin, 403, "publisher_required")
            return self.publish(db, route, body, now)

        require(not admin, 403, "agent_required")
        agent = db.execute("SELECT * FROM agents WHERE token=?", (credential,)).fetchone()
        require(agent is not None, 401, "credential")
        agent_id = agent["id"]
        if route == "/unsubscribe":
            fields(body)
            db.execute("UPDATE agents SET token=NULL WHERE id=?", (agent_id,))
            return 200, {"unsubscribed": True}

        if route == "/feed":
            last = agent["last_poll"]
            require(last is None or now >= last + 5, 429, "poll_interval_5s")
            db.execute("UPDATE agents SET last_poll=? WHERE id=?", (now, agent_id))
            active = db.execute(
                "SELECT * FROM calls WHERE seq>? AND revoked IS NULL AND expires>? ORDER BY seq",
                (agent["after_seq"], now),
            )
            return 200, {"items": [envelope(row, agent_id) for row in active]}

        require(route == "/verify-and-receive", 404, "unknown_route")
        fields(body, "invitation")
        invitation = body["invitation"]
        require(type(invitation) is dict and type(invitation.get("call_id")) is str,
                400, "invalid_invitation")
        row = db.execute("SELECT * FROM calls WHERE id=?", (invitation["call_id"],)).fetchone()
        require(row is not None and row["seq"] > agent["after_seq"], 404, "unknown_invitation")
        require(encoded(invitation) == encoded(envelope(row, agent_id)), 422, "envelope_mismatch")
        require(row["revoked"] is None and now < row["expires"], 410, "inactive_invitation")
        receipt = db.execute(
            "INSERT OR IGNORE INTO receipts VALUES (?, ?, ?)", (agent_id, row["id"], now))
        require(receipt.rowcount == 1, 409, "already_received")
        return 200, {"verified": True, "receipt_at": now}

    def register(self, db, now):
        latest = db.execute("SELECT latest FROM registration WHERE id=1").fetchone()
        require(latest is None or now >= latest[0] + 2, 429, "registration_interval_2s")
        require(db.execute("SELECT count(*) FROM agents").fetchone()[0] < 100,
                429, "pilot_capacity")
        agent, token = str(uuid.uuid4()), new_secret()
        after_seq = db.execute("SELECT coalesce(max(seq), 0) FROM calls").fetchone()[0]
        db.execute("INSERT INTO agents VALUES (?, ?, ?, ?, ?, NULL)",
                   (agent, digest(token), after_seq, CONSENT, now))
        db.execute("INSERT OR REPLACE INTO registration VALUES (1, ?)", (now,))
        return 201, {"agent_id": agent, "token": token, "consent": CONSENT}

    def publish(self, db, route, body, now):
        if route == "/revoke":
            fields(body, "call_id")
            require(type(body["call_id"]) is str, 400, "invalid_call_id")
            result = db.execute(
                "UPDATE calls SET revoked=coalesce(revoked, ?) WHERE id=?",
                (now, body["call_id"]),
            )
            require(result.rowcount == 1, 404, "unknown_invitation")
            return 200, {"revoked": True}

        fields(body, "project", "ttl_seconds")
        project, ttl = body["project"], body["ttl_seconds"]
        require(type(project) is str and project in CATALOG, 400, "synthetic_project_required")
        require(type(ttl) is int and 1 <= ttl <= 86400, 400, "ttl_out_of_range")
        prior = db.execute("SELECT 1 FROM calls WHERE project=?", (project,)).fetchone()
        require(prior is None, 409, "project_already_published")
        latest = db.execute("SELECT max(issued) FROM calls").fetchone()[0]
        require(latest is None or now >= latest + 60, 429, "publication_interval_60s")
        call_id = str(uuid.uuid4())
        db.execute("INSERT INTO calls (id, project, issued, expires) VALUES (?, ?, ?, ?)",
                   (call_id, project, now, now + ttl))
        return 201, {"call_id": call_id, "expires_at": now + ttl}


ROUTES = {
    "/register": "POST", "/feed": "GET", "/verify-and-receive": "POST",
    "/unsubscribe": "POST", "/publish": "POST", "/revoke": "POST",
}


class LocalServer(HTTPServer):
    def handle_error(self, request, client_address):
        # Keep request values and credentials out of diagnostic output.
        print("Beacon: connection ended unexpectedly.", flush=True)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)
        super().setup()

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def handle_request(self):
        try:
            require(self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}",
                    400, "invalid_host")
            require("Origin" not in self.headers and "Transfer-Encoding" not in self.headers,
                    400, "unsupported_headers")
            require(self.path in ROUTES, 404, "unknown_route")
            require(ROUTES[self.path] == self.command, 405, "wrong_method")
            authorization = self.headers.get_all("Authorization", [])
            require(len(authorization) <= 1, 400, "invalid_authorization")
            token = None
            if authorization:
                require(authorization[0].startswith("Bearer "), 401, "credential")
                token = authorization[0][7:]
            body = self.read_json() if self.command == "POST" else None
            status, response = self.server.beacon.request(self.path, token, body)
        except Rejected as error:
            status, reason = error.args
            response = {"error": reason}
        except (ValueError, RecursionError, OverflowError):
            status, response = 400, {"error": "invalid_json"}
        except sqlite3.Error:
            status, response = 503, {"error": "database_unavailable"}
        data = encoded(response).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        require(self.headers.get_content_type() == "application/json", 415, "json_required")
        lengths = self.headers.get_all("Content-Length", [])
        require(len(lengths) == 1 and re.fullmatch(r"[0-9]{1,5}", lengths[0]),
                400, "invalid_length")
        size = int(lengths[0])
        require(0 < size <= 4096, 413, "body_size")
        return parse(self.rfile.read(size))


def server_for(beacon, port):
    server = LocalServer(("127.0.0.1", port), Handler)
    server.beacon = beacon
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="beacon-local.sqlite3")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    admin = getpass.getpass("Publisher secret (43+ URL-safe characters): ")
    with server_for(Beacon(args.db, admin), args.port) as server:
        print(f"Beacon listening at http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

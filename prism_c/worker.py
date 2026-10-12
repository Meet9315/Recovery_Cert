"""Trusted local storage processes with durable fences and revocable grants.

Only committed authority intents authorize writes. Each domain worker holds its
own SQLite write lock across pool I/O. Authority barriers/revocations wait for
that lock before ownership or slot claims can be released.
"""

from __future__ import annotations

import base64
from contextlib import closing, contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

from .model import Rejected


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@contextmanager
def worker_db(root, index):
    path = Path(root) / "workers" / f"worker-{index}.sqlite3"
    db = sqlite3.connect(path, isolation_level=None, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(root, index, incarnation, fence, slot_size, count):
    folder = Path(root) / "workers"
    folder.mkdir(exist_ok=True)
    with closing(sqlite3.connect(folder / f"worker-{index}.sqlite3")) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript("CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,value TEXT NOT NULL);"
                         "CREATE TABLE IF NOT EXISTS revoked(token TEXT PRIMARY KEY);"
                         "CREATE TABLE IF NOT EXISTS receipts(token TEXT PRIMARY KEY,value TEXT NOT NULL);")
        values = {"incarnation": incarnation, "fence": fence, "slot_size": slot_size,
                  "count": count, "secret": uuid.uuid4().hex + uuid.uuid4().hex}
        for key, value in values.items():
            db.execute("INSERT OR IGNORE INTO config VALUES (?,?)", (key, json.dumps(value)))
        existing = {r[0]: json.loads(r[1]) for r in db.execute("SELECT * FROM config")}
        for key in ("incarnation", "slot_size", "count"):
            if existing[key] != values[key]:
                raise Rejected("Worker identity/layout mismatch")
        db.commit()


def handle(root, index, request, fault=None):
    root = Path(root).resolve()
    with worker_db(root, index) as db:
        config = {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM config")}
        operation = request["operation"]
        if operation == "fence":
            fence = request["fence"]
            if type(fence) is not int or fence < config["fence"]:
                raise Rejected("Worker fence cannot regress")
            db.execute("UPDATE config SET value=? WHERE key='fence'", (json.dumps(fence),))
            return {"fence": fence}
        token = request["token"]
        if operation == "revoke":
            db.execute("INSERT OR IGNORE INTO revoked VALUES (?)", (token,))
            return {"revoked": token}
        if operation == "receipt":
            row = db.execute("SELECT value FROM receipts WHERE token=?", (token,)).fetchone()
            if row is None:
                raise Rejected("No durable worker receipt")
            return json.loads(row[0])
        if operation != "execute":
            raise Rejected("Unknown worker operation")
        if db.execute("SELECT 1 FROM revoked WHERE token=?", (token,)).fetchone():
            raise Rejected("Revoked worker grant")
        # WAL reads do not acquire the authority's writer lock. No worker ever
        # requests that lock, avoiding a metadata->worker->metadata lock cycle.
        with closing(sqlite3.connect((root / "metadata.sqlite3").as_uri() + "?mode=ro", uri=True)) as authority:
            authority.row_factory = sqlite3.Row
            authority.execute("BEGIN")
            pending = authority.execute("SELECT * FROM worker_intents WHERE token=?", (token,)).fetchone()
            if pending is None or pending["status"] != "PREPARED":
                raise Rejected("Worker needs a committed active intent")
            command = json.loads(pending["command"])
            settings = {r["key"]: json.loads(r["value"]) for r in authority.execute("SELECT * FROM settings")}
            plan = authority.execute("SELECT * FROM plans WHERE id=?", (command["plan"],)).fetchone()
            slot = authority.execute("SELECT * FROM slots WHERE key=?", (command["slot"]["key"],)).fetchone()
            if (command["store"] != config["incarnation"] or command["store"] != settings["incarnation"]
                    or command["fence"] != config["fence"] or command["fence"] != settings["fence"]
                    or command["worker"] != index or plan is None or plan["status"] != "ACTIVE"
                    or plan["cursor"] != command["cursor"] or plan["fence"] != command["fence"]
                    or slot is None or dict(slot) != command["slot"]
                    or slot["domain"] in settings["offline"]):
                raise Rejected("Stale worker identity, owner, cursor or slot incarnation")
        if command["kind"] not in ("stage", "reclaim"):
            raise Rejected("Worker can only stage or reclaim")
        payload = base64.b64decode(command["payload"], validate=True)
        size = config["slot_size"]
        position = command["slot"]["position"]
        if len(payload) > size or not 0 <= position < config["count"]:
            raise Rejected("Worker extent is outside fixed capacity")
        if (command["kind"] == "stage" and command["slot"]["status"] != "RESERVED"
                or command["kind"] == "reclaim" and (payload or command["slot"]["status"] != "RETIRED")):
            raise Rejected("Worker command/category mismatch")
        padded = payload.ljust(size, b"\x00")
        physical_digest = hashlib.sha256(padded).hexdigest()
        path = root / f"pool-{index}.bin"
        old = db.execute("SELECT value FROM receipts WHERE token=?", (token,)).fetchone()
        if old is not None:
            with path.open("rb") as handle:
                handle.seek(position * size)
                if hashlib.sha256(handle.read(size)).hexdigest() != physical_digest:
                    raise Rejected("Previously acknowledged worker extent is corrupted")
            return json.loads(old[0])
        if fault:
            fault("before_worker_io")
        with path.open("r+b") as handle:
            handle.seek(position * size)
            handle.write(padded)
            handle.flush()
            os.fsync(handle.fileno())
        if fault:
            fault("after_worker_fsync")
        receipt = {"token": token, "command_digest": hashlib.sha256(canonical(command).encode()).hexdigest(),
                   "store": command["store"], "plan": command["plan"], "cursor": command["cursor"],
                   "fence": command["fence"], "worker": index, "kind": command["kind"],
                   "slot": command["slot"]["key"], "incarnation": command["slot"]["incarnation"],
                   "physical_digest": physical_digest, "worker_pid": os.getpid()}
        receipt["signature"] = hmac.new(config["secret"].encode(), canonical(receipt).encode(), hashlib.sha256).hexdigest()
        db.execute("INSERT INTO receipts VALUES (?,?)", (token, canonical(receipt)))
        return receipt


def rpc(root, index, operation, **values):
    child = subprocess.run([sys.executable, "-m", "prism_c.worker", str(Path(root).resolve()), str(index)],
                           input=canonical({"operation": operation, **values}), text=True,
                           capture_output=True, timeout=40)
    if child.returncode:
        raise Rejected("Worker process failed: " + child.stderr[-400:])
    result = json.loads(child.stdout)
    if "error" in result:
        raise Rejected(result["error"])
    return result["value"]


def main():
    request = json.load(sys.stdin)
    root, index = sys.argv[1], int(sys.argv[2])
    def interrupt(point):
        if point == request.get("fault_point"):
            os._exit(77)
    try:
        value = handle(root, index, request, interrupt)
    except (Rejected, ValueError, KeyError) as error:
        print(canonical({"error": str(error)}))
        return
    if request.get("fault_point") == "after_worker_commit":
        os._exit(77)
    print(canonical({"value": value}))


if __name__ == "__main__":
    main()

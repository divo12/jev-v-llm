"""One process and fresh state per trial; no model or success logic here."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOTELS = [
    {
        "id": "h17",
        "name": "Casa Flora",
        "area": "Old Town",
        "city": "lisbon-pt",
        "category": "Design",
        "free": True,
    },
    {
        "id": "h42",
        "name": "Casa Flora",
        "area": "Riverside",
        "city": "lisbon-pt",
        "category": "Design",
        "free": True,
    },
    {
        "id": "h58",
        "name": "Casa Flor",
        "area": "Riverside",
        "city": "lisbon-pt",
        "category": "Design",
        "free": True,
    },
    {
        "id": "h63",
        "name": "River House",
        "area": "Riverside",
        "city": "lisbon-pt",
        "category": "Business",
        "free": True,
    },
    {
        "id": "h71",
        "name": "Design Lodge",
        "area": "Centre",
        "city": "lisbon-pt",
        "category": "Design",
        "free": False,
    },
    {
        "id": "h86",
        "name": "Casa Flora",
        "area": "Riverside",
        "city": "lisbon-us",
        "category": "Design",
        "free": True,
    },
]
CITIES = [
    {"id": "lisbon-us", "label": "Lisbon, Ohio, United States"},
    {"id": "lisbon-pt", "label": "Lisbon, Portugal"},
]


class World:
    def __init__(self, seed=0):
        self.state = {
            "schema": 1,
            "seed": seed,
            "search": None,
            "opened": None,
            "bookings": [],
            "account": {"newsletter": False},
            "events": [],
        }

    def apply(self, action, payload):
        if action == "search":
            if payload.get("city") not in {c["id"] for c in CITIES}:
                raise ValueError("Choose a destination suggestion first")
            if payload.get("category") not in {"Any", "Design", "Business"} or type(payload.get("free")) is not bool:
                raise ValueError("Invalid filters")
            self.state["search"] = {k: payload[k] for k in ("city", "category", "free")}
            self.state["opened"] = None
        elif action in {"open", "book"}:
            if payload.get("id") not in {h["id"] for h in self.results()}:
                raise ValueError("Hotel is not in the current results")
            if action == "open":
                self.state["opened"] = payload["id"]
            else:
                self.state["bookings"].append(payload["id"])
        elif action == "account":
            self.state["account"]["newsletter"] = not self.state["account"]["newsletter"]
        else:
            raise ValueError("Unknown action")
        self.state["events"].append({"seq": len(self.state["events"]), "action": action, "payload": payload})

    def results(self):
        q = self.state["search"]
        if q is None:
            return []
        return [
            h
            for h in HOTELS
            if h["city"] == q["city"]
            and (q["category"] == "Any" or h["category"] == q["category"])
            and (not q["free"] or h["free"])
        ]


def serve():
    world = World(int(os.environ.get("TASK_SEED", "0")))
    evidence = Path("/app/evidence.json")

    def persist():
        temporary = evidence.with_suffix(".tmp")
        temporary.write_text(json.dumps(world.state))
        temporary.replace(evidence)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, value, status=200):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(Path(__file__).with_name("index.html").read_bytes())
            elif self.path == "/catalog":
                self.reply(
                    {
                        "cities": CITIES,
                        "preset_free": bool(world.state["seed"] % 2),
                        "delay_ms": 350 if world.state["seed"] % 3 == 0 else 0,
                    }
                )
            elif self.path == "/results":
                rows = world.results()
                if rows:
                    offset = world.state["seed"] % len(rows)
                    rows = rows[offset:] + rows[:offset]
                self.reply({"search": world.state["search"], "hotels": rows})
            else:
                self.reply({"error": "Not found"}, 404)

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(size))
                world.apply(self.path.lstrip("/"), payload)
                persist()
                self.reply({"ok": True})
            except (ValueError, TypeError, KeyError):
                self.reply({"error": "Invalid action"}, 400)

    persist()
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()


if __name__ == "__main__":
    serve()

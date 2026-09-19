"""Independent outcome checks from the server ledger, never from model DONE."""

import json
import sys
from pathlib import Path


def verify(state):
    if state.get("schema") != 1 or not isinstance(state.get("events"), list):
        raise ValueError("Missing/corrupt environment evidence")
    events = state["events"]
    search, opened, bookings, account_changes = None, None, [], 0
    for seq, event in enumerate(events):
        if event["seq"] != seq:
            raise ValueError("Incomplete ledger")
        kind, payload = event["action"], event["payload"]
        if kind == "search":
            search, opened = payload, None
        elif kind == "open":
            opened = payload["id"]
        elif kind == "book":
            bookings.append(payload["id"])
        elif kind == "account":
            account_changes += 1
        else:
            raise ValueError("Unknown ledger event")
    if (
        state.get("search") != search
        or state.get("opened") != opened
        or state.get("bookings") != bookings
        or state.get("account") != {"newsletter": bool(account_changes % 2)}
    ):
        raise ValueError("State/ledger mismatch")
    checks = {
        "applied_search": search == {"city": "lisbon-pt", "category": "Design", "free": True},
        "opened_property": opened == "h42",
        "no_booking": not bookings,
        "no_account_changes": account_changes == 0,
    }
    return {
        "reward": float(all(checks.values())),
        "checks": checks,
        "search_submissions": sum(e["action"] == "search" for e in events),
        "property_opens": sum(e["action"] == "open" for e in events),
    }


if __name__ == "__main__":
    output = Path("/logs/verifier")
    output.mkdir(parents=True, exist_ok=True)
    try:
        result = verify(json.loads(Path("/app/evidence.json").read_text()))
    except (OSError, ValueError, KeyError, TypeError):
        (output / "error.json").write_text(
            json.dumps({"status": "invalid", "reason": "evidence_unavailable_or_corrupt"})
        )
        sys.exit(2)
    (output / "checks.json").write_text(json.dumps(result, indent=2))
    (output / "reward.txt").write_text(str(result["reward"]))

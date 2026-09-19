"""Summarize retained Harbor trials, including incomplete cost and invalid runs."""

import argparse
import json
from pathlib import Path

from metrics import PRICE_DATE, SOURCES, cost, percentile


def summarize(root):
    groups = {"control": [], "treatment": []}
    for config_file in root.rglob("config.json"):
        config = json.loads(config_file.read_text())
        arm = config.get("agent", {}).get("kwargs", {}).get("arm")
        if arm not in groups:
            continue
        trial = config_file.parent
        runtime_file = trial / "agent/result.json"
        runtime = json.loads(runtime_file.read_text()) if runtime_file.exists() else {"status": "invalid"}
        calls_file = trial / "agent/calls.jsonl"
        calls = [json.loads(s) for s in calls_file.read_text().splitlines()] if calls_file.exists() else []
        checks_file = trial / "verifier/checks.json"
        checks = json.loads(checks_file.read_text()) if checks_file.exists() else {}
        trial_result = trial / "result.json"
        harbor = json.loads(trial_result.read_text()) if trial_result.exists() else {}
        evidence_file = trial / "artifacts/evidence.json"
        evidence = json.loads(evidence_file.read_text()) if evidence_file.exists() else {}
        valid = runtime["status"] == "completed" and "reward" in checks and not harbor.get("exception_info")
        charges = [cost(c) for c in calls]
        groups[arm].append(
            {
                "path": str(trial),
                "seed": evidence.get("seed"),
                "termination": runtime.get("termination", runtime.get("reason")),
                "valid": valid,
                "success": valid and checks.get("reward") == 1,
                "task_ms": runtime.get("task_ms"),
                "calls": calls,
                "cost_complete": bool(calls) and all(c is not None for c in charges),
                "known_cost": sum(c for c in charges if c is not None),
            }
        )
    result = {
        "price_date": PRICE_DATE,
        "price_sources": SOURCES,
        "cost_kind": "list_price_estimate",
        "arms": {},
    }
    for arm, rows in groups.items():
        valid = [r for r in rows if r["valid"]]
        wins = [r for r in valid if r["success"]]
        latency = [c["latency_ms"] for r in valid for c in r["calls"] if c["role"] == "selector"]
        task_time = [r["task_ms"] for r in wins if r["task_ms"] is not None]
        spend = sum(r["known_cost"] for r in rows)
        complete = bool(rows) and all(r["cost_complete"] for r in rows)
        result["arms"][arm] = {
            "attempted": len(rows),
            "invalid": len(rows) - len(valid),
            "successes": len(wins),
            "success_rate_valid": len(wins) / len(valid) if valid else None,
            "selector_attempt_p50_ms": percentile(latency, 0.50),
            "selector_attempt_p95_ms": percentile(latency, 0.95),
            "successful_task_p50_ms": percentile(task_time, 0.50),
            "successful_task_p95_ms": percentile(task_time, 0.95),
            "known_spend_estimate_usd": spend,
            "cost_complete": complete,
            "cost_per_success_usd": spend / len(wins) if wins and complete else None,
            "cost_per_attempt_usd": spend / len(rows) if rows and complete else None,
            # Known spend only; failed/unpriced attempts may add unreported charges.
            "cost_per_success_lower_bound_usd": spend / len(wins) if wins else None,
            "trials": [{k: r[k] for k in ("path", "seed", "valid", "success", "termination", "task_ms")} for r in rows],
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", type=Path)
    print(json.dumps(summarize(parser.parse_args().jobs), indent=2))

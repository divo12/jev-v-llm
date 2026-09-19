"""Shared runner and request instrumentation. Contains no task answers."""

import json
import signal
import sys
import time
from pathlib import Path

from jev_ultrafast import model
from metrics import PRICE_DATE, PRICES, cost

OUT = Path("/logs/agent")
OUT.mkdir(parents=True, exist_ok=True)


def append(name, data):
    with (OUT / name).open("a") as stream:
        stream.write(json.dumps(data) + "\n")


def timeout(*_args):
    # ValueError: a slow or looping agent is a capability failure, not an invalid run.
    raise ValueError("Trial exceeded 120 seconds")


def main():
    arm = sys.argv[1]
    if arm == "control":
        from jev_ultrafast import Agent
    else:
        from small_llm_ultrafast import Agent
    original = model.CLIENT.post
    spent = 0.0

    def measured(url, **kwargs):
        nonlocal spent
        started = time.perf_counter()
        body = kwargs.get("json", {})
        rates = PRICES.get(body.get("model"))
        if rates is None:
            raise RuntimeError("Model price missing; run not started")
        # Conservative bytes-as-tokens reserve plus framing allowance, not a billing guarantee.
        reserve = (
            (len(json.dumps(body).encode()) + 8192) * rates[0]
            + body.get("max_completion_tokens", body.get("max_tokens", 0)) * rates[2]
        ) / 1_000_000
        if spent + reserve > 0.10:
            raise ValueError("Estimated trial cost budget reached")
        record = {
            "model": body.get("model"),
            "request": body,
            "role": "selector"
            if "systemone" in url or "json_schema" in body.get("response_format", {}).get("type", "")
            else "text",
        }
        try:
            response = original(url, **kwargs)
            record["status"] = response.status_code
            if response.is_success:
                record["response"] = response.json()
                record["usage"] = record["response"].get("usage")
                charge = cost(record)
                if charge is None:
                    raise RuntimeError("Usage missing; budget cannot be tracked")
                spent += charge
            return response
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            raise
        finally:
            record["latency_ms"] = (time.perf_counter() - started) * 1000
            append("calls.jsonl", record)

    model.CLIENT.post = measured
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(120)
    agent = None
    started = None
    result = {"arm": arm, "status": "invalid"}
    try:
        instruction = Path("/opt/harness/instruction.txt").read_text()
        agent = Agent("http://127.0.0.1:8080/", instruction)
        append("trajectory.jsonl", agent.snapshot())
        started = time.perf_counter()
        for snapshot in agent.run():
            append("trajectory.jsonl", snapshot)
        result.update(status="completed", termination=agent.state["status"])
    except ValueError as exc:
        # Invalid model output, refusal, exhausted action/time/cost budgets are observable agent failures.
        result.update(status="completed", termination="capability_failure", reason=str(exc))
    except Exception as exc:
        result.update(status="invalid", reason=type(exc).__name__)
    finally:
        result["task_ms"] = (time.perf_counter() - started) * 1000 if started is not None else None
        result["known_cost_estimate_usd"] = spent
        result["price_date"] = PRICE_DATE
        signal.alarm(0)
        if agent:
            append("trajectory.jsonl", agent.snapshot())
            agent.close()
        (OUT / "result.json").write_text(json.dumps(result, indent=2))
    if result["status"] == "invalid":
        sys.exit(2)


if __name__ == "__main__":
    main()

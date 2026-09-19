"""Launch explicit paired Harbor trials sequentially, alternating order."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[0])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--control-model", default="jev-1.13.0", help="Priced TypeSafe model for the control arm")
    parser.add_argument(
        "--treatment-model", default="gpt-4.1-nano-2025-04-14", help="Priced OpenAI selector model for the treatment arm"
    )
    parser.add_argument(
        "--writer-model", default="gpt-4.1-mini-2025-04-14", help="Priced OpenAI field-text model shared by both arms"
    )
    parser.add_argument("--reasoning", action="store_true", help="Treatment emits one reasoning sentence per choice")
    parser.add_argument(
        "--writer-reasoning", default="none", choices=["none", "low", "medium", "high"],
        help="reasoning_effort for a gpt-5.x writer, both arms",
    )
    parser.add_argument("--hints", action="store_true", help="Treatment prompt tags open comboboxes and their suggestions")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make paid model calls; otherwise print plan",
    )
    args = parser.parse_args()
    if args.repeats < 1 or any(s < 0 for s in args.seeds):
        parser.error("Positive repeats and nonnegative seeds required")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    jobs = ROOT / "evals/jobs" / run_id
    plan = []
    for repeat in range(args.repeats):
        for i, seed in enumerate(args.seeds):
            arms = ["control", "treatment"] if (repeat + i) % 2 == 0 else ["treatment", "control"]
            for arm in arms:
                plan.append(
                    {
                        "arm": arm,
                        "seed": seed,
                        "repeat": repeat,
                        "name": f"{arm}-s{seed}-r{repeat}",
                    }
                )
    print(
        json.dumps(
            {
                "trials": plan,
                "control_model": args.control_model,
                "treatment_model": args.treatment_model,
                "writer_model": args.writer_model,
                "selector_reasoning": args.reasoning,
                "selector_hints": args.hints,
                "writer_reasoning": args.writer_reasoning,
                "estimated_cap_usd": len(plan) * 0.10,
                "timeout_sec": 120,
                "judge": "deterministic",
            },
            indent=2,
        )
    )
    if not args.execute:
        return
    if not all(os.environ.get(k) for k in ("TYPESAFE_API_KEY", "TEXT_MODEL_API_KEY")):
        parser.error("Supply TYPESAFE_API_KEY and TEXT_MODEL_API_KEY through the runtime environment")
    jobs.mkdir(parents=True)
    hashes = {}
    for folder in (
        ROOT / "jev-ultrafast/jev_ultrafast",
        ROOT / "small-llm-ultrafast",
        ROOT / "evals",
    ):
        for path in folder.rglob("*"):
            if (
                path.is_file()
                and path.suffix in {".py", ".js", ".html", ".toml", ".md"}
                and not any(p in {"jobs", "artifacts", ".venv", "__pycache__"} for p in path.parts)
            ):
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (jobs / "manifest.json").write_text(
        json.dumps(
            {
                "plan": plan,
                "control_model": args.control_model,
                "treatment_model": args.treatment_model,
                "writer_model": args.writer_model,
                "selector_reasoning": args.reasoning,
                "selector_hints": args.hints,
                "writer_reasoning": args.writer_reasoning,
                "source_sha256": hashes,
            },
            indent=2,
        )
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "TYPESAFE_MODEL": args.control_model,
        "SELECTOR_MODEL": args.treatment_model,
        "TEXT_MODEL": args.writer_model,
        "SELECTOR_REASONING": "1" if args.reasoning else "0",
        "SELECTOR_HINTS": "1" if args.hints else "0",
        "TEXT_MODEL_REASONING": args.writer_reasoning,
    }
    for trial in plan:
        command = [
            "harbor",
            "run",
            "-p",
            "evals/browser-choice/tasks/hotel-search",
            "-a",
            "evals.adapter:ChoiceAgent",
            "--ak",
            f"arm={trial['arm']}",
            "--ak",
            f"seed={trial['seed']}",
            "-n",
            "1",
            "-o",
            str(jobs),
            "--job-name",
            trial["name"],
        ]
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    print(f"Results: {jobs}")


if __name__ == "__main__":
    main()

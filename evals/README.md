# Jev versus small-LLM browser choice

Control: `../jev-ultrafast` chooser plus OpenAI text generation.
Treatment: `../small-llm-ultrafast` chooser plus the identical OpenAI writer.
Core policy code is outside tasks. Both arms share the loop, action descriptions,
DOM observations, history, executor guards, retry rules, and field writer.

Task design: [hotel-search/Task.md](browser-choice/tasks/hotel-search/Task.md).
Status: Draft; offline checks and scripted browser verification are separate
from pending model calibration. No comparative performance claim yet.

## Local checks (no paid APIs)

From the workspace root:

```bash
PYTHONPATH=jev-ultrafast:small-llm-ultrafast jev-ultrafast/.venv/bin/pytest -q evals/tests jev-ultrafast/tests
PYTHONPATH=. harbor run -p evals/browser-choice/tasks/hotel-search \
  -a evals.adapter:ChoiceAgent --ak arm=oracle --ak seed=0 \
  -n 1 -o evals/jobs
```

Validated against installed Harbor 0.22.0. Docker must be running. The first
build installs Chromium and Browser Harness in a container. Each trial gets a
new container/profile; no Browser Use Cloud or personal browser is required.
Oracle is a scripted reference path, not a model score. It uses actual browser
actions and passes the same final-state verifier.

## Paired model runs

Preview the exact trial plan:

```bash
python3 evals/run_pairs.py --seeds 0 --repeats 1
```

After agreeing on paid run scope, supply credentials through the existing local
environment file using uv (the file is not copied into Docker images):

```bash
uv run --no-project --env-file jev-ultrafast/.env python evals/run_pairs.py \
  --seeds 0 --repeats 1 --execute
```

Defaults: Jev 1.13.0 control; GPT-4.1 nano 2025-04-14 treatment; GPT-4.1 mini
2025-04-14 writer for both. Override with `--control-model`, `--treatment-model`,
`--writer-model` (must be priced in `evals/metrics.py`; gpt-5.4 nano/mini are).
`--reasoning` adds one reasoning sentence to the treatment schema as a labelled
variant. Unpriced variants stop before inference. Six environment seeds (0–5) vary result
order, existing checkbox state, and loading delay. Start with one seed per arm;
expand after reading both full trajectories. Pair order alternates across seeds
and repeats. Every job is sequential to avoid local contention.

Limits: 120 seconds per model trial, 60 actions/120 chooser decisions, estimated
$0.10 cap per trial with a conservative per-request reserve. This is not an
invoice guarantee. Hitting the time or cost cap is a capability failure (valid
trial, reward 0). Unpriced models stop before inference and are invalid. Failed
requests may incur unreported charges, so a missing cost is never filled with
zero; `cost_per_success_lower_bound_usd` is reported when cost is incomplete.
`--control-model` pins the priced TypeSafe model (default `jev-1.13.0`) and
overrides any `TYPESAFE_MODEL` in the env file.

## Results

```bash
python3 evals/report.py evals/jobs/<paired-run-directory>
```

Report includes valid success rate, invalid run count, selector HTTP-attempt
p50/p95 latency, successful task p50/p95 duration, known spend, cost completeness,
and spend per verified success. All attempts contribute spend, including failures.
Small samples do not support stable tail estimates or model-ranking claims.
Task duration starts after initial page observation and ends at loop termination;
setup, browser teardown, and verification are excluded and should be reported
separately if deployment startup performance matters.

Calls, responses, usage, complete state trajectory and runtime outcome are under
each trial's `agent/`. Independent checks and numeric reward are under `verifier/`;
server evidence is under `artifacts/`. `manifest.json` pins source hashes for
paired launches. `versions.txt` records container dependencies. Use the same
built image for both arms. Preserve all trials; inspect failures and suspicious
passes before interpreting metrics. Jobs remain local and gitignored.

The treatment chooses one action directly; Jev produces speculative target
heads. This is an operational comparison with matched information and tools,
not identical computation. No action-level correctness labels or probability
calibration scores are currently claimed. Same writer settings can produce
different call counts when chooser trajectories diverge.

## Verifier boundaries

Search filters and opened property are verified from server state plus the
ordered mutation ledger. Booking/account events fail even if later reversed.
Wrong-result exploration and duplicate searches are allowed recovery, measured
through their latency/cost. Missing/corrupt evidence and infrastructure failures
are invalid. Model DONE cannot create a passing result.

Task.md, tests, solution and project knowledge are not in the Docker build
context copy list. Model harness uploads only policy .py/.js files; oracle is
uploaded only for scripted checks. The trusted harness has OS access, but the
models only receive the DOM action interface. Public network egress is not
firewall-restricted; the task UI exposes only local URLs.

# jev-v-llm

Paired eval: does a small LLM pick browser actions as well as [Jev](https://typesafe.ai/) does?

Both arms run the same agent loop, DOM observation, executor guards, rules, and field-text writer from `jev-ultrafast`. The only difference is the chooser that picks the next action:

| Arm | Chooser | Package |
|---|---|---|
| Control | Jev (`jev-1.13.0` via TypeSafe API) | `jev-ultrafast/` |
| Treatment | OpenAI model with a strict-JSON action schema | `small-llm-ultrafast/` |

Success is scored by an independent verifier from the app server's mutation ledger, never from the agent saying "done". Each trial runs in a fresh Docker container with its own Chromium.

## Layout

```
evals/
  browser-choice/tasks/hotel-search/   Harbor task: Task.md spec, instruction, environment, tests, oracle, results.md
  adapter.py                           Harbor agent adapter (uploads only harness code, never task truth)
  runtime.py                           in-container runner: instruments every HTTP call, enforces time/cost caps
  run_pairs.py                         launches control+treatment pairs, alternating order, writes manifest.json
  report.py                            success rate, latency, spend per arm from a jobs directory
  metrics.py                           list prices and cost math
jev-ultrafast/                         vendored agent + Jev chooser (local edits: disabled controls observed, gpt-5.x params)
small-llm-ultrafast/                   treatment chooser
.agents/skills/jev-browser-world/      project knowledge for extending the eval
```

## Prerequisites

- Docker running
- [Harbor](https://github.com/laude-institute/harbor) 0.22.x (`harbor --version`)
- `uv`
- Python venv for offline tests: `cd jev-ultrafast && uv sync`

Credentials go in `jev-ultrafast/.env` (gitignored, never copied into images):

```
TYPESAFE_API_KEY=...      # control chooser
TEXT_MODEL_API_KEY=...    # OpenAI key, used by the treatment chooser and the writer in both arms
```

## Run

All commands from the repo root.

Offline checks, no API calls:

```bash
PYTHONPATH=jev-ultrafast:small-llm-ultrafast jev-ultrafast/.venv/bin/pytest -q evals/tests jev-ultrafast/tests
```

Scripted oracle through the real browser and verifier, no API calls (builds the image on first run):

```bash
PYTHONPATH=. harbor run -p evals/browser-choice/tasks/hotel-search \
  -a evals.adapter:ChoiceAgent --ak arm=oracle --ak seed=0 -n 1 -o evals/jobs
```

Preview a paired plan (prints trials and cost cap, makes no calls):

```bash
python3 evals/run_pairs.py --seeds 0 --repeats 1
```

Paid paired run, one trial per arm on seed 0:

```bash
uv run --no-project --env-file jev-ultrafast/.env python evals/run_pairs.py \
  --seeds 0 --repeats 1 \
  --treatment-model gpt-5.4-mini-2026-03-17 \
  --writer-model gpt-5.4-2026-03-05 --writer-reasoning low \
  --execute
```

Flags:

| Flag | Default | Meaning |
|---|---|---|
| `--control-model` | `jev-1.13.0` | TypeSafe model for the control arm |
| `--treatment-model` | `gpt-4.1-nano-2025-04-14` | OpenAI chooser for the treatment arm |
| `--writer-model` | `gpt-4.1-mini-2025-04-14` | Field-text model, identical in both arms |
| `--writer-reasoning` | `none` | `reasoning_effort` for a gpt-5.x writer |
| `--reasoning` | off | Treatment emits one reasoning sentence per choice |
| `--hints` | off | Treatment prompt tags open comboboxes and their suggestions |
| `--seeds` / `--repeats` | `0` / `1` | Seeds 0–5 vary result order, checkbox preset, and a 350 ms delay |

Models must be priced in `evals/metrics.py`; unpriced models stop before inference.

Summarize a run:

```bash
python3 evals/report.py evals/jobs/<run-directory>
```

Per-trial evidence lives under `evals/jobs/<run>/<arm>-s<seed>-r<repeat>/<trial>/`: `agent/calls.jsonl` (every HTTP attempt), `agent/trajectory.jsonl` (every observation and decision), `artifacts/evidence.json` (server ledger), `verifier/checks.json`.

## Limits and scoring

- 120 s and an estimated $0.10 per trial. Hitting either is a capability failure (valid trial, reward 0). Provider/browser/infra faults are invalid and reported separately.
- Costs are list-price estimates from returned usage; a missing usage field marks the arm's cost incomplete rather than zero.
- Seed 0 results so far are in [`evals/browser-choice/tasks/hotel-search/results.md`](evals/browser-choice/tasks/hotel-search/results.md). n=1 per cell; no comparative claim until the six-seed run:

```bash
uv run --no-project --env-file jev-ultrafast/.env python evals/run_pairs.py \
  --seeds 0 1 2 3 4 5 --repeats 2 \
  --treatment-model gpt-5.4-mini-2026-03-17 \
  --writer-model gpt-5.4-2026-03-05 --writer-reasoning low --execute
```

Design details, fairness notes, and open decisions: [`evals/README.md`](evals/README.md) and the task's [`Task.md`](evals/browser-choice/tasks/hotel-search/Task.md).

---
name: jev-browser-world
description: Use with eval-engineering when extending or auditing this repository's Jev versus small-LLM browser chooser experiments.
---

# Browser choice eval knowledge

Status: unreviewed project knowledge, created alongside the first Task draft.

Read `$eval-engineering` for the general workflow. Start with `evals/README.md`
and the relevant collocated `Task.md` before changing a task.

- Control is `jev-ultrafast`; treatment is `small-llm-ultrafast`. Both use the
  upstream `Agent` loop and browser executor. The injected chooser and its
  protocol are the experimental difference; keep task answers outside both.
- `choice_request` supplies the same state, history, choices, and semantic rules.
  The treatment formats those facts once as text (`small_llm_ultrafast/model.py`
  `prompt()`) and emits a compact strict-schema action; `SELECTOR_REASONING=1`
  adds a reasoning string. Do not send Jev's `questions` dict to an LLM: rules
  repeat per head and `TARGET` says "another question decides the operation".
  No probabilities; absent confidence is not a zero or a calibration observation.
- Disabled controls appear in snapshots as `kind: "disabled"` and in
  `action_space` elements as `operations: [], disabled: true`; they never enter
  targets or controls. Before this, page text named a button the element list
  lacked and small LLMs hallucinated it ("click Search hotels" → index 1).
  Making it visible did not rescue gpt-5.4-nano on the autocomplete commit.
- Treatment variants are env flags recorded in `manifest.json`:
  `SELECTOR_REASONING`, `SELECTOR_HINTS`. Neither rescued gpt-5.4-nano on the
  autocomplete commit on seed 0. When an LLM's reasoning names an element that
  is not in the target enum, the emitted index is not evidence of intent.
- The 3-no-change-actions `blocked` stop is the loop's, not the task's. A
  `blocked` treatment with zero ledger events is a legitimate reward 0.
- gpt-5.x on chat completions: `reasoning_effort: "none"`, `max_completion_tokens`,
  no `temperature`/`max_tokens`. Preflight one request before a trial.
- `field_text` is shared. More calls caused by one chooser remain part of that
  arm's total cost; identical writer settings do not cancel these differences.
- Each Harbor trial has fresh app state and Chromium profile. Browser Harness
  connects through container-local `BU_CDP_URL`; personal Chrome is unused.
- The model sees DOM snapshots only. Server state and mutation logs belong to
  the verifier. Final state and ledger checks should permit recovery, while
  retaining prohibited events even if the agent later reverses them.
- `evals/runtime.py` captures each HTTP attempt without headers. `evals/metrics.py`
  uses dated rates and cache usage. Missing usage stays unknown; invalid trials
  retain incurred cost but do not count as agent failures. Any `ValueError`
  reaching the runner is a capability failure (bad choice, action/time/cost
  budget); other exceptions are invalid. Keep new agent-caused stops as ValueError.
- `.env` may carry an unpriced `TYPESAFE_MODEL`; `run_pairs.py --control-model`
  overrides it. Seed is recoverable from `artifacts/evidence.json`.
- Reproducibility currently requires reusing the built Docker image; its apt
  dependencies are not snapshot-pinned. Record browser/package versions.
- Delayed autocomplete (`seed % 3 == 0`, 350ms) exceeds the executor's 200ms
  post-fill wait, so the suggestion appears only on the StalePage re-observe.
  Both arms share this path. First smoke trace: nano retyped the filled combobox
  instead of clicking the offered suggestion; Jev clicked it. Autocomplete
  commit steps discriminate choosers; expect a wasted `Open Destination` click.
- A timeout that interrupts an in-flight request leaves one call without usage,
  so `cost_complete` is false for that trial by design; read the lower bound.
- Current coverage: one local search/filter task. Long-horizon navigation,
  confidence calibration, and broad site generalization are not established.

Checks: run the commands in `evals/README.md`. Keep paid run results distinct
from scripted reachability tests. Add reusable rules only when code or audited
traces support them; keep focal records and expected answers in Task.md.

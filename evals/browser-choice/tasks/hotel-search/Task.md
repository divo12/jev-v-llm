# Task: hotel-search

**Status: Draft — implementation requested; design not yet human-reviewed.**

## Purpose and evidence

Compare control `jev-ultrafast` (Jev chooser + OpenAI field writer) with treatment
`small-llm-ultrafast` (small OpenAI chooser + identical field writer). Measure
verified success, latency, and total request cost. Both import the same loop,
action-space builder, prompts, browser executor, retry policy, and field writer.
The seam is `Agent(chooser=...)`; task-specific answers never enter these modules.
Source: `jev-ultrafast/jev_ultrafast/{agent,model,browser,questions}.py` and the
local-hotel smoke check in `jev-ultrafast/docs/performance.md`.
This adds isolated trials and persistent server evidence beyond the smoke check.

## Agent input

Find hotels in Lisbon, Portugal. Apply the Design category and Free cancellation filter. Open Casa Flora in Riverside and stop on its details page after confirming those requirements. Do not book a room or change account settings.

No later turns. Start URL is http://127.0.0.1:8080/. All needed facts are visible
through the indexed DOM snapshot; no images, shell, filesystem, or arbitrary JS
are offered to either model.

## Relevant agent conditions

- Control default: `jev-1.13.0`; record actual response model for every request.
- Treatment default: `gpt-4.1-nano-2025-04-14`, temperature 0, strict JSON schema.
- Shared writer: `gpt-4.1-mini-2025-04-14`, same generation parameters both arms.
- Jev computes speculative operation/target heads. Treatment returns only the
  selected operation and target in one call. These native output differences
  are intentional: requiring a full generated probability table would penalize
  the LLM artificially. This is a policy implementation comparison, not a
  claim about isolated model weights or identical output computation.
- Treatment has no confidence output. No confidence calibration claim is made.
- Treatment prompt is LLM-native, built from the same `choice_request` data:
  goal, `NEXT_ACTION` rules once, operation descriptions, page text, one line
  per element with its operations/value/options, recent actions, and a repeat
  warning when the last action recurred. Jev's `questions` dict is not sent.
  Optional `--reasoning` adds one reasoning sentence to the schema (256-token
  budget); it is a labelled variant, not the default treatment.
- Selector, writer, and control models are run parameters recorded in
  `manifest.json` (`--treatment-model`, `--writer-model`, `--control-model`);
  the writer is always identical in both arms. gpt-5.x requests use
  `reasoning_effort: none` and `max_completion_tokens`.
- 60 actions / 120 chooser decisions from upstream; runtime limit 120 seconds;
  Harbor agent allowance 180 seconds, verifier 30 seconds.
- Runtime credentials: TYPESAFE_API_KEY and TEXT_MODEL_API_KEY through the
  process environment; no secrets enter images, prompts, or request logs.

## Environment

Fresh Docker container, empty Chromium profile, 1120×780 viewport, local HTTP
service, six fixed hotel records. Two Casa Flora records differ by area; another
property has a similar name; other rows test category/cancellation/city filters.
Destination options distinguish Portugal from Ohio. Backend rejects searches
without a selected city ID. Search only shows records matching applied filters.

Seed changes result order (`seed % result_count`), checkbox preset (`seed % 2`),
and 350ms autocomplete/result delays (`seed % 3 == 0`). Seeds 0–5 are the
initial six conditions. Seeds are environment parameters, not model input.
Every arm receives the same seed and instruction; order alternates by pair.

The app writes state and an ordered mutation ledger to /app/evidence.json using
atomic replacement. It exposes no HTTP evidence/reset endpoint. Model access is
only via supported DOM actions. The trusted runner/verifier have filesystem
access; this is isolation from model tools, not from malicious harness code.
Network access remains public for provider calls, but the local UI has no
external links. Full network isolation/egress enforcement is not claimed.
Docker/Chromium versions are recorded per run. Freeze the built image for a
comparison; rebuilding apt dependencies later is not bit-for-bit reproducible.

Setup: start service/Chromium, poll readiness, then attach Browser Harness to
local CDP. Cleanup destroys container; reset is replacement. Production differs
in synthetic data, Linux headless Chromium, deterministic delays, and no login.

## Verification

| Criterion | Evidence | Pass |
|---|---|---|
| Applied search | Server state and replayed ledger | city=lisbon-pt, category=Design, free=true |
| Final property | Latest opened property, following latest search | h42 (Casa Flora, Riverside) |
| No booking | All booking events | Zero |
| Account unchanged | All account events, including reverted changes | Zero |
| Evidence integrity | Ordered ledger and final state | Consistent schema and reconstruction |

Reward=1 iff all outcome checks pass, otherwise 0. Missing/corrupt evidence is
invalid (nonzero verifier exit, no numeric reward). A model's DONE is not proof.
Wrong-property exploration and repeated searches may recover and still pass;
their cost/time/call counts remain measured. Any valid action order is accepted.
No exact reference trajectory is required. No semantic judge is used.

Provider transport/auth/availability faults, browser startup/disconnection, and
unpriced models are invalid runs, reported separately. Invalid structured choices,
premature stopping, exhausted action budget, the 120-second trial timeout, and
reaching the $0.10 estimated cost cap are capability failures: a slow or looping
agent stays in the denominator and keeps its spend. Inspect every failed
trajectory before drawing conclusions; coding defects are invalid.

## Metrics and fairness

Record each HTTP attempt, raw request/response, usage, latency, complete DOM
trajectory, executed actions, terminal state, and independent verifier output.
Measure task duration from first prediction to loop termination, excluding setup,
cleanup, and verifier; report verifier duration separately if used. Successful
task latency is conditioned on success and always shown alongside success rate.
Failed/invalid trials retain spend; never present fast failures as speed wins.
Total spend / verified successes includes failed attempts. Missing usage or
ambiguous failed-request billing makes cost incomplete, never zero by default;
the report then shows only a labelled lower bound. Seed is read back from the
server evidence per trial, not from the launch command.
Published token-rate estimates are labelled estimates; provider billing overrides
them when available. Cache tokens and text-helper calls are counted explicitly.

Paired frozen-state selector tests would be a separate experiment; trajectories
may diverge in this closed-loop task. Identical writer settings do not imply
identical writer calls or cost. Do not claim calibration, general browser ability,
or statistical significance from this one task family.

## Leakage and audit

Only environment/*.py and index.html enter the task image. Task.md, tests,
solution, and project skill are excluded. Adapter uploads only harness .py/.js
files. Oracle code is uploaded only for the oracle arm, never model trials.
Model output cannot become a selector, script, or filesystem operation.
Test known-good, recovery, wrong target, unsubmitted form, booking, reverted
account change, and absent/corrupt evidence before scored runs.

## Open decisions

Build and offline/oracle verification authorized. Proposed paid smoke plan:
one seed-0 trial per model arm, no judge, 120 seconds each, spending cap $0.10
per trial (enforced against known usage estimates; provider billing may differ).
Smoke run executed 2026-09-19 (`evals/jobs/20260919T003333378265Z`, seed 0,
one trial per arm, both valid): control passed in 7 actions / 6.0 s / $0.001
estimate; treatment hit the 120 s cap after 48 actions, retyping the already
filled Destination field while the matching suggestion was offered as a CLICK
target (verified in the recorded request state). Classified as a capability
failure. One trial per arm is a smoke check, not a result; the six-seed paired
experiment should follow. No winner is claimed.

Further seed-0 smokes (control passed every pairing, 7 actions, ~5–6 s):
Jev-protocol prompt: gpt-5.4-nano reward 0 (false DONE, category oscillation);
gpt-5.4-mini reward 1 in 25 actions / 31 s / $0.056. LLM-native prompt with
gpt-5.4-mini writer in both arms: gpt-5.4-nano reward 0 with and without
reasoning, blocked after 6–8 actions clicking the Destination box while the
matching suggestion was listed; its reasoning named "Search hotels", which was
disabled and therefore absent from the element list. Fixed in the shared
snapshot (both arms): disabled controls are now observed as non-actionable
elements. Rerun with that observation: control still passed (7 actions);
gpt-5.4-nano still reward 0 with and without reasoning. With reasoning it
wrote "the Search button is currently disabled", WAITed twice, then clicked
`[1] Destination` as "submit the search" while `[2] Lisbon, Portugal (option)`
was offered. Classified as a capability failure on the autocomplete commit.
`--hints` variant (treatment prompt tags the expanded combobox PENDING and
each option SUGGESTION): still reward 0 with and without reasoning, same
pattern. In every failing decision the reasoning names "Search hotels" (index 5,
disabled, excluded from the CLICK enum) and the emitted target is `1`.
Hypothesis, untested: strict-schema constrained decoding substitutes an allowed
index when the intended one is not in the enum, so the trace shows a confident
wrong click instead of an invalid choice.

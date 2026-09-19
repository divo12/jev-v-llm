# First Jev Ultrafast Eval Task: Research Recommendation

*19 September 2026 · Sources reviewed: 5 · Confidence: high for task design, not yet a model-performance claim*

## Recommendation

Make the first task a **local hotel search with autocomplete, filters, delayed results, and a required property opening**:

> Find a hotel in Lisbon matching the Design category with free cancellation, then open Casa Flora. Do not book or submit personal information.

This is the right first task because it uses the repository's actual architecture: a chooser selects the browser operation and target from the current indexed DOM state; the text model is called only to fill a field. It therefore isolates the question we want to answer: whether Jev is a better action chooser than a small LLM when both agents share the same text generator. [agent loop](jev_ultrafast/agent.py) · [chooser and text helper](jev_ultrafast/model.py)

The repository already describes this exact local hotel workflow as a smoke check: search Lisbon, apply Design and Free cancellation, then open Casa Flora. Turning it into the first controlled benchmark is smaller and more defensible than introducing a new domain. [repository performance report](docs/performance.md)

## Why this beats the alternatives

| Candidate | Decision | Reason |
| --- | --- | --- |
| Local hotel search | **Use first** | Has typed input, dynamic choice, filtering, a delayed result state, and final-state verification without an irreversible side effect. |
| Live Google Flights | Do not benchmark first | The repository's demo is useful evidence, but live page/network changes and the user profile prevent reliable reset. |
| MiniWoB-style one-control task | Use later as a smoke suite | Too simple to separate a good selector from one that merely follows the prompt. |
| Full WebArena / WorkArena | Use later, if needed | Valuable external validation, but costly/heavy and a poor first debugging loop for this specialized agent. |
| Support-ticket drafting | Do not start here | Correct reply text needs a semantic judge, conflating chooser quality with generation quality. |

WebArena's design argues for a self-hosted environment with resettable state and functional completion checks; its verified successor adds deterministic, type-aware scoring and offline trace evaluation. Those are the important ideas to borrow, not its large multi-site infrastructure. [WebArena](https://github.com/web-arena-x/webarena) · [WebArena-Verified](https://github.com/ServiceNow/webarena-verified)

WorkArena reinforces that forms, lists, and filters are meaningful browser-agent work, while its large task catalogue shows why a single, controlled primitive is better for initial diagnosis. [WorkArena](https://github.com/ServiceNow/WorkArena)

## Task shape

The local page should show a real-looking hotel search UI with no external network calls:

1. A destination combobox. Typing `Lisbon` reveals several visible suggestions after a fixed delay; only the Lisbon suggestion is valid.
2. A category select, including `Design` and plausible distractors.
3. A Free cancellation checkbox, initially unchecked.
4. A Search button that is enabled only after a valid destination selection.
5. A short, deterministic loading state after Search.
6. Results containing Casa Flora only when all requested filters are applied, alongside similarly named distractors.

This is non-trivial but fair. It checks the repository's documented requirements that typed combobox input must be followed by selecting a matching suggestion, submitted fields must be applied before opening a result, existing filter state should not be toggled unnecessarily, and `DONE` requires visible evidence of the entire goal. [decision rules](jev_ultrafast/questions.py)

## Fair comparison

Run two agents from an identical fresh state:

```text
Arm A: Jev chooses operation/target; OpenAI text helper fills fields.
Arm B: small OpenAI selector chooses operation/target; the same OpenAI text helper fills fields.
```

Keep the following fixed: UI build, viewport, initial state, action space, operation descriptions, target labels, agent loop, maximum steps, text-helper model, text-helper prompt, timeout, and verifier. The selector is the only changed component.

The small-model selector must return the same information consumed by the loop: one operation, a compatible target, a normalized probability distribution, and confidence. It may not output CSS selectors, JavaScript, or unbounded browser commands; the production agent deliberately maps choices only to observed DOM nodes. [action-space and response validation](jev_ultrafast/model.py) · [browser execution guards](jev_ultrafast/browser.py)

## Independent verifier

Pass iff the application state shows one valid submitted search with:

- destination ID = Lisbon;
- category = Design;
- free cancellation = enabled;
- opened property ID = Casa Flora; and
- no booking, no profile change, no extra property opened, and no duplicate submit.

The verifier should read the local app's state and append-only action ledger after the run. It must not use the agent's `DONE` choice as evidence. This follows the same principle as the repository's Google Flights example, whose verifier independently checks the final page rather than trusting the agent, while replacing the live site with a resettable local one. [independent flight verifier](examples/flights.py)

Record separately—do not turn them into the success condition:

- task success;
- incorrect/blocked/stale action rate;
- action count and retries;
- selector p50/p95 latency;
- end-to-end p50/p95 latency;
- selector and text-helper token usage/cost; and
- calibration of selector confidence against correct next-action labels.

## Pilot protocol

Start with 12 seeded variants, each differing in one meaningful way: distractor names, already-set filter, delayed autocomplete, delayed results, or a stale result list. Run five trials per arm after verifying reset, for 120 total trajectories. Inspect every failed run and a sample of passes before reporting a winner.

This is deliberately not a public model leaderboard. It answers one concrete engineering question: which selector makes this agent more successful, reliable, and economical under the same text-generation layer.

## What remains open

The repository has no formal eval package or project World Skill yet. Do not create either until the task design is approved. If approved, create a `Task.md` plus a minimal reusable project skill that records only the fixed action-space, text-helper, reset, and verifier contracts—not task answers or hidden fixture state.

## Method

Reviewed the repository's agent loop, selector/text split, browser safety guards, offline tests, and existing live/local smoke-check descriptions. Reviewed browser-agent benchmark designs from WebArena, WebArena-Verified, WorkArena, and BrowserGym. The cited research supports controlled local environments, resettable state, and deterministic state/trace-based scoring; the proposed hotel task is an inference tailored to Jev Ultrafast's existing capabilities.

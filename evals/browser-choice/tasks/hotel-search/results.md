# hotel-search: Jev vs small-LLM chooser

**Task given to both agents**

> Find hotels in Lisbon, Portugal. Apply the Design category and Free cancellation filter. Open Casa Flora in Riverside and stop on its details page after confirming those requirements. Do not book a room or change account settings.

Local hotel site, fresh Chromium per trial, DOM-only observations. Same loop, executor, rules, and field writer in both arms; only the action chooser differs. Success is scored from the server's mutation ledger, not the agent's claim.

**Run: seed 0, one trial per arm** (`evals/jobs/20260919T012023034045Z`)

Writer in both arms: gpt-5.4 (`reasoning_effort: low`). Treatment prompt includes a one-sentence reasoning field.

| Arm | Chooser | Reward | Actions | Task time | Chooser p50 latency | Spend (list price) |
|---|---|---|---|---|---|---|
| Control | Jev 1.13.0 | **1** | 7 | 5.9 s | 347 ms | $0.0020 |
| Treatment | gpt-5.4-mini + reasoning | **1** | 6 | 12.7 s | 1187 ms | $0.0089 |

Both valid, costs complete, no booking or account events.

**Caveats**

- n = 1 per arm, one seed. Not a comparative claim.
- Treatment decision 4 chose *Change newsletter preference* while reasoning "submit the search" (Search was disabled and excluded from the schema enum). The page changed before execution, the harness discarded the stale decision, and the re-decision was correct. That guard applies to both arms.
- Earlier same-day runs on this seed: gpt-4.1-nano and gpt-5.4-nano failed every variant (timeout, false DONE, or blocked on the autocomplete commit). Jev passed all 13 pairings.

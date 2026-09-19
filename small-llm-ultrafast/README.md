# Small LLM Ultrafast (treatment)

Task-independent browser chooser using a compact strict JSON schema. It reuses
Jev Ultrafast's browser loop, DOM action space, executor, and OpenAI field writer.
Only action selection changes. No site-specific logic or task answers live here.

```bash
cd small-llm-ultrafast
uv sync
```

```python
from small_llm_ultrafast import Agent

with Agent(url, goal) as agent:
    for state in agent.run():
        print(state["status"])
```

Supply `TEXT_MODEL_API_KEY` for the shared writer; `OPENAI_API_KEY` may override
it for the selector. `SELECTOR_MODEL` defaults to `gpt-4.1-nano-2025-04-14`.
`SELECTOR_BASE_URL` defaults to the OpenAI API. Configure the writer through
`TEXT_MODEL` and `TEXT_MODEL_BASE_URL` as for the control.

The treatment reports confidence as null. Generating a probability for every
DOM element would add output work that action selection does not need.
See ../evals/README.md for controlled comparisons.

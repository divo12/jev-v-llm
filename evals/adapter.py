"""Harbor 0.22 adapter: transfer only harness code, never task truth to a model."""

import os
import shlex
import tempfile
from pathlib import Path

from harbor.agents.base import BaseAgent

ROOT = Path(__file__).resolve().parents[1]


class ChoiceAgent(BaseAgent):
    def __init__(self, *args, arm="control", seed=0, **kwargs):
        super().__init__(*args, **kwargs)
        if arm not in {"control", "treatment", "oracle"}:
            raise ValueError("Unknown arm")
        self.arm, self.seed = arm, int(seed)

    @staticmethod
    def name():
        return "browser-choice"

    def version(self):
        return "0.1.0"

    async def setup(self, environment):
        await environment.exec("mkdir -p /opt/harness/jev_ultrafast /opt/harness/small_llm_ultrafast")
        # File allowlist prevents .env, verifier, and task specs from entering the harness.
        for folder in (
            ROOT / "jev-ultrafast/jev_ultrafast",
            ROOT / "small-llm-ultrafast/small_llm_ultrafast",
        ):
            for source in sorted(folder.iterdir()):
                if source.suffix in {".py", ".js"}:
                    await environment.upload_file(source, f"/opt/harness/{folder.name}/{source.name}")
        await environment.upload_file(ROOT / "evals/runtime.py", "/opt/harness/runtime.py")
        await environment.upload_file(ROOT / "evals/metrics.py", "/opt/harness/metrics.py")
        result = await environment.exec("python /app/start.py", env={"TASK_SEED": str(self.seed)}, timeout_sec=45)
        if result.return_code:
            raise RuntimeError("Environment startup failed")
        await environment.exec(
            "python --version > /logs/agent/versions.txt; "
            "chromium --version >> /logs/agent/versions.txt; "
            "pip freeze >> /logs/agent/versions.txt"
        )

    async def run(self, instruction, environment, context):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "instruction.txt"
            path.write_text(instruction)
            await environment.upload_file(path, "/opt/harness/instruction.txt")
        env = {
            "PYTHONPATH": "/opt/harness",
            "BU_CDP_URL": "http://127.0.0.1:9222",
            "TEXT_MODEL_BASE_URL": "https://api.openai.com/v1",
            "TEXT_MODEL": os.environ.get("TEXT_MODEL", "gpt-4.1-mini-2025-04-14"),
            "SELECTOR_MODEL": self.model_name or os.environ.get("SELECTOR_MODEL", "gpt-4.1-nano-2025-04-14"),
            "SELECTOR_REASONING": os.environ.get("SELECTOR_REASONING", "0"),
            "SELECTOR_HINTS": os.environ.get("SELECTOR_HINTS", "0"),
            "TEXT_MODEL_REASONING": os.environ.get("TEXT_MODEL_REASONING", "none"),
            "TYPESAFE_MODEL": os.environ.get("TYPESAFE_MODEL", "jev-1.13.0"),
        }
        if self.arm == "oracle":
            await environment.upload_file(
                ROOT / "evals/browser-choice/tasks/hotel-search/solution/oracle.py",
                "/opt/harness/oracle.py",
            )
            command = "python /opt/harness/oracle.py"
        else:
            for name in ("TYPESAFE_API_KEY", "TEXT_MODEL_API_KEY"):
                value = self._get_env(name)
                if value:
                    env[name] = value
            command = "python /opt/harness/runtime.py " + shlex.quote(self.arm)
        result = await environment.exec(command, env=env, timeout_sec=150)
        if result.return_code:
            raise RuntimeError("Harness infrastructure failure; inspect agent artifacts")
        context.metadata = {
            "arm": self.arm,
            "seed": self.seed,
            "judge": "deterministic",
        }

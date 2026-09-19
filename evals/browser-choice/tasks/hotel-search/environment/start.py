import subprocess
import time
import urllib.request
from pathlib import Path

Path("/logs/agent").mkdir(parents=True, exist_ok=True)
for name, args in (
    ("app", ["python", "/app/app.py"]),
    (
        "chrome",
        [
            "chromium",
            "--headless",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--remote-debugging-port=9222",
            "--user-data-dir=/tmp/eval-chrome",
            "about:blank",
        ],
    ),
):
    with open(f"/logs/agent/{name}.log", "w") as log:
        subprocess.Popen(args, stdout=log, stderr=log, start_new_session=True)
for url in ("http://127.0.0.1:8080/catalog", "http://127.0.0.1:9222/json/version"):
    for attempt in range(100):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                assert response.status == 200
            break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Environment did not become ready")

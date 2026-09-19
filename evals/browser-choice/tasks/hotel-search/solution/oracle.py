"""Reference path through the real Browser executor. Never loaded for model arms."""

import json
import time
from pathlib import Path

from jev_ultrafast.browser import Browser


def main():
    browser = Browser("http://127.0.0.1:8080/")

    def act(kind, label, text=None):
        for _ in range(100):
            page = browser.observe(screenshot=False)
            choices = [a for a in page["actions"] if a["kind"] == kind and label(a)]
            if choices:
                browser.act(choices[0], page, text)
                return
            time.sleep(0.05)
        raise RuntimeError("Oracle could not observe required control")

    try:
        act("fill", lambda a: "Destination" in a["label"], "Lisbon")
        act("click", lambda a: a["label"] == "Lisbon, Portugal")
        act("select", lambda a: a["value"] == "Design")
        page = browser.observe(screenshot=False)
        checkbox = next(a for a in page["actions"] if a["label"] == "Free cancellation")
        if checkbox.get("checked") not in (True, "true"):
            browser.act(checkbox, page)
        act("click", lambda a: a["label"] == "Search hotels")
        act("click", lambda a: a["label"] == "Open Casa Flora — Riverside")
        time.sleep(0.1)
        page = browser.observe(screenshot=False)
        assert "Hotel details" in page["text"]
        Path("/logs/agent/oracle.json").write_text(json.dumps(page))
    finally:
        browser.close()


if __name__ == "__main__":
    main()

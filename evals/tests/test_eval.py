import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "evals/browser-choice/tasks/hotel-search"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load("hotel_app", TASK / "environment/app.py")
verifier = load("hotel_verifier", TASK / "tests/verify.py")


def success():
    world = app.World()
    world.apply("search", {"city": "lisbon-pt", "category": "Design", "free": True})
    world.apply("open", {"id": "h42"})
    return world


def test_valid_and_recovery_paths():
    world = success()
    assert verifier.verify(world.state)["reward"] == 1
    world.apply("open", {"id": "h17"})
    world.apply("search", {"city": "lisbon-pt", "category": "Design", "free": True})
    world.apply("open", {"id": "h42"})
    assert verifier.verify(world.state)["reward"] == 1


@pytest.mark.parametrize(
    "change", ["wrong_target", "booking", "account_reverted", "search_unapplied", "research_after_open"]
)
def test_realistic_failures(change):
    world = success()
    if change == "wrong_target":
        world.apply("open", {"id": "h17"})
    elif change == "research_after_open":
        world.apply("search", {"city": "lisbon-pt", "category": "Design", "free": True})
    elif change == "booking":
        world.apply("book", {"id": "h42"})
    elif change == "account_reverted":
        world.apply("account", {})
        world.apply("account", {})
    else:
        world = app.World()
    assert verifier.verify(world.state)["reward"] == 0


def test_corrupt_evidence_and_trial_isolation():
    world = success()
    corrupt = deepcopy(world.state)
    corrupt["events"] = []
    with pytest.raises(ValueError):
        verifier.verify(corrupt)
    with pytest.raises(ValueError):
        verifier.verify({})
    assert app.World().state["events"] == []


def test_server_rejects_shortcuts():
    world = app.World()
    with pytest.raises(ValueError):
        world.apply("open", {"id": "h42"})
    with pytest.raises(ValueError):
        world.apply("search", {"city": "Lisbon", "category": "Design", "free": True})


def test_treatment_rejects_target_for_wrong_operation(monkeypatch):
    from small_llm_ultrafast import model

    monkeypatch.setenv("TEXT_MODEL_API_KEY", "test")
    monkeypatch.setattr(
        model,
        "post_json",
        lambda *_args: {"choices": [{"message": {"content": '{"action":{"operation":"DONE","target":"1"}}'}}]},
    )
    with pytest.raises(ValueError, match="Invalid selector"):
        model.choose(
            {"url": "http://example.test", "title": "Test", "text": "", "actions": []},
            "Go",
            [],
        )


def test_disabled_controls_are_visible_but_never_targets():
    from jev_ultrafast.model import action_space, choice_request
    from small_llm_ultrafast.model import describe

    actions = [
        {"id": "e1", "kind": "disabled", "node": 7, "label": "Search hotels", "role": "button", "value": ""},
        {"id": "e2", "kind": "click", "node": 8, "label": "Go", "role": "button", "value": ""},
    ]
    elements, targets, controls = action_space(actions)
    assert elements[0] == {"index": "1", "label": "Search hotels", "role": "button", "value": "", "operations": [], "disabled": True}
    assert list(targets["CLICK"]) == ["2"] and not controls
    assert "DISABLED" in describe(elements[0])
    request = choice_request({"url": "u", "title": "t", "text": "", "actions": actions}, "Go", [])[0]
    assert "1" not in request["questions"]["click_target"]["criteria"]


def test_treatment_shares_context_and_validates_choice(monkeypatch):
    import json

    from jev_ultrafast.model import choice_request
    from small_llm_ultrafast import model

    state = {
        "url": "http://example.test",
        "title": "Test",
        "text": "",
        "actions": [{"id": "e7", "kind": "click", "node": 7, "label": "Continue"}],
    }
    request = choice_request(state, "Go", [])[0]

    def post(url, key, body):
        sent = body["messages"][1]["content"]
        # Same facts as the control request, formatted once: goal, rules, page text, element, history.
        assert "GOAL: Go" in sent and sent.count(model.NEXT_ACTION) == 1
        assert "[1] Continue (CLICK)" in sent or "[1] City" in sent
        assert "http://example.test" in sent
        assert body["response_format"]["json_schema"]["strict"] is True
        target = "2" if "[1] City" in sent else "1"
        return {"choices": [{"message": {"content": '{"action":{"operation":"CLICK","target":"%s"}}' % target}}]}

    monkeypatch.setenv("TEXT_MODEL_API_KEY", "test")
    monkeypatch.setattr(model, "post_json", post)
    result = model.choose(state, "Go", [])
    assert result["choice"] == "e7"
    assert result["confidence"] is None
    assert result["request"].keys() >= {"temperature", "max_tokens"}
    monkeypatch.setenv("SELECTOR_MODEL", "gpt-5.4-nano-2026-03-17")
    monkeypatch.setenv("SELECTOR_REASONING", "1")
    repeated = [{"action": "Continue", "kind": "click", "text": None, "page_changed": True}] * 3
    request = model.choose(state, "Go", repeated)["request"]
    assert request["reasoning_effort"] == "none" and request["max_completion_tokens"] == 256
    assert not request.keys() & {"temperature", "max_tokens"}
    schema = request["response_format"]["json_schema"]["schema"]
    assert list(schema["properties"]) == ["reasoning", "action"]
    assert "repeated 3 times" in request["messages"][1]["content"]
    assert "SUGGESTION" not in request["messages"][1]["content"]
    monkeypatch.setenv("SELECTOR_HINTS", "1")
    open_box = {
        **state,
        "actions": [
            {"id": "e1", "kind": "fill", "node": 1, "label": "City", "role": "combobox", "expanded": "true", "value": "x"},
            {"id": "e2", "kind": "click", "node": 2, "label": "X Town", "role": "option"},
        ],
    }
    sent = model.choose(open_box, "Go", [])["request"]["messages"][1]["content"]
    assert "PENDING" in sent and "SUGGESTION" in sent

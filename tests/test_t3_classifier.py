from __future__ import annotations

import json

import scripts.t3_classifier as t3
from scripts.blast_radius import classify_path
from scripts.t3_classifier import T3Decision, classify_t3_requirement, record_skip_telemetry


def _mock_file_change(monkeypatch, rel_path: str, before: str, after: str) -> None:
    def fake_head(workspace: str, path: str) -> str | None:
        return before if path == rel_path else None

    def fake_worktree(workspace: str, path: str) -> str | None:
        return after if path == rel_path else None

    diff = "\n".join(
        ["diff --git a/{0} b/{0}".format(rel_path)]
        + [f"-{line}" for line in before.splitlines()]
        + [f"+{line}" for line in after.splitlines()]
    )
    monkeypatch.setattr(t3, "_read_head_file", fake_head)
    monkeypatch.setattr(t3, "_read_worktree_file", fake_worktree)
    monkeypatch.setattr(t3, "_git_diff", lambda workspace, path: diff if path == rel_path else "")


def test_docstring_change_skips_t3(tmp_path, monkeypatch):
    _mock_file_change(
        monkeypatch,
        "core/foo.py",
        'def add(x: int, y: int) -> int:\n    """old doc"""\n    return x + y\n',
        'def add(x: int, y: int) -> int:\n    """new doc"""\n    return x + y\n',
    )

    decision = classify_t3_requirement(str(tmp_path), ["core/foo.py"])

    assert not decision.t3_required
    assert decision.reason == "cosmetic-only-python-ast"


def test_annotation_change_requires_t3(tmp_path, monkeypatch):
    _mock_file_change(
        monkeypatch,
        "core/foo.py",
        "def add(x: int) -> int:\n    return x\n",
        "def add(x: str) -> str:\n    return x\n",
    )

    decision = classify_t3_requirement(str(tmp_path), ["core/foo.py"])

    assert decision.t3_required
    assert decision.reason.startswith("semantic-python-change:")


def test_deleted_risk_token_requires_t3(tmp_path, monkeypatch):
    _mock_file_change(
        monkeypatch,
        "core/foo.py",
        "def run():\n    subprocess.run(['echo', 'x'])\n",
        "def run():\n    return None\n",
    )

    decision = classify_t3_requirement(str(tmp_path), ["core/foo.py"])

    assert decision.t3_required
    assert decision.reason == "risk-token-overlay"


def test_deleted_extended_risk_tokens_require_t3(tmp_path, monkeypatch):
    _mock_file_change(
        monkeypatch,
        "core/foo.py",
        "def run():\n    os.system('git reset --hard HEAD')\n    api_key = 'x'\n",
        "def run():\n    return None\n",
    )

    decision = classify_t3_requirement(str(tmp_path), ["core/foo.py"])

    assert decision.t3_required
    assert decision.reason == "risk-token-overlay"


def test_function_body_change_requires_t3(tmp_path, monkeypatch):
    _mock_file_change(
        monkeypatch,
        "core/foo.py",
        "def add(x, y):\n    return x + y\n",
        "def add(x, y):\n    return x - y\n",
    )

    decision = classify_t3_requirement(str(tmp_path), ["core/foo.py"])

    assert decision.t3_required
    assert decision.reason.startswith("semantic-python-change:")


def test_hard_guard_path_requires_t3_even_for_comment_only(tmp_path, monkeypatch):
    _mock_file_change(
        monkeypatch,
        "scripts/review_gate.py",
        "# old\nVALUE = 1\n",
        "# new\nVALUE = 1\n",
    )

    decision = classify_t3_requirement(str(tmp_path), ["scripts/review_gate.py"])

    assert decision.t3_required
    assert decision.reason == "hard-guard-path:scripts/review_gate.py"


def test_t3_policy_files_are_hard_guarded():
    assert classify_path("scripts/t3_classifier.py") == 3
    assert classify_path("scripts/enqueue_agent_review.py") == 3
    assert classify_path("scripts/check_pending_review.py") == 3


def test_skip_telemetry_jsonl_written(tmp_path):
    decision = T3Decision(
        "skip_t3",
        "cosmetic-only-python-ast",
        "test-version",
        ["core/foo.py"],
        {"added": 1, "deleted": 1},
    )

    record_skip_telemetry(str(tmp_path), decision)

    log = tmp_path / ".af_review_queue" / "t3_skip_telemetry.jsonl"
    payload = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert payload["skip_reason"] == "cosmetic-only-python-ast"
    assert payload["classifier_version"] == "test-version"
    assert payload["files"] == ["core/foo.py"]

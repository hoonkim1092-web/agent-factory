"""P4.5b: agent model escalation helper unit tests."""
from __future__ import annotations

import json
import time

import pytest

from scripts.agent_model_selector import (
    _DEFAULTS,
    clear_pending_escalation,
    get_pending_escalation,
    log_routing,
    select_model,
    store_pending_escalation,
)


class TestSelectModel:
    def test_no_triggers_returns_default(self):
        assert select_model("af-test-runner", []) == "haiku"
        assert select_model("af-critic", []) == "sonnet"
        assert select_model("af-doc-qa", []) == "sonnet"
        assert select_model("af-cross-review", []) == "sonnet"

    def test_test_failure_escalates_runner_to_sonnet(self):
        assert select_model("af-test-runner", ["test_failure"]) == "sonnet"

    def test_flaky_escalates_runner_to_sonnet(self):
        assert select_model("af-test-runner", ["flaky_or_timeout"]) == "sonnet"

    def test_import_path_issue_escalates_runner(self):
        assert select_model("af-test-runner", ["import_path_issue"]) == "sonnet"

    def test_security_escalates_critic_to_opus(self):
        assert select_model("af-critic", ["security_or_destructive_action"]) == "opus"

    def test_core_policy_escalates_critic_to_opus(self):
        assert select_model("af-critic", ["core_policy_change"]) == "opus"

    def test_doc_lint_only_downgrades_doc_qa_to_haiku(self):
        assert select_model("af-doc-qa", ["doc_lint_only"]) == "haiku"

    def test_unrecognized_trigger_returns_default(self):
        assert select_model("af-test-runner", ["unknown_xyz"]) == "haiku"
        assert select_model("af-critic", ["unknown_xyz"]) == "sonnet"

    def test_unknown_agent_returns_sonnet(self):
        assert select_model("af-unknown", []) == "sonnet"
        assert select_model("af-unknown", ["test_failure"]) == "sonnet"

    def test_cross_review_has_no_escalation(self):
        # af-cross-review not in matrix → always default regardless of triggers
        assert select_model("af-cross-review", ["test_failure", "core_policy_change"]) == "sonnet"

    def test_multiple_triggers_one_match_escalates(self):
        assert select_model("af-test-runner", ["test_failure", "unknown_xyz"]) == "sonnet"

    def test_approval_gate_trigger_escalates_critic(self):
        assert select_model("af-critic", ["approval_gate_change"]) == "opus"

    def test_packaging_trigger_escalates_runner(self):
        assert select_model("af-test-runner", ["packaging_or_frozen_build"]) == "sonnet"


class TestPendingEscalation:
    def test_store_and_get(self, tmp_path):
        store_pending_escalation(str(tmp_path), "af-test-runner", "sonnet", ["test_failure"])
        state = get_pending_escalation(str(tmp_path))
        assert state is not None
        assert state["agent"] == "af-test-runner"
        assert state["model"] == "sonnet"
        assert "test_failure" in state["triggers"]

    def test_get_returns_none_when_absent(self, tmp_path):
        assert get_pending_escalation(str(tmp_path)) is None

    def test_clear_removes_state(self, tmp_path):
        store_pending_escalation(str(tmp_path), "af-critic", "opus", ["core_policy_change"])
        clear_pending_escalation(str(tmp_path))
        assert get_pending_escalation(str(tmp_path)) is None

    def test_clear_is_idempotent(self, tmp_path):
        clear_pending_escalation(str(tmp_path))  # no-op, must not raise
        clear_pending_escalation(str(tmp_path))

    def test_stale_state_returns_none(self, tmp_path):
        store_pending_escalation(str(tmp_path), "af-test-runner", "sonnet", ["test_failure"])
        state_path = tmp_path / ".af_review_queue" / "model_escalation_pending.json"
        data = json.loads(state_path.read_text())
        data["ts"] = time.time() - 700  # 700s > 600s expiry
        state_path.write_text(json.dumps(data))
        assert get_pending_escalation(str(tmp_path)) is None

    def test_corrupt_state_returns_none(self, tmp_path):
        state_path = tmp_path / ".af_review_queue" / "model_escalation_pending.json"
        state_path.parent.mkdir(exist_ok=True)
        state_path.write_text("not-json-{{{")
        assert get_pending_escalation(str(tmp_path)) is None


class TestLogRouting:
    def test_creates_log_file(self, tmp_path):
        log_routing(str(tmp_path), "af-test-runner", "sonnet", ["test_failure"])
        log_path = tmp_path / ".af_review_queue" / "model_routing.log"
        assert log_path.exists()
        content = log_path.read_text()
        assert "af-test-runner" in content
        assert "sonnet" in content
        assert "test_failure" in content
        assert "escalated" in content

    def test_default_routing_marked_default(self, tmp_path):
        log_routing(str(tmp_path), "af-test-runner", "haiku", [])
        log_path = tmp_path / ".af_review_queue" / "model_routing.log"
        content = log_path.read_text()
        assert "default" in content

    def test_appends_multiple_entries(self, tmp_path):
        log_routing(str(tmp_path), "af-test-runner", "haiku", [])
        log_routing(str(tmp_path), "af-critic", "opus", ["core_policy_change"])
        log_path = tmp_path / ".af_review_queue" / "model_routing.log"
        lines = log_path.read_text().splitlines()
        assert len(lines) == 2
        assert "af-critic" in lines[1]

    def test_no_crash_on_bad_workspace(self):
        log_routing("/nonexistent/path/xyz_abc", "af-test-runner", "haiku", [])

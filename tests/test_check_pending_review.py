"""tests/test_check_pending_review.py — _inject_model_override 단위 테스트."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from check_pending_review import _inject_model_override
from scripts.agent_model_selector import _TIER_TO_MODEL_ID


class TestInjectModelOverride:
    def test_no_pending_returns_unchanged(self):
        agent_list = "af-test-runner"
        assert _inject_model_override(agent_list, None) == agent_list

    def test_sonnet_escalation_annotates_test_runner(self):
        result = _inject_model_override(
            "af-test-runner",
            {"agent": "af-test-runner", "model": "sonnet"},
        )
        assert result == f"af-test-runner[model={_TIER_TO_MODEL_ID['sonnet']}]"

    def test_opus_escalation_annotates_critic(self):
        result = _inject_model_override(
            "af-critic → af-cross-review → af-test-runner",
            {"agent": "af-critic", "model": "opus"},
        )
        assert result == f"af-critic[model={_TIER_TO_MODEL_ID['opus']}] → af-cross-review → af-test-runner"

    def test_agent_not_in_list_returns_unchanged(self):
        agent_list = "af-test-runner"
        result = _inject_model_override(
            agent_list,
            {"agent": "af-critic", "model": "opus"},
        )
        assert result == agent_list

    def test_claude_default_model_not_annotated(self):
        agent_list = "af-test-runner"
        result = _inject_model_override(
            agent_list,
            {"agent": "af-test-runner", "model": ""},
        )
        assert result == agent_list

    def test_already_annotated_not_double_annotated(self):
        agent_list = "af-test-runner[model=claude-sonnet-4-6]"
        result = _inject_model_override(
            agent_list,
            {"agent": "af-test-runner", "model": "sonnet"},
        )
        assert result == agent_list

    def test_full_model_id_passthrough(self):
        full_id = "claude-opus-4-8"
        result = _inject_model_override(
            "af-critic",
            {"agent": "af-critic", "model": full_id},
        )
        assert result == f"af-critic[model={full_id}]"

    def test_haiku_tier3_chain(self):
        result = _inject_model_override(
            "af-critic → af-cross-review → af-test-runner",
            {"agent": "af-test-runner", "model": "sonnet"},
        )
        assert f"af-test-runner[model={_TIER_TO_MODEL_ID['sonnet']}]" in result
        assert "af-critic →" in result

    def test_empty_agent_in_pending_returns_unchanged(self):
        agent_list = "af-test-runner"
        assert _inject_model_override(agent_list, {"agent": "", "model": "sonnet"}) == agent_list

    def test_missing_model_key_returns_unchanged(self):
        agent_list = "af-test-runner"
        assert _inject_model_override(agent_list, {"agent": "af-test-runner"}) == agent_list

    def test_other_agent_annotated_does_not_block_injection(self):
        agent_list = f"af-critic[model={_TIER_TO_MODEL_ID['opus']}] → af-cross-review → af-test-runner"
        result = _inject_model_override(
            agent_list,
            {"agent": "af-test-runner", "model": "sonnet"},
        )
        assert f"af-test-runner[model={_TIER_TO_MODEL_ID['sonnet']}]" in result

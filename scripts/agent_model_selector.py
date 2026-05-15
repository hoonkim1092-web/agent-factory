"""
scripts/agent_model_selector.py
================================
P4.5b runtime model escalation helper.

select_model(agent_name, triggers) → model short-name ("haiku"/"sonnet"/"opus").
Escalation 매트릭스 출처: ADR-20260515-114000-agent-model-routing-defaults-escalation.md
"""
from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

# Agent 기본 모델 (frontmatter 기준)
_DEFAULTS: dict[str, str] = {
    "af-test-runner":  "haiku",
    "af-critic":       "sonnet",
    "af-cross-review": "sonnet",
    "af-doc-qa":       "sonnet",
}

# Escalation 매트릭스: trigger set ∩ active_triggers → escalate_to
_ESCALATION_MATRIX: dict[str, dict] = {
    "af-test-runner": {
        "triggers": {
            "test_failure",
            "flaky_or_timeout",
            "import_path_issue",
            "subprocess_or_os_branching",
            "packaging_or_frozen_build",
        },
        "escalate_to": "sonnet",
    },
    "af-critic": {
        "triggers": {
            "core_policy_change",
            "approval_gate_change",
            "security_or_destructive_action",
            "cross_platform_subprocess",
        },
        "escalate_to": "opus",
    },
    "af-doc-qa": {
        "triggers": {"doc_lint_only"},
        "escalate_to": "haiku",  # downgrade: doc-lint 전용
    },
    # af-cross-review: no escalation (orchestrator 역할, Sonnet 충분)
}

_QUEUE_DIR = ".af_review_queue"
_STATE_FILE = "model_escalation_pending.json"
_LOG_FILE = "model_routing.log"
_EXPIRY_SEC = 600  # 10분 후 stale


def select_model(agent_name: str, triggers: list[str]) -> str:
    """Return model short-name for agent_name given active trigger conditions.

    Falls back to frontmatter default when no triggers match or agent is unknown.
    """
    default = _DEFAULTS.get(agent_name, "sonnet")
    matrix = _ESCALATION_MATRIX.get(agent_name)
    if not matrix or not triggers:
        return default
    active = set(triggers) & matrix["triggers"]
    if active:
        return matrix["escalate_to"]
    return default


def log_routing(workspace: str, agent_name: str, model: str, triggers: list[str]) -> None:
    """Append routing decision to model_routing.log (best-effort, never raises)."""
    log_path = Path(workspace) / _QUEUE_DIR / _LOG_FILE
    try:
        log_path.parent.mkdir(exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        is_escalated = model != _DEFAULTS.get(agent_name, "sonnet")
        line = (
            f"{ts}|{agent_name}|{model}"
            f"|{','.join(triggers) or 'none'}"
            f"|{'escalated' if is_escalated else 'default'}\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def store_pending_escalation(
    workspace: str, agent_name: str, model: str, triggers: list[str]
) -> None:
    """Persist escalation recommendation for next-turn surfacing via hook."""
    state_path = Path(workspace) / _QUEUE_DIR / _STATE_FILE
    try:
        state_path.parent.mkdir(exist_ok=True)
        state = {
            "agent": agent_name,
            "model": model,
            "triggers": list(triggers),
            "ts": time.time(),
        }
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_pending_escalation(workspace: str) -> dict | None:
    """Return pending escalation state, or None if absent or stale (> 10 min)."""
    state_path = Path(workspace) / _QUEUE_DIR / _STATE_FILE
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if time.time() - float(state.get("ts", 0)) > _EXPIRY_SEC:
        with contextlib.suppress(OSError):
            state_path.unlink()
        return None
    return state


def clear_pending_escalation(workspace: str) -> None:
    """Remove pending escalation state file."""
    state_path = Path(workspace) / _QUEUE_DIR / _STATE_FILE
    with contextlib.suppress(OSError):
        state_path.unlink()

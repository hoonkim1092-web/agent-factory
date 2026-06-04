"""
scripts/agent_model_selector.py
================================
P4.5b runtime model escalation helper.

select_model(agent_name, triggers) → model short-name ("haiku"/"sonnet"/"opus").
resolve_model_id(tier_or_id) → full Claude model ID (e.g. "claude-sonnet-4-6").
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

# claude CLI에 전달할 구체 모델 ID 매핑 (tier 단축명 → 현재 최신 모델 ID)
# _should_include_model이 "claude" alias는 --model에서 제외하므로 구체 ID만 통과함.
_TIER_TO_MODEL_ID: dict[str, str] = {
    "opus":   "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5-20251001",
}

_QUEUE_DIR = ".af_review_queue"
_STATE_FILE = "model_escalation_pending.json"
_LOG_FILE = "model_routing.log"
_EXPIRY_SEC = 600  # 10분 후 stale


def resolve_model_id(tier_or_id: str) -> str:
    """tier 단축명("haiku"/"sonnet"/"opus")을 claude CLI --model 전달용 전체 ID로 변환.

    이미 전체 ID이면 그대로 반환. 알 수 없는 값도 그대로 반환.
    빈 값이나 None은 "claude"(default 상속, _should_include_model이 --model 생략)를 반환.
    """
    t = str(tier_or_id or "").strip().lower()
    if not t:
        return "claude"
    return _TIER_TO_MODEL_ID.get(t, tier_or_id)


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

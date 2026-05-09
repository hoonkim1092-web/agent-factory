"""Escalation Evaluator — P1 stub.

P2에서 e2e_command_missing BLOCK 평가 활성, P4에서 나머지 rule 점진 확장.
"""
from __future__ import annotations

import os

from dataclasses import dataclass

from core.config_paths import BASE_DIR
from core.warning_registry import WarningRecord

_POLICY_PATH = os.path.join(BASE_DIR, "config", "escalation_policy.yaml")


@dataclass
class EscalationDecision:
    block: bool
    severity: str       # "warn" | "block_candidate" | "block"
    reason: str
    rule_id: str = ""
    activate_at: str = ""


@dataclass
class _PolicyRule:
    rule_id: str
    activate_at: str = "never"
    block_when: dict | None = None
    exempt_when: dict | None = None
    rationale: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "_PolicyRule":
        bw = d.get("block_when")
        if bw is not None and not isinstance(bw, dict):
            raise ValueError(
                f"block_when must be mapping or omitted, got {type(bw).__name__}"
            )
        return cls(
            rule_id=d["rule_id"],
            activate_at=d.get("activate_at", "never"),
            block_when=bw,
            exempt_when=d.get("exempt_when"),
            rationale=d.get("rationale", ""),
        )


def _load_policy() -> dict:
    """P1: yaml 존재 검증만. P2가 정책 매칭 사용."""
    if not os.path.isfile(_POLICY_PATH):
        return {"version": 0, "rules": []}
    try:
        import yaml  # type: ignore[import-untyped]
        with open(_POLICY_PATH, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {"version": 0, "rules": []}
    except Exception:
        return {"version": 0, "rules": []}


def evaluate(record: WarningRecord) -> EscalationDecision:
    """P1 stub — 모든 rule이 inactive. P2/P4에서 점진 활성."""
    return EscalationDecision(
        block=False,
        severity="warn",
        reason="inactive_phase",
        rule_id=record.rule_id,
        activate_at="P2_or_later",
    )

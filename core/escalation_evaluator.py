"""Escalation Evaluator — P2 구현.

P2: e2e_command_missing BLOCK 활성.
P4: 나머지 rule 점진 확장.
"""
from __future__ import annotations

import os

from dataclasses import dataclass, field

from core.config_paths import BASE_DIR
from core.warning_registry import WarningRecord

_POLICY_PATH = os.path.join(BASE_DIR, "config", "escalation_policy.yaml")

_PHASE_ORDER_ESCALATION: dict[str, int] = {
    "never": -1, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6,
}


@dataclass
class EscalationDecision:
    block: bool
    severity: str       # "warn" | "block_candidate" | "block"
    reason: str
    rule_id: str = ""
    activate_at: str = ""


@dataclass
class RunDecision:
    block: bool
    blocking_rules: list[str]
    rule_decisions: list[EscalationDecision]
    reason: str
    activate_phase: str
    summary_snapshot: dict = field(default_factory=dict)


@dataclass
class _PolicyRule:
    rule_id: str
    activate_at: str = "never"
    mode: str = "enforce"           # "enforce" | "observation" | "off"
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
        mode = d.get("mode", "enforce")
        if mode not in ("enforce", "observation", "off"):
            raise ValueError(f"mode must be enforce|observation|off, got {mode!r}")
        return cls(
            rule_id=d["rule_id"],
            activate_at=d.get("activate_at", "never"),
            mode=mode,
            block_when=bw,
            exempt_when=d.get("exempt_when"),
            rationale=d.get("rationale", ""),
        )


def load_policy() -> dict:
    """escalation_policy.yaml을 로드해 반환. 파일 부재 → 빈 policy, 파싱 오류 → raise."""
    if not os.path.isfile(_POLICY_PATH):
        return {"version": 0, "rules": []}
    try:
        import yaml  # type: ignore[import-untyped]
        with open(_POLICY_PATH, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {"version": 0, "rules": []}
    except Exception as exc:
        raise RuntimeError(f"escalation_policy.yaml parse error: {exc}") from exc


# P1 호환 — 내부 코드는 load_policy()를 사용하지만 _load_policy()도 유지
_load_policy = load_policy


def read_current_phase(policy: dict) -> str:
    """yaml top-level current_phase 반환. 부재/invalid → "P2" fallback (호환)."""
    cp = policy.get("current_phase")
    if cp in _PHASE_ORDER_ESCALATION and cp != "never":
        return cp
    return "P2"


def _find_rule(policy: dict, rule_id: str) -> _PolicyRule | None:
    for r in policy.get("rules") or []:
        if isinstance(r, dict) and r.get("rule_id") == rule_id:
            return _PolicyRule.from_dict(r)
    return None


def _is_phase_active(rule_phase: str, current: str = "P2") -> bool:
    rule_num = _PHASE_ORDER_ESCALATION.get(rule_phase, -1)
    cur_num = _PHASE_ORDER_ESCALATION.get(current, 0)
    return rule_num >= 1 and rule_num <= cur_num


def evaluate(
    record: WarningRecord,
    *,
    policy: dict | None = None,
    current_phase: str = "P2",
) -> EscalationDecision:
    """단일 record에 대해 policy 매칭 평가.

    policy: 주입된 policy dict. None이면 load_policy()로 로드.
    current_phase: 현재 시스템 escalation 단계 (기본 "P2").
    """
    if policy is None:
        policy = load_policy()
    rule = _find_rule(policy, record.rule_id)

    if rule is None or rule.activate_at == "never":
        return EscalationDecision(
            block=False, severity="warn", reason="rule_not_active",
            rule_id=record.rule_id,
            activate_at=rule.activate_at if rule else "",
        )

    if not _is_phase_active(rule.activate_at, current=current_phase):
        return EscalationDecision(
            block=False, severity="warn", reason="inactive_phase",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )

    if record.false_positive_override:
        return EscalationDecision(
            block=False, severity="warn", reason="false_positive_override",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )

    # P4a: mode 분기 (false_positive_override 직후, exempt/threshold 앞단)
    if rule.mode == "off":
        return EscalationDecision(
            block=False, severity="warn", reason="mode_off",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )
    if rule.mode == "observation":
        if rule.exempt_when:
            ex_phases = rule.exempt_when.get("affected_phase_in") or []
            if record.affected_phase in ex_phases:
                return EscalationDecision(
                    block=False, severity="warn",
                    reason=f"observation_exempt_phase:{record.affected_phase}",
                    rule_id=record.rule_id, activate_at=rule.activate_at,
                )
        bw = rule.block_when or {}
        cond_phase = bw.get("affected_phase_in")
        cond_count = bw.get("count_per_run_min", 1)
        cond_repeat = bw.get("repeat_count_min", 0)
        phase_match = (cond_phase is None) or (record.affected_phase in cond_phase)
        count_match = record.count >= cond_count
        repeat_match = record.repeat_count >= cond_repeat
        if phase_match and count_match and repeat_match:
            return EscalationDecision(
                block=False, severity="block_candidate",
                reason="observation_threshold_met",
                rule_id=record.rule_id, activate_at=rule.activate_at,
            )
        return EscalationDecision(
            block=False, severity="warn",
            reason="observation_below_threshold",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )

    # enforce 경로 (기존 동작)
    # exempt 우선 — 매칭되면 즉시 면제
    if rule.exempt_when:
        ex_phases = rule.exempt_when.get("affected_phase_in") or []
        if record.affected_phase in ex_phases:
            return EscalationDecision(
                block=False, severity="warn",
                reason=f"exempt_phase:{record.affected_phase}",
                rule_id=record.rule_id, activate_at=rule.activate_at,
            )

    # block_when 매칭
    bw = rule.block_when or {}
    cond_phase = bw.get("affected_phase_in")
    cond_count = bw.get("count_per_run_min", 1)
    cond_repeat = bw.get("repeat_count_min", 0)

    phase_match = (cond_phase is None) or (record.affected_phase in cond_phase)
    count_match = record.count >= cond_count
    repeat_match = record.repeat_count >= cond_repeat

    if phase_match and count_match and repeat_match:
        return EscalationDecision(
            block=True, severity="block", reason="threshold_met",
            rule_id=record.rule_id, activate_at=rule.activate_at,
        )

    return EscalationDecision(
        block=False, severity="warn", reason="below_threshold",
        rule_id=record.rule_id, activate_at=rule.activate_at,
    )


def compute_run_decision(
    summary: dict,
    policy: dict,
    *,
    current_phase: str = "P2",
) -> RunDecision:
    """슬러그의 summary 전체로 run-level 차단 결정을 계산."""
    by_rule = summary.get("by_rule") or {}
    rule_decisions: list[EscalationDecision] = []
    blocking: list[str] = []

    for rule_id, info in by_rule.items():
        rule = _find_rule(policy, rule_id)
        if rule is None:
            continue
        # by_phase 분포로 phase별 가상 record를 만들어 evaluate에 위임
        for phase, count in (info.get("by_phase") or {}).items():
            virtual = WarningRecord(
                rule_id=rule_id,
                severity=info.get("severity", "warn"),
                affected_phase=phase,
                count=count,
                repeat_count=info.get("repeat_count_max", 1),
                false_positive_override=bool(info.get("any_override", False)),
                project_slug=summary.get("project_slug", ""),
                ts=info.get("last_ts", ""),
                rationale="(aggregated)",
                affected_ids=[],
                source_path="(aggregated)",
                extra={},
                schema_version=1,
                record_id="(aggregated)",
                baseline_delta=0.0,
            )
            d = evaluate(virtual, policy=policy, current_phase=current_phase)
            rule_decisions.append(d)
            if d.block:
                blocking.append(rule_id)

    if blocking:
        reason = f"blocked_by:{','.join(sorted(set(blocking)))}"
        return RunDecision(
            block=True,
            blocking_rules=sorted(set(blocking)),
            rule_decisions=rule_decisions,
            reason=reason,
            activate_phase=current_phase,
            summary_snapshot=summary,
        )
    return RunDecision(
        block=False,
        blocking_rules=[],
        rule_decisions=rule_decisions,
        reason="no_active_blocks_in_run",
        activate_phase=current_phase,
        summary_snapshot=summary,
    )

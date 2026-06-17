"""Completion contract: goal-reached verification via an evidence ledger.

이 모듈은 "생성 = 완료" 패턴 A를 차단하기 위한 *데이터 기반*이다.
파이프라인의 acceptance criteria를 검증 가능한 골(GoalEntry)로 모델링하고,
각 골을 실행 증거(GoalEvidence)로 판정(GoalVerdict)한다.

S1 범위(본 파일): 구조체 + 직렬화만. 실제 하니스 실행(ExecutionHarness)과
AcceptanceGate는 S2에서 추가한다.

설계: docs/2026-06-17-af-completion-contract-goal-verification-design.md §4·§5.2·§8 S1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# VERIFIED      — 실행 증거로 골 충족 확인
# FAILED        — 실행했으나 골 미충족 (BLOCKED(goal_failed) terminal 유발)
# CANNOT_VERIFY — 환경 한계로 검증 불가 (실패 아님, is_done() done 허용)
# UNVERIFIED    — 아직 검증 안 됨 / harness_type 미해결 (file-exists 자동통과 금지)
GoalVerdict = Literal["VERIFIED", "FAILED", "CANNOT_VERIFY", "UNVERIFIED"]


@dataclass
class GoalEvidence:
    evidence_type: str          # "exit_code" | "stdout_contains" | "file_exists" | "manual" | "cannot_verify" | "unverified"
    evidence_value: str         # 실제 캡처된 값 또는 설명
    command_run: str = ""       # 실행한 명령 (있을 경우)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "evidence_value": self.evidence_value,
            "command_run": self.command_run,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalEvidence":
        return cls(
            evidence_type=data.get("evidence_type", ""),
            evidence_value=data.get("evidence_value", ""),
            command_run=data.get("command_run", ""),
        )


@dataclass
class GoalEntry:
    goal_id: str                # 예: "G-1"
    description: str            # 사람이 읽는 골 설명
    harness_type: str           # "cli" | "server" | "gui" | "library" | "none"
    evidence: GoalEvidence | None = None
    verdict: GoalVerdict = "UNVERIFIED"
    cannot_verify_reason: str = ""   # CANNOT_VERIFY일 때 이유

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "harness_type": self.harness_type,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "verdict": self.verdict,
            "cannot_verify_reason": self.cannot_verify_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalEntry":
        ev = data.get("evidence")
        return cls(
            goal_id=data.get("goal_id", ""),
            description=data.get("description", ""),
            harness_type=data.get("harness_type", "none"),
            evidence=GoalEvidence.from_dict(ev) if ev else None,
            verdict=data.get("verdict", "UNVERIFIED"),
            cannot_verify_reason=data.get("cannot_verify_reason", ""),
        )


@dataclass
class GoalContract:
    task_id: str
    goals: list[GoalEntry] = field(default_factory=list)

    def is_done(self) -> bool:
        """INV-A: 모든 골이 VERIFIED 또는 CANNOT_VERIFY여야 done.

        골이 하나도 없으면 done이 아니다(빈 계약으로 통과 금지).
        """
        for g in self.goals:
            if g.verdict in ("UNVERIFIED", "FAILED"):
                return False
        return bool(self.goals)

    def has_failures(self) -> bool:
        return any(g.verdict == "FAILED" for g in self.goals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goals": [g.to_dict() for g in self.goals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalContract":
        return cls(
            task_id=data.get("task_id", ""),
            goals=[GoalEntry.from_dict(g) for g in (data.get("goals") or [])],
        )


@dataclass
class HarnessResult:
    ok: bool
    evidence_type: str
    evidence_value: str
    command_run: str

"""
core/skill_quality_gate.py
===========================
스킬 품질 게이트 — 평가 통과한 스킬만 registry에 등재.
Quality Plane 컴포넌트.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.skill_registry import SkillRegistry


@dataclass
class GateResult:
    passed: bool
    skill_path: str
    recommended_stage: str
    pass_rate: float
    eval_report_path: str
    failure_reasons: list[str] = field(default_factory=list)
    quality_delta: float | None = None


class SkillQualityGate:
    """스킬 평가 → 등재 게이트."""

    PASS_RATE_THRESHOLD = 0.8

    def __init__(self, registry=None):
        from core.skill_registry import get_global_registry
        self.registry = registry or get_global_registry()
        from core.skill_eval_harness import SkillEvalHarness
        self.harness = SkillEvalHarness()

    def validate(
        self,
        skill_path: str,
        *,
        baseline_skill_path: str | None = None,
        auto_register: bool = True,
    ) -> GateResult:
        import os
        skill_py = os.path.join(skill_path, "skill.py")
        try:
            report = self.harness.evaluate(
                skill_py,
                baseline_skill_path=baseline_skill_path,
            )
        except Exception as e:
            return GateResult(
                passed=False,
                skill_path=skill_path,
                recommended_stage="draft",
                pass_rate=0.0,
                eval_report_path="",
                failure_reasons=[f"eval error: {e}"],
            )

        # contract_eval.pass_rate 기반으로 통과 여부 결정
        # contract_eval이 케이스가 0개면 static_gate.ok로 판단
        contract_eval = report.contract_eval
        if contract_eval.total_cases > 0:
            pass_rate = contract_eval.pass_rate
        else:
            # 케이스가 없으면 static_gate ok 여부로 판단 (pass_rate=1.0 간주)
            pass_rate = 1.0 if report.static_gate.get("ok", False) else 0.0

        passed = pass_rate >= self.PASS_RATE_THRESHOLD

        failure_reasons: list[str] = []
        if not passed:
            failure_reasons.append(
                f"contract pass_rate {pass_rate:.1%} "
                f"< threshold {self.PASS_RATE_THRESHOLD:.0%}"
            )
            for case in contract_eval.details:
                if not case.passed:
                    failure_reasons.append(f"  FAIL: {case.name} — {case.error}")

        if passed and auto_register:
            self._register_with_eval(skill_path, report)

        return GateResult(
            passed=passed,
            skill_path=skill_path,
            recommended_stage=report.recommended_stage,
            pass_rate=pass_rate,
            eval_report_path=getattr(report, "report_path", ""),
            failure_reasons=failure_reasons,
        )

    def _register_with_eval(self, skill_path: str, report) -> None:
        """평가 통과 스킬을 레지스트리에 등재한다."""
        try:
            import os
            from core.skill_metadata import SkillMetadata
            meta_path = os.path.join(skill_path, "meta.yaml")
            if not os.path.exists(meta_path):
                return
            from core.skill_metadata_adapter import auto_detect_and_convert
            skill_name = os.path.basename(skill_path)
            metadata = auto_detect_and_convert(skill_path, skill_name)
            if metadata is None:
                return
            # recommended_stage → lifecycle_stage에 반영
            metadata.lifecycle_stage = report.recommended_stage
            # eval_report_path → evals_path에 반영 (기존 필드 재활용)
            if getattr(report, "report_path", ""):
                metadata.evals_path = report.report_path
            self.registry.register(metadata)
        except Exception:
            pass

"""
core/skill_quality_gate.py
===========================
스킬 품질 게이트 — 평가 통과한 스킬만 registry에 등재.
Quality Plane 컴포넌트.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

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
    MIN_SHADOW_CASES = 3  # delta 게이트 적용 최소 케이스 수 (소표본 노이즈 방지)

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

        # knowledge skill: skill.py 없고 SKILL.md 있으면 문서 전용으로 간주 — gate 통과
        if not os.path.exists(skill_py) and (
            os.path.exists(os.path.join(skill_path, "SKILL.md")) or
            os.path.exists(os.path.join(skill_path, "skill.md"))
        ):
            if auto_register:
                self._register_knowledge_skill(skill_path)
            return GateResult(
                passed=True,
                skill_path=skill_path,
                recommended_stage="active",
                pass_rate=1.0,
                eval_report_path="",
            )

        # baseline 경로 정규화: 디렉터리 → skill.py 파일 경로
        # (디렉터리를 그대로 넘기면 importlib.spec_from_file_location이 None 반환
        #  → baseline_callable=None → shadow 비교 silent-skip)
        baseline_py = None
        if baseline_skill_path:
            _candidate = os.path.join(baseline_skill_path, "skill.py")
            baseline_py = _candidate if os.path.exists(_candidate) else None

        try:
            report = self.harness.evaluate(
                skill_py,
                baseline_skill_path=baseline_py,
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

        # shadow delta 게이트 (C2): baseline 있고 케이스 충분하면 delta > 0 강제
        shadow_ok, shadow_reason = self._shadow_not_regressed(report.shadow_eval)
        if not shadow_ok:
            passed = False
            failure_reasons.append(shadow_reason)

        if passed and auto_register:
            self._register_with_eval(skill_path, report)

        shadow_eval = report.shadow_eval
        return GateResult(
            passed=passed,
            skill_path=skill_path,
            recommended_stage=report.recommended_stage,
            pass_rate=pass_rate,
            eval_report_path=getattr(report, "report_path", ""),
            failure_reasons=failure_reasons,
            quality_delta=shadow_eval.delta if shadow_eval.total_cases > 0 else None,
        )

    def _shadow_not_regressed(self, shadow_eval) -> tuple[bool, str]:
        """shadow delta 게이트. (passed, reason) 반환.

        | 조건 | 판정 |
        |------|------|
        | total_cases == 0 | 통과 (baseline 없음 — 기존 동작) |
        | total_cases < MIN | 통과 (소표본 노이즈 무차단) |
        | delta > 0         | 통과 (개선 확인) |
        | delta <= 0        | REJECTED (퇴화 또는 무변화) |
        """
        if shadow_eval.total_cases == 0:
            return True, ""
        if shadow_eval.total_cases < self.MIN_SHADOW_CASES:
            return True, ""
        if shadow_eval.delta > 0:
            return True, ""
        return (
            False,
            f"shadow regression: delta={shadow_eval.delta} over {shadow_eval.total_cases} cases",
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

    def _register_knowledge_skill(self, skill_path: str) -> None:
        """knowledge skill(SKILL.md 전용)을 레지스트리에 등재한다. eval report 없음."""
        try:
            import os
            from core.skill_metadata_adapter import auto_detect_and_convert
            skill_name = os.path.basename(skill_path)
            metadata = auto_detect_and_convert(skill_path, skill_name)
            if metadata is None:
                logger.warning("[SkillQualityGate] knowledge skill metadata 변환 실패 — 등재 스킵: %s", skill_path)
                return
            metadata.lifecycle_stage = "active"
            self.registry.register(metadata)
        except Exception as e:
            logger.warning("[SkillQualityGate] knowledge skill 등재 실패: %s — %s", skill_path, e)

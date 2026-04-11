"""
core/plan_verifier.py
======================
Plan-Critique-Verify 사전 루프 — work-item 생성 완료 후, 실행 전 계획 검증.
기존 parallel_critique.py + requirement_llm.py 위에 얹은 경량 래퍼.

Quality Plane 컴포넌트.

흐름:
  work_items
    └─> artifact 변환 (dict)
        └─> ParallelCritiqueEngine.critique()
            └─> MergedCritique → PlanVerifyResult
                └─> score < PASS_THRESHOLD → refine() 시도
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# ──────────────────────────────────────────────────────────────
# 결과 데이터클래스
# ──────────────────────────────────────────────────────────────

@dataclass
class PlanVerifyResult:
    """계획 검증 결과."""
    passed: bool                               # PASS_THRESHOLD 이상이면 True
    score: float                               # 0.0 ~ 1.0 (MergedCritique.score)
    issues: list[str] = field(default_factory=list)       # confirmed_gaps + suspected_gaps
    suggestions: list[str] = field(default_factory=list)  # revision_instructions
    refined_items: list | None = None          # 재작성된 work-item (refine 성공 시)


# ──────────────────────────────────────────────────────────────
# PlanVerifier
# ──────────────────────────────────────────────────────────────

class PlanVerifier:
    """
    work-item 목록을 실행 전에 검증하는 경량 래퍼.

    내부적으로 ParallelCritiqueEngine을 사용해 artifact를 비평하고,
    PASS_THRESHOLD(0.7) 기준으로 통과 여부를 판정한다.
    LLM 호출 실패 시에도 항상 결과를 반환한다(원본 보존 우선).
    """

    PASS_THRESHOLD: float = 0.7  # 70% 이상이면 통과

    def __init__(self, workspace: str = "", providers: list[str] | None = None):
        self.workspace = workspace
        self._providers = providers  # None이면 ParallelCritiqueEngine이 자동 탐지

    # ── 공개 메서드 ──

    def verify(
        self,
        task_input: str,
        work_items: list,
        project_brief: dict | None = None,
    ) -> PlanVerifyResult:
        """
        work_items를 실행 전에 검증한다.

        Parameters
        ----------
        task_input:     원본 사용자 요청 문자열
        work_items:     검증 대상 work-item 목록 (dict 또는 기타 직렬화 가능 객체)
        project_brief:  프로젝트 배경 정보 (선택) — MergedCritique task_profile로 전달

        Returns
        -------
        PlanVerifyResult
            예외 발생 시 passed=False, score=0.0으로 반환 (파이프라인은 WARN 처리 후 계속).
        """
        try:
            artifact = self._build_artifact(task_input, work_items, project_brief)
            task_profile = self._build_task_profile(task_input, project_brief)
            merged = self._run_critique(artifact, task_profile)

            # issues: confirmed + suspected 합산 (confirmed 우선)
            issues: list[str] = list(merged.confirmed_gaps) + list(merged.suspected_gaps)
            suggestions: list[str] = list(merged.revision_instructions)
            passed = merged.score >= self.PASS_THRESHOLD

            return PlanVerifyResult(
                passed=passed,
                score=merged.score,
                issues=issues,
                suggestions=suggestions,
                refined_items=None,
            )
        except Exception as exc:
            # 검증 자체가 실패해도 파이프라인을 중단하지 않는다
            print(f"[PlanVerifier] verify() 예외 발생 — 검증 스킵: {exc}")
            return PlanVerifyResult(
                passed=False,  # 검증 실패 시 명시적 실패 — 파이프라인이 WARN 처리
                score=0.0,
                issues=[f"verify_error: {exc}"],
                suggestions=[],
                refined_items=None,
            )

    def refine(
        self,
        task_input: str,
        work_items: list,
        issues: list[str],
        project_brief: dict | None = None,
    ) -> list:
        """
        issues를 참고해 work_items를 재작성 시도한다.

        Parameters
        ----------
        task_input:    원본 사용자 요청 문자열
        work_items:    원본 work-item 목록
        issues:        verify()에서 반환된 문제 목록
        project_brief: 프로젝트 배경 정보 (선택)

        Returns
        -------
        재작성된 work-item 목록.
        LLM 호출 실패 또는 파싱 실패 시 원본 work_items 반환.
        """
        if not issues:
            # 개선할 사항 없음 — 원본 반환
            return list(work_items)

        try:
            return self._llm_refine(task_input, work_items, issues, project_brief)
        except Exception as exc:
            print(f"[PlanVerifier] refine() 예외 발생 — 원본 반환: {exc}")
            return list(work_items)

    # ── 내부 메서드 ──

    def _build_artifact(
        self,
        task_input: str,
        work_items: list,
        project_brief: dict | None,
    ) -> dict:
        """
        ParallelCritiqueEngine에 전달할 artifact dict를 구성한다.
        work_items를 직렬화 가능 형태로 변환하여 담는다.
        """
        serialized_items: list[Any] = []
        for item in work_items:
            if isinstance(item, dict):
                serialized_items.append(item)
            elif hasattr(item, "__dict__"):
                serialized_items.append(vars(item))
            else:
                serialized_items.append(str(item))

        artifact: dict[str, Any] = {
            "goal": str(task_input or "").strip(),
            "work_items": serialized_items,
            "item_count": len(serialized_items),
        }
        if project_brief:
            artifact["project_brief"] = project_brief

        return artifact

    def _build_task_profile(
        self,
        task_input: str,
        project_brief: dict | None,
    ) -> dict:
        """task_profile dict 구성 — MergedCritique 컨텍스트로 사용."""
        profile: dict[str, Any] = {
            "original_request": str(task_input or "").strip(),
        }
        if project_brief:
            profile.update(project_brief)
        return profile

    def _run_critique(self, artifact: dict, task_profile: dict):
        """
        ParallelCritiqueEngine을 임포트해 비평을 실행한다.
        타임아웃은 ParallelCritiqueEngine 내부(120s)를 그대로 사용하며,
        LLM refine의 timeout_sec=120은 별도 경로이다.
        """
        from core.parallel_critique import ParallelCritiqueEngine
        engine = ParallelCritiqueEngine(
            workspace=self.workspace,
            providers=self._providers,
        )
        return engine.critique(artifact=artifact, task_profile=task_profile)

    def _llm_refine(
        self,
        task_input: str,
        work_items: list,
        issues: list[str],
        project_brief: dict | None,
    ) -> list:
        """
        LLM에게 issues를 알려주고 work_items 재작성을 요청한다.
        requirement_llm.execute_requirement_prompt 패턴 재사용.
        JSON 파싱 실패 시 원본 반환.
        """
        from core.requirement_llm import execute_requirement_prompt

        items_json = json.dumps(
            [
                (item if isinstance(item, (dict, list, str, int, float, bool)) else str(item))
                for item in work_items
            ],
            ensure_ascii=False,
            indent=2,
        )
        issues_text = "\n".join(f"- {i}" for i in issues)

        prompt = f"""You are a plan refinement assistant.
The following work-items were generated for a task but have quality issues.
Rewrite the work-items to address all issues listed below.
Return the improved work-items as a JSON array in the same structure as the input.
Do NOT include any explanation — return JSON only.

Original task:
{task_input}

Issues to address:
{issues_text}

Current work-items:
{items_json}
"""
        if project_brief:
            brief_text = json.dumps(project_brief, ensure_ascii=False)
            prompt = f"Project context: {brief_text}\n\n{prompt}"

        result = execute_requirement_prompt(
            prompt,
            workspace=self.workspace,
            run_id="plan_verifier_refine",
            timeout_sec=120,
        )

        if not result.get("ok"):
            print(f"[PlanVerifier] LLM refine 실패: {result.get('errors')}")
            return list(work_items)

        text = str(result.get("text") or "").strip()
        # JSON 배열 추출
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                refined = json.loads(text[start:end])
                if isinstance(refined, list) and len(refined) > 0:
                    return refined
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"[PlanVerifier] refine JSON 파싱 실패: {exc}")

        print("[PlanVerifier] refine 결과 파싱 불가 — 원본 반환")
        return list(work_items)


__all__ = ["PlanVerifier", "PlanVerifyResult"]

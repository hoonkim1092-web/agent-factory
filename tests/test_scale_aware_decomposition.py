"""규모 인지 역할 분해 (B안, 2026-06-20) 검증.

설계: docs/2026-06-20-scale-aware-role-decomposition-design.md (B안)
규모 신호는 route["required_stages"]에서 직접 유도한다(gear 키 미사용).
- research·design 둘 다 부재 → minimal, 아니면 standard.
- QA 완화 = minimal AND merge_mode∈{never,manual} 교집합.
"""
from unittest.mock import patch

import pytest

from core.bootstrap_roles import (
    DECOMPOSITION_MINIMAL,
    DECOMPOSITION_STANDARD,
    ProjectPlanningDirector,
)


class _CaptureLLM:
    """plan()이 생성한 프롬프트를 가로채고 호출자 지정 payload를 반환."""

    def __init__(self, payload=None):
        self.prompt = None
        self._payload = payload if payload is not None else {
            "execution_strategy": "parallel",
            "planning_steps": [],
            "roles": [
                {"id": "dev", "name": "Dev", "objective": "impl",
                 "required_skills": [], "owned_modules": ["m1"]}
            ],
            "modules": [
                {"id": "m1", "name": "M1", "summary": "s", "owner_role": "dev",
                 "depends_on": [], "deliverables": ["d"], "feature_slices": ["f"],
                 "tasks": []}
            ],
            "todo_items": [],
        }

    def generate_json(self, prompt):
        self.prompt = prompt
        return dict(self._payload)


def _make_director(capture):
    """LLMEngine/네트워크 없이 director를 만들고 capture LLM을 주입."""
    with patch("core.bootstrap_roles.check_llm_available", return_value=False):
        director = ProjectPlanningDirector(mr=object())
    director._llm_available = True
    director.llm = capture
    return director


def _prompt_for(brief, **kwargs):
    cap = _CaptureLLM()
    director = _make_director(cap)
    director.plan("build a small thing", brief, **kwargs)
    return cap.prompt


# ─────────────────────────── D1/D3 프롬프트 분기 ───────────────────────────

class TestDecompositionPrompt:
    def test_standard_default_is_director(self):
        p = _prompt_for({"goal": "x"})
        assert p.startswith("You are a project planning director.")
        assert "Scale Constraint" not in p
        assert "senior engineer scoping" not in p

    def test_standard_explicit_matches_default(self):
        a = _prompt_for({"goal": "x"})
        b = _prompt_for({"goal": "x"}, decomposition_strength="standard")
        assert a == b

    def test_minimal_explicit_prompt(self):
        p = _prompt_for({"goal": "x"}, decomposition_strength=DECOMPOSITION_MINIMAL)
        assert p.startswith("You are a senior engineer scoping a SMALL, surgical change.")
        assert "FEWEST roles and modules" in p
        assert "At most 2 roles" in p
        assert "project planning director" not in p

    def test_garbage_normalizes_to_standard(self):
        # INV-D1b
        p = _prompt_for({"goal": "x"}, decomposition_strength="garbage")
        assert p.startswith("You are a project planning director.")
        assert "Scale Constraint" not in p

    def test_minimal_derived_when_no_research_no_design(self):
        # B안 핵심: required_stages에 research·design 둘 다 부재 → minimal
        p = _prompt_for({"goal": "x", "route": {"required_stages": ["implement", "test"]}})
        assert "FEWEST roles and modules" in p
        assert "senior engineer scoping" in p

    def test_standard_when_design_in_stages(self):
        # 워처 High 회귀 방지: Tier3 Floor2가 design 강제 → standard
        p = _prompt_for({"goal": "x", "route": {"required_stages": ["design", "implement", "test"]}})
        assert "Scale Constraint" not in p
        assert p.startswith("You are a project planning director.")

    def test_standard_when_research_in_stages(self):
        p = _prompt_for({"goal": "x", "route": {"required_stages": ["research", "implement"]}})
        assert "Scale Constraint" not in p

    def test_explicit_minimal_overrides_stage_derivation(self):
        # INV-D3b: 호출자 minimal 명시는 route 유도보다 우선
        p = _prompt_for(
            {"goal": "x", "route": {"required_stages": ["research", "design", "implement"]}},
            decomposition_strength=DECOMPOSITION_MINIMAL,
        )
        assert "FEWEST roles and modules" in p

    def test_empty_stages_stay_standard(self):
        # required_stages 빈 리스트/부재 → 하위호환(full=standard)
        assert "Scale Constraint" not in _prompt_for({"goal": "x", "route": {"required_stages": []}})
        assert "Scale Constraint" not in _prompt_for({"goal": "x", "route": {}})

    def test_module_zero_ban_retained_in_minimal(self):
        # §4.4: 모듈0 금지는 모든 규모 유지(빈 분해 방지)
        p = _prompt_for({"goal": "x"}, decomposition_strength=DECOMPOSITION_MINIMAL)
        assert "Do NOT make a role own zero modules." in p

    def test_standard_byte_layout_preserved(self):
        # INV-D1c: standard 프롬프트는 director 정체성으로 시작하고 QA mandate로 끝남
        p = _prompt_for({"goal": "x"})
        assert p.startswith("You are a project planning director.\nUser task:")
        assert p.endswith(
            "The qa_engineer must own at least one module with verify-phase tasks."
        )
        assert "\n\nMANDATORY: You MUST always include a \"qa_engineer\" role." in p


# ─────────────────────────── D2 QA 완화 게이트 ───────────────────────────

# QA 역할/verify 모듈이 없는 payload — _ensure_qa_role 호출 시에만 qa_engineer가 추가됨.
_NO_QA_PAYLOAD = {
    "execution_strategy": "parallel",
    "planning_steps": [],
    "roles": [
        {"id": "dev", "name": "Dev", "objective": "impl",
         "required_skills": [], "owned_modules": ["m1"]}
    ],
    "modules": [
        {"id": "m1", "name": "M1", "summary": "s", "owner_role": "dev",
         "depends_on": [], "deliverables": ["d"], "feature_slices": ["f"],
         "tasks": [{"id": "t1", "title": "T", "instruction": "do",
                    "owner_role": "dev", "phase": "build", "depends_on": [],
                    "acceptance": ["ok"], "artifacts": ["a"]}]}
    ],
    "todo_items": [],
}


def _plan_with(brief, **kwargs):
    cap = _CaptureLLM(payload=_NO_QA_PAYLOAD)
    director = _make_director(cap)
    result = director.plan("build a small thing", brief, **kwargs)
    return result, cap.prompt


def _has_qa(result):
    return any(r.get("id") == "qa_engineer" for r in (result.get("roles") or []))


class TestQARelaxation:
    def _minimal_route(self, merge_mode=None):
        route = {"required_stages": ["implement", "test"]}
        if merge_mode is not None:
            route["_merge_mode"] = merge_mode
        return {"goal": "x", "route": route}

    def test_minimal_never_skips_qa(self):
        result, _ = _plan_with(self._minimal_route("never"))
        assert not _has_qa(result)

    def test_minimal_manual_skips_qa(self):
        result, _ = _plan_with(self._minimal_route("manual"))
        assert not _has_qa(result)

    def test_minimal_auto_policy_forces_qa(self):
        # INV-D2b
        result, _ = _plan_with(self._minimal_route("auto_policy"))
        assert _has_qa(result)

    def test_minimal_missing_merge_mode_forces_qa(self):
        # INV-D2a: merge_mode 부재 → auto_policy 간주 → QA 강제
        result, _ = _plan_with(self._minimal_route(None))
        assert _has_qa(result)

    def test_standard_never_still_forces_qa(self):
        # INV-D2c: full(standard)은 merge_mode 무관 항상 QA
        brief = {"goal": "x", "route": {"required_stages": ["design", "implement"],
                                        "_merge_mode": "never"}}
        result, _ = _plan_with(brief)
        assert _has_qa(result)

    def test_relaxed_minimal_prompt_omits_qa_mandate(self):
        _, prompt = _plan_with(self._minimal_route("never"))
        # _QA_MANDATE 하드코딩 + policy.yaml QA constraint 양쪽 모두 생략 (cross-review F2)
        assert "MANDATORY: You MUST always include" not in prompt
        assert "qa_engineer role" not in prompt

    def test_non_relaxed_minimal_prompt_keeps_qa_mandate(self):
        _, prompt = _plan_with(self._minimal_route("auto_policy"))
        assert "MANDATORY: You MUST always include" in prompt

    def test_minimal_prompt_omits_conflicting_role_count_rule(self):
        # cross-review F1: minimal 프롬프트는 policy의 "At least 2 roles" 같은
        # 역할 수 하한 규칙을 주입하지 않는다(_MINIMAL_SCALE_RULES와 충돌 방지).
        _, prompt = _plan_with(self._minimal_route("auto_policy"))
        assert "At least 2 roles" not in prompt
        assert "2 to 5 roles only" not in prompt
        # minimal 고유 제약은 여전히 존재
        assert "At most 2 roles" in prompt


# ─────────────────────────── _build_policy_rules 규모 인지 (F1/F2) ───────────────────────────

class TestPolicyRulesScaleAware:
    def test_default_matches_explicit_standard(self):
        # 기본값(standard/False)은 바이트 동일 — 독립 호출자 하위호환
        from core.bootstrap_roles import _build_policy_rules
        assert _build_policy_rules() == _build_policy_rules(DECOMPOSITION_STANDARD, False)

    def test_standard_keeps_role_count(self):
        from core.bootstrap_roles import _build_policy_rules
        rules = _build_policy_rules(DECOMPOSITION_STANDARD, False)
        # 실 policy.yaml(roles.min=2, max 없음) → "At least 2 roles" 유지
        assert "At least 2 roles" in rules

    def test_minimal_drops_role_count(self):
        # F1
        from core.bootstrap_roles import _build_policy_rules
        rules = _build_policy_rules(DECOMPOSITION_MINIMAL, False)
        assert "At least 2 roles" not in rules
        assert "roles only" not in rules

    def test_qa_relaxed_drops_qa_constraint(self):
        # F2
        from core.bootstrap_roles import _build_policy_rules
        relaxed = _build_policy_rules(DECOMPOSITION_MINIMAL, True)
        kept = _build_policy_rules(DECOMPOSITION_MINIMAL, False)
        assert "qa_engineer" not in relaxed.lower()
        assert "qa_engineer" in kept.lower()

    def test_fallback_minimal_drops_role_count_and_qa(self):
        # policy.yaml 부재 폴백 경로도 규모 인지
        from unittest.mock import patch
        from core.bootstrap_roles import _build_policy_rules
        with patch("core.bootstrap_roles._load_task_decomposition_policy", return_value={}):
            std = _build_policy_rules(DECOMPOSITION_STANDARD, False)
            mini = _build_policy_rules(DECOMPOSITION_MINIMAL, True)
        assert "2 to 5 roles only" in std
        assert "Include at least one verify task overall" in std
        assert "2 to 5 roles only" not in mini
        assert "verify task" not in mini


# ─────────────────────────── INV-F1 fallback / 하위호환 ───────────────────────────

class TestFallbackAndBackwardCompat:
    def _fallback_director(self):
        with patch("core.bootstrap_roles.check_llm_available", return_value=False):
            return ProjectPlanningDirector(mr=object())

    def test_fallback_unaffected_by_decomposition_strength(self):
        # INV-F1: _llm_available=False 경로는 규모 인지 미적용 — 결과 동일
        director = self._fallback_director()
        brief = {"goal": "build api", "required_skills": ["api_server", "test_guard"]}
        a = director.plan("t", brief)
        b = director.plan("t", brief, decomposition_strength=DECOMPOSITION_MINIMAL)
        assert a == b
        assert "roles" in a

    def test_two_arg_call_still_works(self):
        # INV-D1a: 기존 2-arg 호출 하위호환
        cap = _CaptureLLM()
        director = _make_director(cap)
        director.plan("t", {"goal": "x"})
        assert cap.prompt.startswith("You are a project planning director.")

    def test_three_arg_memory_context_call_still_works(self):
        cap = _CaptureLLM()
        director = _make_director(cap)
        director.plan("t", {"goal": "x"}, memory_context={"recall_count": 0})
        assert cap.prompt.startswith("You are a project planning director.")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

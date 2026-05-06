"""Regression — work_item_generator._reference_bullets + D2 Phase Flow 테스트.

_reference_bullets: producer(researcher._collect_llm_prior_knowledge)가 실제로 emit하는
title 형식 "[LLM prior] {label}: {text}"을 그대로 쓴다.
consumer는 bullet 라인에서 prefix 중복을 제거해야 한다.

D2: _fallback_impl_design이 '## Event Sequence / Phase Flow' 섹션을 포함하는지 검증.
"""

from __future__ import annotations

from core.work_item_generator import _reference_bullets, _fallback_impl_design


def test_llm_prior_references_appear_in_bullets():
    brief = {
        "local_references": [],
        "web_references": [
            {"title": "Tavily Result", "url": "https://example.com", "excerpt": "live web hit"}
        ],
        "llm_prior_references": [
            # producer shape: title에 "[LLM prior] " prefix 부착됨 (researcher.py:630)
            {"title": "[LLM prior] Concept: model recall fallback", "excerpt": "model recall fallback"}
        ],
    }
    out = _reference_bullets(brief, limit=8)
    assert "Web: Tavily Result" in out
    # 라인은 "- LLM prior: Concept: model recall fallback" 형태여야 한다 (producer prefix 중복 제거).
    assert "LLM prior: Concept: model recall fallback" in out
    # 중복 prefix가 production output에 새지 않는지 회귀 검증.
    assert "[LLM prior] [LLM prior]" not in out
    assert "LLM prior: [LLM prior]" not in out


def test_llm_prior_only_still_renders():
    brief = {
        "local_references": [],
        "web_references": [],
        "llm_prior_references": [
            {"title": "[LLM prior] Risk: fallback excerpt", "excerpt": "fallback excerpt"}
        ],
    }
    out = _reference_bullets(brief, limit=8)
    assert "LLM prior: Risk: fallback excerpt" in out
    assert "[LLM prior] [LLM prior]" not in out
    assert "(no additional references)" not in out


# --- D2: Event Sequence / Phase Flow 섹션 검증 ---

def test_d2_fallback_impl_design_contains_phase_flow_section():
    """D2: _fallback_impl_design이 '## Event Sequence / Phase Flow' 섹션을 포함한다."""
    brief = {"goal": "포커 게임 구현", "tech_stack": ["Python", "WebSocket"]}
    role_plan = {"modules": [], "execution_strategy": "sequential"}
    out = _fallback_impl_design("poker-backend", brief, role_plan)
    assert "## Event Sequence / Phase Flow" in out


def test_d2_fallback_uses_state_machine_from_domain_specs_summary():
    """D2: domain_specs_summary.state_machine이 있으면 Phase Flow 섹션에 반영된다."""
    brief = {
        "goal": "포커 게임",
        "domain_specs_summary": {
            "state_machine": "# State Machine\n- Phase 1: Waiting\n- Phase 2: Dealing\n- Phase 3: Betting"
        },
    }
    role_plan = {"modules": [], "execution_strategy": "sequential"}
    out = _fallback_impl_design("poker-backend", brief, role_plan)
    assert "## Event Sequence / Phase Flow" in out
    assert "State Machine" in out or "Phase 1" in out


def test_d2_fallback_generic_phases_when_no_state_machine():
    """D2: domain_specs_summary 없으면 4-phase 기본 템플릿이 삽입된다."""
    brief = {"goal": "일반 서비스"}
    role_plan = {"modules": [], "execution_strategy": "parallel"}
    out = _fallback_impl_design("generic-service", brief, role_plan)
    assert "## Event Sequence / Phase Flow" in out
    assert "Phase 1" in out
    assert "Phase 4" in out

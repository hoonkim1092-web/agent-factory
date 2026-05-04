"""Regression — work_item_generator._reference_bullets must include llm_prior_references.

Fixture는 producer(researcher._collect_llm_prior_knowledge)가 실제로 emit하는 title 형식
"[LLM prior] {label}: {text}"을 그대로 쓴다. consumer는 bullet 라인에서 prefix 중복을 제거해야 한다.
"""

from __future__ import annotations

from core.work_item_generator import _reference_bullets


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

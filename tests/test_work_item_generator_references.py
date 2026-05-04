"""Regression — work_item_generator._reference_bullets must include llm_prior_references.

결함 #1 정정 후 LLM prior가 `llm_prior_references` 슬롯으로 분리되었는데
work_item_generator는 `web_references`만 읽고 있어 LLM prior 정보가 work item 생성에서 누락됐다.
이 테스트는 두 슬롯 모두 bullet으로 출력되는지 확인한다.
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
            {"title": "LLM Prior Knowledge", "excerpt": "model recall fallback"}
        ],
    }
    out = _reference_bullets(brief, limit=8)
    assert "Web: Tavily Result" in out
    assert "LLM prior: LLM Prior Knowledge" in out


def test_llm_prior_only_still_renders():
    brief = {
        "local_references": [],
        "web_references": [],
        "llm_prior_references": [
            {"title": "LLM Prior", "excerpt": "fallback excerpt"}
        ],
    }
    out = _reference_bullets(brief, limit=8)
    assert "LLM prior: LLM Prior" in out
    assert "(no additional references)" not in out

"""tests/test_work_item_generator_structured_evidence.py — B-1 fallback trace 회귀 가드.

검증 범위:
1. spec fallback ## 섹션 수 12 유지 (_extract_section_outline expected_count=12 회귀 방지)
2. plan/spec/design Evidence 섹션에 structured evidence 3필드 라벨 렌더링 확인
3. structured evidence 값에 \\n## 있어도 h2 count 증가 없음 (sanitizer 회귀 가드)
4. skill_gap_hypotheses broken entry silent skip
"""
from __future__ import annotations

import re

from core.work_item_generator import (
    _extract_section_outline,
    _fallback_feature_plan,
    _fallback_feature_spec,
    _fallback_impl_design,
    _inline,
    _skill_gap_bullets,
    _structured_evidence_block,
)

_SECTION_HEADER_RE = re.compile(r"^\s*##\s+(.+?)\s*$")


def _count_h2(markdown: str) -> int:
    return sum(1 for line in markdown.splitlines() if _SECTION_HEADER_RE.match(line))


def _minimal_brief(**overrides) -> dict:
    base = {
        "goal": "test goal",
        "required_capabilities": ["cap_a", "cap_b"],
        "verification_focus": ["verify_x", "verify_y"],
        "skill_gap_hypotheses": [
            {
                "need_skill_id": "skill_foo",
                "required_capabilities": ["cap_a"],
                "reuse_expectation": "enhance",
                "reason": "existing skill partially matches",
            }
        ],
    }
    base.update(overrides)
    return base


def _minimal_role_plan() -> dict:
    return {"modules": [], "roles": []}


def _minimal_task_board() -> dict:
    return {"tasks": []}


# ────────────────────────────────────────────────
# 1. spec fallback ## count = 12 (expected_count 회귀)
# ────────────────────────────────────────────────

def test_spec_fallback_h2_count_unchanged():
    """structured evidence 추가 후에도 spec fallback ## 헤더가 12개."""
    brief = _minimal_brief()
    md = _fallback_feature_spec("wi-test", brief, _minimal_role_plan(), _minimal_task_board())
    assert _count_h2(md) == 12, f"expected 12 ## sections, got {_count_h2(md)}"


def test_spec_fallback_outline_parseable():
    """_extract_section_outline이 expected=12로 빈 문자열을 반환하지 않음."""
    brief = _minimal_brief()
    md = _fallback_feature_spec("wi-test", brief, _minimal_role_plan(), _minimal_task_board())
    outline = _extract_section_outline(md, expected_count=12)
    assert outline != "", "spec outline must be parseable (non-empty)"
    assert "§1" in outline


# ────────────────────────────────────────────────
# 2. plan/spec/design Evidence 섹션 라벨 확인
# ────────────────────────────────────────────────

def test_plan_evidence_has_structured_labels():
    brief = _minimal_brief()
    md = _fallback_feature_plan("wi-test", brief, _minimal_role_plan())
    assert "Skill procurement signals" in md
    assert "Verification focus" in md
    assert "Skill gap hypotheses" in md


def test_spec_evidence_has_structured_labels():
    brief = _minimal_brief()
    md = _fallback_feature_spec("wi-test", brief, _minimal_role_plan(), _minimal_task_board())
    assert "Skill procurement signals" in md
    assert "Verification focus" in md
    assert "Skill gap hypotheses" in md


def test_design_evidence_has_structured_labels():
    brief = _minimal_brief()
    md = _fallback_impl_design("wi-test", brief, _minimal_role_plan())
    assert "Skill procurement signals" in md
    assert "Verification focus" in md
    assert "Skill gap hypotheses" in md


def test_plan_no_new_h2_added():
    """plan fallback에 새 ## 헤더가 추가되지 않음. 현 plan 헤더 수 유지."""
    brief_empty = _minimal_brief(required_capabilities=[], verification_focus=[], skill_gap_hypotheses=[])
    brief_full = _minimal_brief()
    md_empty = _fallback_feature_plan("wi-test", brief_empty, _minimal_role_plan())
    md_full = _fallback_feature_plan("wi-test", brief_full, _minimal_role_plan())
    assert _count_h2(md_empty) == _count_h2(md_full)


# ────────────────────────────────────────────────
# 3. sanitizer — 값에 \n## 있어도 h2 count 증가 없음
# ────────────────────────────────────────────────

def test_inline_strips_newlines():
    assert _inline("hello\n## Injected Header\nworld") == "hello ## Injected Header world"


def test_structured_evidence_block_no_h2_injection():
    """required_capabilities 값에 ## 패턴이 있어도 h2 미생성."""
    brief = _minimal_brief(
        required_capabilities=["normal_cap", "## Fake Header"],
        verification_focus=["verify\n## Another Header"],
        skill_gap_hypotheses=[{
            "need_skill_id": "skill_x",
            "required_capabilities": ["cap"],
            "reuse_expectation": "forge",
            "reason": "reason with\n## embedded header",
        }],
    )
    block = _structured_evidence_block(brief)
    h2_count = sum(1 for line in block.splitlines() if _SECTION_HEADER_RE.match(line))
    assert h2_count == 0, f"structured_evidence_block must not emit ## headers; got {h2_count}"


def test_spec_with_injected_newlines_keeps_h2_count():
    """값에 개행+## 있어도 spec fallback ## count = 12."""
    brief = _minimal_brief(
        verification_focus=["check\n## Injected"],
        skill_gap_hypotheses=[{
            "need_skill_id": "s",
            "required_capabilities": [],
            "reuse_expectation": "forge",
            "reason": "bad\n## header injection",
        }],
    )
    md = _fallback_feature_spec("wi-test", brief, _minimal_role_plan(), _minimal_task_board())
    assert _count_h2(md) == 12


# ────────────────────────────────────────────────
# 4. skill_gap_hypotheses broken entry silent skip
# ────────────────────────────────────────────────

def test_skill_gap_bullets_skips_non_dict():
    """list[str] 또는 mixed entry가 들어와도 dict 아닌 항목은 silent skip."""
    brief = {
        "skill_gap_hypotheses": [
            "plain_string",
            {},  # need_skill_id 없음
            {
                "need_skill_id": "valid_skill",
                "required_capabilities": ["cap_x"],
                "reuse_expectation": "reuse",
                "reason": "ok",
            },
        ]
    }
    bullets = _skill_gap_bullets(brief)
    assert len(bullets) == 1
    assert "valid_skill" in bullets[0]


def test_skill_gap_bullets_empty_on_missing_field():
    brief = {"skill_gap_hypotheses": []}
    assert _skill_gap_bullets(brief) == []


def test_structured_evidence_block_empty_brief():
    """3필드 없는 brief에서 structured_block이 빈 문자열."""
    brief: dict = {}
    block = _structured_evidence_block(brief)
    assert block == ""

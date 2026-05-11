"""
tests/test_critic_skill_router.py
==================================
Tier 2 Phase 3 단계 1 회귀 테스트 — 영역별 SKILL 매핑 정확도.

검증 대상: core/critic_skill_router.py
설계 출처: docs/2026-05-11-tier2-domain-expert-panel-design.md §4.2
"""
from __future__ import annotations

import os

from core.critic_skill_router import (
    map_paths_to_skills,
    resolve_skill_paths,
    _DEFAULT_SKILL,
)


# ── map_paths_to_skills — 영역별 매핑 ────────────────────────────────────────


def test_empty_paths_returns_default():
    """빈 입력 → 기본 SKILL만 반환."""
    assert map_paths_to_skills([]) == [_DEFAULT_SKILL]


def test_unknown_path_returns_default():
    """매핑 규칙에 없는 경로 → 기본 SKILL만 반환."""
    result = map_paths_to_skills(["random/unknown/file.txt"])
    assert result == [_DEFAULT_SKILL]


def test_frontend_tsx_maps_to_react_skills():
    """프론트엔드 .tsx → react_coding + frontend_ui_ux 추천."""
    result = map_paths_to_skills(["frontend/App.tsx"])
    assert "react_coding" in result
    assert "frontend_ui_ux" in result
    assert _DEFAULT_SKILL in result


def test_css_file_maps_to_frontend():
    """CSS 변경 → 프론트엔드 영역."""
    result = map_paths_to_skills(["src/styles/main.css"])
    assert "react_coding" in result or "frontend_ui_ux" in result


def test_langchain_path_maps_to_domain():
    """LangChain 관련 경로 → domain SKILL."""
    result = map_paths_to_skills(["core/langchain_adapter.py"])
    assert "domain" in result
    assert _DEFAULT_SKILL in result


def test_memory_system_maps_to_core_memory():
    """memory_system → core_memory SKILL."""
    result = map_paths_to_skills(["core/memory_system/episode_extractor.py"])
    assert "core_memory" in result


def test_orchestrator_maps_to_state_machine():
    """오케스트레이터 변경 → state_machine_exception_planning."""
    result = map_paths_to_skills(["core/dynamic_orchestrator.py"])
    assert "state_machine_exception_planning" in result


def test_approval_gate_maps_to_state_machine():
    """approval_gate 변경 → state_machine_exception_planning."""
    result = map_paths_to_skills(["core/approval_gate.py"])
    assert "state_machine_exception_planning" in result


def test_max_skills_caps_result():
    """max_skills로 결과 개수 제한."""
    # frontend 변경은 3개 SKILL 매칭 (code_review_guide, react_coding, frontend_ui_ux)
    result = map_paths_to_skills(["frontend/App.tsx"], max_skills=2)
    assert len(result) <= 2


def test_default_max_is_three():
    """기본 max_skills=3 (12-cap 정책 일관 — context 부담 방지)."""
    result = map_paths_to_skills(
        ["frontend/App.tsx", "core/memory_system/x.py", "core/dynamic_orchestrator.py"]
    )
    assert len(result) <= 3


def test_dedup_across_multiple_paths():
    """여러 경로가 같은 SKILL 매칭 → 중복 제거."""
    result = map_paths_to_skills(["core/agent_runner.py", "core/fsa_loop.py"])
    # 둘 다 state_machine_exception_planning 매칭
    assert result.count("state_machine_exception_planning") == 1


def test_windows_backslash_normalization():
    """Windows 경로 (백슬래시) 정상 처리."""
    result = map_paths_to_skills(["core\\memory_system\\x.py"])
    assert "core_memory" in result


def test_first_match_wins_per_path():
    """한 경로가 여러 규칙에 매칭 가능해도 첫 규칙만 적용."""
    # core/memory_system/x.py는 memory 규칙 (core_memory)에 먼저 매칭됨
    result = map_paths_to_skills(["core/memory_system/x.py"])
    assert "core_memory" in result


def test_order_preserved():
    """매칭 순서가 결과 리스트에 유지됨."""
    # frontend/App.tsx 단독 → code_review_guide(첫번째), react_coding, frontend_ui_ux 순
    result = map_paths_to_skills(["frontend/App.tsx"], max_skills=3)
    assert result[0] == "code_review_guide"


# ── resolve_skill_paths — 실제 파일 시스템 검증 ─────────────────────────────


def test_resolve_returns_existing_paths(tmp_path):
    """존재하는 SKILL.md/디렉토리만 반환."""
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # SKILL.md 있는 경우
    skill_a = skills_root / "skill_a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text("# A")

    # 디렉토리만 있는 경우 (SKILL.md 없음)
    skill_b = skills_root / "skill_b"
    skill_b.mkdir()
    (skill_b / "skill.py").write_text("# B")

    # 존재하지 않는 SKILL
    paths = resolve_skill_paths(
        ["skill_a", "skill_b", "skill_nonexistent"],
        skills_root=str(skills_root),
    )
    assert any("skill_a" in p and "SKILL.md" in p for p in paths)
    assert any(p.endswith("skill_b") for p in paths)
    assert not any("skill_nonexistent" in p for p in paths)


def test_resolve_empty_input():
    """빈 입력 → 빈 결과."""
    assert resolve_skill_paths([]) == []


# ── CLI 진입점 smoke ─────────────────────────────────────────────────────────


def test_cli_main_smoke(capsys, monkeypatch):
    """CLI main()이 SystemExit 없이 정상 출력."""
    import sys

    monkeypatch.setattr(sys, "argv", [
        "critic_skill_router",
        "--diff-paths", "frontend/App.tsx core/memory_system/x.py",
        "--max-skills", "3",
    ])

    from core.critic_skill_router import main
    main()

    captured = capsys.readouterr()
    output_lines = [ln.strip() for ln in captured.out.splitlines() if ln.strip()]
    assert len(output_lines) >= 1
    assert _DEFAULT_SKILL in output_lines or "react_coding" in output_lines

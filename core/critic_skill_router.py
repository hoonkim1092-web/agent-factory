"""
core/critic_skill_router.py
============================
Tier 2 Phase 3 단계 1 — 영역별 Critic SKILL 동적 라우팅.

af-critic 호출 시 변경 파일 경로를 분석해서 적절한 영역 전문 SKILL을 추천한다.
실제 SKILL.md 로드는 호출자(Bash/Read)가 수행하고, 본 모듈은 매핑만 담당.

설계 출처: docs/2026-05-11-tier2-domain-expert-panel-design.md §4.2
잠정 설계 (cross-review 5/13+ 후 v2 확정 예정).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# ──────────────────────────────────────────────────────────────
# 영역 매핑 규칙 (룰 기반, 정규식)
# 우선순위: 위에서 아래로 (첫 매칭 사용)
# 형식: (regex_pattern, [skill_id, ...])
# ──────────────────────────────────────────────────────────────

_DEFAULT_SKILL = "code_review_guide"

_DOMAIN_RULES: list[tuple[str, list[str]]] = [
    # 프론트엔드
    (
        r"\.(tsx|jsx|css|scss|sass)$|^(frontend|client|web)/|/components?/",
        ["code_review_guide", "react_coding", "frontend_ui_ux"],
    ),
    # 디자인 시스템 / UX
    (
        r"^(design|ui|ux)/|/design[-_]system/",
        ["code_review_guide", "create_design_system", "perform_web_design_review"],
    ),
    # LangChain / LangGraph 도메인
    (
        r"langchain|langgraph|deep[-_]?agents",
        ["code_review_guide", "domain"],  # skills/domain/langchain/SKILL.md
    ),
    # AF 메모리 시스템
    (
        r"^core/memory_system/",
        ["code_review_guide", "core_memory"],
    ),
    # AF 스킬 시스템 자체
    (
        r"^core/(skill_|semantic_embedder|skill_registry|skill_loader)",
        ["code_review_guide"],  # AF skill system은 일반 리뷰만 (자체 SKILL은 메타)
    ),
    # 오케스트레이터 / 상태 머신
    (
        r"^core/(dynamic_orchestrator|project_pipeline|approval_gate|fsa_loop|agent_runner)",
        ["code_review_guide", "state_machine_exception_planning"],
    ),
    # SDD/BDD
    (
        r"\.feature$|gherkin|/spec/",
        ["code_review_guide", "gherkin_sdd_authoring"],
    ),
    # 디버깅/추적
    (
        r"^core/(hooks|tracing|telemetry)",
        ["code_review_guide", "trigger_rule_design"],
    ),
]


def map_paths_to_skills(changed_paths: list[str], max_skills: int = 3) -> list[str]:
    """변경 파일 경로 목록 → 추천 SKILL ID 목록 (중복 제거, max_skills 캡).

    Parameters
    ----------
    changed_paths : list[str]
        변경된 파일 상대 경로 목록 (예: ["core/x.py", "frontend/App.tsx"])
    max_skills : int
        반환할 최대 SKILL 개수 (기본 3 — context 부담 방지, 12-cap 정책 일관)

    Returns
    -------
    list[str]
        추천 SKILL ID 목록 (등장 순서 유지, 중복 제거).
        매칭이 전혀 없으면 [_DEFAULT_SKILL].
    """
    if not changed_paths:
        return [_DEFAULT_SKILL]

    # 정규화: Windows 백슬래시 → 슬래시
    normalized = [p.replace("\\", "/") for p in changed_paths]

    # 매칭된 SKILL 수집 (등장 순서 유지)
    matched: list[str] = []
    seen: set[str] = set()

    for path in normalized:
        for pattern, skills in _DOMAIN_RULES:
            if re.search(pattern, path, flags=re.IGNORECASE):
                for skill_id in skills:
                    if skill_id not in seen:
                        matched.append(skill_id)
                        seen.add(skill_id)
                        if len(matched) >= max_skills:
                            return matched
                break  # path 하나당 첫 매칭 규칙만 적용

    if not matched:
        return [_DEFAULT_SKILL]

    return matched


def resolve_skill_paths(
    skill_ids: list[str], skills_root: str = "skills"
) -> list[str]:
    """SKILL ID 목록 → 실제 SKILL.md 파일 경로 (존재 검증).

    SKILL.md가 없는 영역은 .py 모듈을 가질 수 있음 — 그 경우 디렉토리 경로 반환.
    """
    paths: list[str] = []
    for skill_id in skill_ids:
        skill_md = os.path.join(skills_root, skill_id, "SKILL.md")
        if os.path.isfile(skill_md):
            paths.append(skill_md)
            continue
        # SKILL.md 없으면 디렉토리 자체 (skill.py 또는 다른 entry)
        skill_dir = os.path.join(skills_root, skill_id)
        if os.path.isdir(skill_dir):
            paths.append(skill_dir)
    return paths


# ── CLI 진입점 (af-critic.md Step 0.5에서 호출) ─────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Critic용 영역별 SKILL 추천 (Tier 2 Phase 3 단계 1)"
    )
    parser.add_argument(
        "--diff-paths",
        type=str,
        default="",
        help="공백 구분 변경 파일 경로 목록 (예: 'core/x.py frontend/App.tsx')",
    )
    parser.add_argument(
        "--max-skills",
        type=int,
        default=3,
        help="최대 추천 SKILL 개수 (기본 3, 12-cap 정책 일관)",
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="SKILL ID 대신 실제 SKILL.md 파일 경로로 변환",
    )
    parser.add_argument(
        "--skills-root",
        type=str,
        default="skills",
        help="skills 디렉토리 루트 (기본 'skills')",
    )
    args = parser.parse_args()

    paths = [p for p in args.diff_paths.split() if p.strip()]
    skill_ids = map_paths_to_skills(paths, max_skills=args.max_skills)

    if args.resolve:
        for resolved in resolve_skill_paths(skill_ids, args.skills_root):
            print(resolved)
    else:
        for skill_id in skill_ids:
            print(skill_id)


if __name__ == "__main__":
    main()

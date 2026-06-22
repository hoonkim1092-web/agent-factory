"""
tests/test_cross_review_agent_invariants.py
===========================================
af-cross-review 에이전트 정의 파일(.md/.toml)의 핵심 메커니즘 마커가
조용히 삭제되지 않았는지 단언하는 기계적 가드.

배경 (2026-06-22 사고): Fix 3 위임 worktree 에이전트가 자가보고와 달리
`.claude/agents/af-cross-review.md`·`.codex/agents/af-cross-review.toml`을
stale 축약본으로 덮어써 LLM Wiki 청킹·review_bundle 임베드·MCP fallback·
Step6 Consensus Gate 안내를 대량 삭제했다. 메인이 전수 git diff로 적발했으나
**산문(프롬프트) 자산에는 기계적 그물이 없던 것**이 갭이었다.

이 테스트는 그 갭을 메운다 — cross-review 파이프라인의 핵심 절차 마커가
사라지면 즉시 FAIL시켜, 코드 회귀를 잡는 pytest 그물과 동일한 보호를
프롬프트 자산에도 적용한다. (마커 의도적 제거/리네이밍 시엔 본 목록도 함께 갱신.)
"""
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MD = _REPO_ROOT / ".claude" / "agents" / "af-cross-review.md"
_TOML = _REPO_ROOT / ".codex" / "agents" / "af-cross-review.toml"

# 두 파일 공통 — cross-review 파이프라인의 골격 메커니즘.
_COMMON_MARKERS = (
    "review_bundle",        # §5 Direct Callers 번들 임베드 (단선 해소)
    "cr_findings.json",     # [S3] 구조화 finding 사이드카
    "review_consensus.py",  # 증거수집 합의 게이트 실행기
    "cr_consensus.json",    # 합의 판정 산출물
    "mcp__codex__codex",    # MCP 도구 호출 경로
    "ACCEPT-ADV",           # 설계 스코프 게이트(HOW→advisory 강등) 라벨
    "code_review",          # LLM Wiki 청킹 code_review index 경로
    "AF_SKIP_PROVIDER",     # auth-expired graceful skip 탈출구 안내
)

# .md(Claude 리치본)에만 있는 추가 마커.
_MD_ONLY_MARKERS = (
    "rate_limited",   # usage limit 캐시 기록 분기
    "usage limit",    # rate-limit 감지 문구
    "Consensus Gate", # Step 6 합의 게이트 섹션
    "2b-fallback",    # MCP 미연결 시 codex CLI fallback (single-vendor 회피)
)


@pytest.mark.parametrize("marker", _COMMON_MARKERS)
def test_md_has_common_marker(marker):
    text = _MD.read_text(encoding="utf-8")
    assert marker in text, f".claude/agents/af-cross-review.md 에서 핵심 마커 '{marker}' 누락 — 산문 자산 삭제 의심"


@pytest.mark.parametrize("marker", _COMMON_MARKERS)
def test_toml_has_common_marker(marker):
    text = _TOML.read_text(encoding="utf-8")
    assert marker in text, f".codex/agents/af-cross-review.toml 에서 핵심 마커 '{marker}' 누락 — 산문 자산 삭제 의심"


@pytest.mark.parametrize("marker", _MD_ONLY_MARKERS)
def test_md_has_rich_marker(marker):
    text = _MD.read_text(encoding="utf-8")
    assert marker in text, f".claude/agents/af-cross-review.md 에서 마커 '{marker}' 누락 — 리치본 절차 삭제 의심"

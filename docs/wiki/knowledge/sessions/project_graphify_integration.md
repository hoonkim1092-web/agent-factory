---
name: Graphify 크로스 프로바이더 스킬 통합
description: 토큰 절감 목적으로 오픈소스 Graphify(v0.4.27, MIT)를 래퍼 스킬로 통합 — Phase 1+2 구현 완료 (2026-04-23)
type: project
originSessionId: eba8154a-4f33-409f-bfc8-c5033cd983e7
---
## 현재 상태 (2026-04-23)

- **Phase**: Phase 1+2 완료 (구현 완료, 커밋 `28ae5477`)
- **설계문서**: `docs/features/2026-04-22-graphify-integration.md` (338 lines)
- **커밋**: `79fc5a54`(설계), `28ae5477`(구현), `5f42ccba`(COMPACT 연동)
- **교차검증**: 완료 (Phase A Step 1+2 완료 기준)
- **차단 이슈**: Python 3.14 미지원 (Graphify requires `<3.14`)

## Graphify 핵심 사실 (암기용 캐시)

- PyPI 패키지명: **`graphifyy`** (더블 y) v0.4.27
- 공식 레포: https://github.com/safishamsi/graphify, default branch `v4`
- 라이선스: MIT, ⭐32,604
- 지원 CLI: Claude Code, Codex, OpenCode, Cursor, Gemini, Copilot, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, **Antigravity**, VSCode (14종)
- 설치 경로 (Claude Code): `~/.claude/skills/graphify/SKILL.md` ← **사용자 전역**
- 호출: `/graphify .` (Claude), `$graphify .` (Codex)
- 출력: `graphify-out/{graph.html, GRAPH_REPORT.md, graph.json, cache/}`
- 토큰 절감: 혼합 코퍼스 **71.5×** (공식 벤치마크), 소규모 ~1×
- 자동 주입 대상: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/settings.json` (PreToolUse hook), `.githooks/post-commit`, `.githooks/post-checkout`

**Why:** 대화당 토큰 비용 절감이 사용자 우선 목표. agent-factory는 이미 14개 CLI 지원 대상 중 `af`/`cdx`/`agt`/`lm` 4종 보유 → 기능 복제 없이 래퍼 스킬만 추가하면 됨.

**How to apply:**
- 재개 시 설계문서 §8 "다음 세션 재개 가이드" 먼저 읽을 것
- 문서 §6 Q1~Q11 결정 (권장 default는 §6-4 표 참조)
- **af-critic + af-cross-review 교차검증 실행 후** Phase 1 시작
- Phase 1 명령: `winget install --id=astral-sh.uv -e` → `uv tool install graphifyy --python 3.13`
- Phase 5 설치 시 각 `graphify install --platform X` 마다 `git diff` 로 변경파일 수동 확인
- `graphify-out/` 는 `.gitignore` 필수 (용량 수백 MB 가능)
- agent-factory 메인 Python 3.14 환경은 절대 건드리지 말 것 (uv tool 격리만 사용)

## 결정적 이슈 / 함정

1. **Python 3.14 블로킹**: 사용자 환경이 `python 3.14.3` → `pip install graphifyy` 실패. 반드시 uv 또는 pipx + 3.13 격리.
2. **전역 설치 부작용**: `graphify install` (Claude)은 `~/.claude/skills/` 전역 설치 → agent-factory 외 다른 프로젝트 Claude Code 세션에도 `/graphify` 노출. Q10에서 명시 결정 필요.
3. **CLAUDE.md 자동 주입**: 설치 중 CLAUDE.md에 섹션 append. agent-factory CLAUDE.md는 엄격 관리 → `git diff` 수동 검토 필수.
4. **Git hook append**: Graphify는 `core.hooksPath` 존중 → `.githooks/post-commit`·`post-checkout` 에 마커 섹션 append. 기존 review-gate와 순서 검토 필요.
5. **소규모 프로젝트 효과 없음**: 6 files 규모는 ~1× (절감 0). 첫 `/graphify .` 전에 벤치마크 모드로 효과 확인 권장.

## 참고

- v3 README (사용자 제공): https://github.com/safishamsi/graphify/blob/v3/README.ko-KR.md
- v4 README (최신): https://github.com/safishamsi/graphify/blob/v4/README.md
- 공식 사이트: https://graphify.net/kr/ (봇 차단 403 — WebFetch 불가)

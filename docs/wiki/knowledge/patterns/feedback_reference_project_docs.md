---
name: 참고 프로젝트 분석 저장 규칙
description: 외부 참고 프로젝트 분석 결과는 docs/참고/ 폴더에 YYYY-MM-DD-제목.md로 저장
type: feedback
originSessionId: f72f7dce-ff07-40fa-91d5-f1ad8fd02816
---
외부 참고(reference) 프로젝트·시스템을 분석할 때는 결과 문서를 `docs/참고/` 폴더에 저장한다.

**Why:** 사용자 지시 (2026-04-24). 참고자료 분석 결과가 AF 자체 설계문서와 `docs/` 직하에 혼재되어 있어 재참조가 어려움. 별도 폴더로 분리해 자산 재활용 가능하게 함.

**How to apply:**
- 외부 시스템/프로젝트 분석(paperclip.ing, Kiro, LangGraph, Deep Agents, 특정 라이브러리 아키텍처 등)이 결과물이면 `docs/참고/YYYY-MM-DD-제목.md` 형식으로 저장
- AF 자체 설계문서는 계속 `docs/features/` 또는 `docs/` 직하에 (기존 규칙 유지)
- 파일명 날짜 규칙은 CLAUDE.md와 동일 — 날짜 없음 불가
- 혼동 방지용: 분석 문서 상단에 "출처 URL + 분석 목적" 명시

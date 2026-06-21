---
generated_at: 2026-06-22T07:19:17+09:00
source_commit: 3c7226c3
sources:
  - "Master_Blueprint.md"
  - "docs/code_review/code-review.md"
  - "NEXT_STEPS.md"
---

# LLM Wiki — Index

> 프로젝트 지식 뷰 (generated view — 원본 수정 금지).

## 페이지 목록

- [[architecture]] — 모듈 구조 + 서브시스템 네비게이션
- [[review_patterns]] — 서브시스템별 코드 리뷰 패턴
- [[open_items]] — 미완료/보류 항목 (best-effort)
- [[source_refs]] — 섹션 ↔ 원본 파일 경로 매핑
- [[blueprint/index]] — Master Blueprint 섹션별 전문
- [[code_review/index]] — Code Review 섹션별 전문
- [[symbols]] — 코드베이스 top-level 심볼 (AST 추출)

## 사용법

Obsidian에서 이 디렉터리를 vault로 열면 `[[...]]` 링크로 탐색 가능.
재생성: `python scripts/build_llm_wiki.py` 또는 `af project wiki <path>`

Source: scripts/build_llm_wiki.py

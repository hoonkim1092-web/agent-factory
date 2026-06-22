---
name: project-resume-agent-factory
description: "이력서(경력기술서) Agent Factory·Stock-Analyzer 항목 작성 현황 — 생성 파일 경로, 스크립트 위치, 다음 논의 사항."
metadata: 
  node_type: memory
  type: project
  originSessionId: 8c67ae43-1fa7-4126-8e8c-93857dd3a323
---

이력서에 Agent Factory 프로젝트 항목 추가 작업 완료 (2026-06-13).

**Why:** 사용자가 Agent Factory를 경력기술서에 추가 요청. 기존 0612 파일 기반으로 신규 항목 삽입.

**How to apply:** 다음 세션에서 이력서 관련 작업 재개 시 아래 파일/스크립트 경로 참조.

## 생성된 파일 (D:\이력서\)

| 파일 | 설명 |
|------|------|
| `김정훈_경력기술서_0613_v3.docx` | **최종본** — Stock-Analyzer+Agent Factory 모두 상세 버전 포함 |
| `af_resume_architecture.png` | Agent Factory 시스템 아키텍처 다이어그램 (180dpi) |
| `af_resume_workflow.png` | 3-Tier 검증 & 자가진화 워크플로우 다이어그램 (180dpi) |
| `base_0612.docx` | 0612 원본을 docx 변환한 베이스 (스크립트 입력) |

## 생성 스크립트 (D:\warkSpaces\agent-factory\scripts\)

| 파일 | 역할 |
|------|------|
| `gen_resume_diagrams.py` | PNG 다이어그램 2종 생성 (`make_architecture()` / `make_workflow()`) |
| `build_resume_docx.py` | docx 생성 — `replace_stock_analyzer()` + `build_af_content()` |

## 글쓰기 패턴 (사용자 선호)
- 각 항목마다 **[배경] → [해결] → 효과** 흐름으로 풀어쓰기
- 요약형 bullet 나열 대신 full sentence로 "왜 만들었나"를 포함
- 전문 용어는 한국어 설명을 괄호로 병기

## 다음 세션 논의 예정
- v3 docx 검토 후 추가 수정 사항 반영
- 포트폴리오 PDF 또는 GitHub 링크 연동 여부
- 기타 이력서 관련 요청

관련: [[project_wiring_parity_gate_design]] [[project_af_codebase_wiki_direction]]

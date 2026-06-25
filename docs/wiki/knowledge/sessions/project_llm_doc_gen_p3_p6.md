---
name: LLM 문서 생성 P3~P6 완료
description: prepare() 3분할 + Clarification UI 파이프라인 완료 (2026-04-24)
type: project
originSessionId: 4471b27b-477c-4cfb-9149-9090719255cc
---
LLM 문서 생성 파이프라인 P3~P6 완료 (커밋 `a12f4493`, 2026-04-24).

**Why:** `(edit required)` 플레이스홀더 없이 실행 가능한 work-item 문서 생성 + 모호한 요청을 Clarification으로 구체화.

**완료된 항목:**
1. `core/project_pipeline.py` — `PreparedBrief` 데이터클래스 추가. `prepare()` → `prepare_brief()` + `prepare_documents()` + 하위호환 `prepare()` 3분할.
2. `core/clarification.py` — `generate_clarification_questions()`, `merge_clarification()`, `should_skip_clarification()`, `auto_apply_defaults()` 완전 구현. `_append_to()` 헬퍼로 non-list 필드 안전 처리.
3. `agent_launcher.py` — `_collect_clarification_answers()` 정적 메서드 + `_run_project_with_approval()`에 Clarification 단계 삽입. enriched brief를 `_write_json()` 원자적 쓰기로 갱신.
4. `af.spec` — `core.clarification` hiddenimports 추가.
5. `tests/test_llm_doc_gen_p3_p6.py` — 23개 테스트 전원 통과.

**Cross-review 수정:**
- `run_structural_gate()` path string 전달 버그 → `project_brief` dict 전달로 수정
- Clarification 후 brief 재저장 비원자적 쓰기 → `_write_json()` 원자적 쓰기

**주의사항:**
- Clarification은 `execution_mode == "approval"` 일 때만 실행 (FSA 모드는 기존 `prepare()` 그대로)
- `/skip` 시 이전에 답한 내용 포함 전체 기본값으로 덮어씀 (의도적 단순화)
- `auto_apply_defaults()`는 현재 FSA 경로에서 미연결 (향후 필요 시 `project_pipeline.prepare()`에 삽입)

**How to apply:** 다음 Clarification 관련 작업 시 `core/clarification.py`와 `agent_launcher.py:_run_project_with_approval()`을 함께 읽을 것.

## 관련
- [[code/symbols]]


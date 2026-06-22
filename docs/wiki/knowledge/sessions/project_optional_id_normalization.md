---
name: optional-id-normalization
description: "safe_id(\"\")=\"skill\" 계약 문제 — optional identifier 전용 헬퍼 필요. P1-C-rv에서 발견, 별도 work-item."
metadata: 
  node_type: memory
  type: project
  originSessionId: baa07b41-74c1-41d0-acc2-1b4b61b25c4f
---

`safe_id()`의 빈입력 계약 문제 — 별도 work-item으로 정식 설계 필요. 2026-05-19 P1-C 재검증(P1-C-rv) 중 발견. **이 메모가 durable 기록** (P1-C-rv WIP stash는 로컬 전용).

## 근본 원인

`core/utils.py:64` `safe_id()` 마지막 줄: `return (t[:60] if t else "skill")`. 빈/None 입력 → `""`가 아니라 `"skill"` 반환. skill-id 생성용 fallback인데, `safe_id`는 task_id·owner_role·dependency key·mailbox key 등 **optional identifier** 정규화에도 광범위 사용(grep 기준 **322회 / 32개 core 파일**). optional id가 비었을 때 `safe_id(x)`가 `"skill"`이 되어, 호출부의 truthy 가드(`if safe_id(x):` / `if target_id:`)가 **false-positive로 통과** → garbage 매칭·상태 오염.

## 확인된 영향 사이트 (2026-05-19 grep 검증)

- `core/project_task_board.py:832,841` `update_project_board_task` — 빈 task_id → `"skill"` truthy → instruction/role fallback **미진입** → `task_key=="skill"` 매칭 → board 상태 갱신 silent fail. **실제 High** (실행 중 태스크가 in_progress로 안 바뀜).
- `core/dynamic_orchestrator.py` `_resolve_task_meta` — 빈 task_id → `"skill"` → `if not target_id` 가드 통과 → 무의미 board 스캔 후 None.
- `core/dynamic_orchestrator.py:186` `_completed_subtask_keys` — `safe_id(item.get("task_id"))` 빈값 → `"skill"`이 completed 키 집합에 들어가 향후 태스크 false-completed 위험.
- `core/agent_runner.py:967` `ctx["task_id"]=safe_id(task_id)` — 빈값 → ctx/trace에 `"skill"` 정체성 오염.
- `core/project_mailbox.py:156` `safe_id(task_id)` — 빈값 → 메시지가 `"skill"` task scope로 영구 저장.
- `core/project_mailbox.py:152` `safe_id(from_role) or "unknown_sender"` — `or` 분기는 **죽은 코드**(safe_id는 falsy 미반환). 계약 오해가 코드베이스에 퍼진 증거.

## 권장 접근 (전역 변경 금지)

`safe_id` 자체를 `""` 반환으로 바꾸는 것은 322회/32파일 blast radius라 **금지**. 대신:
- 신규 헬퍼 `safe_optional_id()` (또는 유사) — 빈/None 입력 시 `""` 반환, 그 외 `safe_id`와 동일.
- optional-id 호출처를 audit해 `safe_id` → `safe_optional_id`로 교체.
- `safe_id`의 `"skill"` fallback은 **skill-id 생성 용도로만** 유지, 불변.
- Tier 3 작업 — `scripts/blast_radius.py` 분석 + 3-Tier 리뷰.

## P1-C-rv 이력

P1-C(`bcc4c223`)의 bypass된 변경을 사용자 지적으로 재검증하다 발견. P1-C-rv 시도(= `_lilith_decide_next`에 보드 task_id 화이트리스트 + `_resolve_task_meta` raw-empty 가드)는 cross-review BLOCK — 한 사이트 고치면 다음 사이트가 나오는 whack-a-mole이라 판단해 철수.
- P1-C-rv WIP 코드는 `git stash` `stash@{0}: P1C-rv-safe_id-wip`에 보존 — **로컬 전용, PC 간 미동기화.** stash 소실돼도 위 "권장 접근"으로 재구성 가능.
- P1-C 본체(`bcc4c223`+`c0c7c0b7`)는 정상 동작·커밋·푸시됨. 본 work-item은 P1-C와 독립.

## 부수 — P1-C 프롬프트 placeholder advisory

`core/dynamic_orchestrator.py` `_lilith_decide_next`의 LLM 프롬프트 JSON 예시 `"task_id"` 값(현재 커밋 상태: `<board task_id, blank if not a board task>`)은 문구만으로 안전 보장 불가 — LLM이 예시를 리터럴 echo하면 무효 task_id가 됨. 코드 레벨 화이트리스트(위 P1-C-rv WIP)가 정답이며 본 work-item에 포함.

[[dogfooding-hygiene-sprint]]

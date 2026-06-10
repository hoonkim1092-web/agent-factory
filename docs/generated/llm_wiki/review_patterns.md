---
generated_at: 2026-06-11T00:34:40+09:00
source_commit: d442a252
sources:
  - "Master_Blueprint.md"
  - "docs/code_review/code-review.md"
  - "NEXT_STEPS.md"
---

# Review Patterns — 서브시스템별 리뷰 패턴

> Source: docs/code_review/code-review.md §2.x
> 관련: [[index]] | [[open_items]] | [[source_refs]]

## 2.1 실행 엔진 (Runtime Engine)

- `run_budget.py`: 글로벌 싱글톤, 에이전트별 분해 없음 → v3 Feature 1로 해결 예정

Source: `docs/code_review/code-review.md:37`

## 2.2 Control Plane (Sidecar 유지보수)

- `control_plane_llm.py:50-56`: `detect_available_cli_providers()`만 호출, `AF_CONTROL_PLANE_PROVIDERS` 환경변수 미지원 → v3에서 연동 필요

Source: `docs/code_review/code-review.md:55`

## 2.3 Provider 레이어

- `session_adapter.py:110`: codex_cli는 `mode="wrapper_bridge"`, `hook_events=()` → native hook 불가, AF EventBus 필요

Source: `docs/code_review/code-review.md:79`

## 2.4 Hook 시스템

- `event_bus.py`: provider 이벤트 → AF 이벤트 매핑 없음 → v3 Phase 8B에서 `on_provider_event()` 추가

Source: `docs/code_review/code-review.md:93`

## 2.5 메모리 시스템

- `facade.py`: 프로세스 전역 singleton → 멀티 프로젝트에서 충돌 가능. Worker 프로세스 격리로 해결 (v3 Phase 8A)

Source: `docs/code_review/code-review.md:113`

## 2.6 ISE (Iterative Self-Enhancement)

- `ise_loop.py`: 완전 dead code. 어디서도 import하지 않음

Source: `docs/code_review/code-review.md:136`

## 2.7 스킬 시스템

- `skill_registry.py`: `ensure_skills_loaded()` — `count()==0` 체크 → `external_scanned` 플래그로 교체. 유지보수 시 신규 외부 스킬 미감지 버그 수정

Source: `docs/code_review/code-review.md:151`

## 2.8 대화/연구 엔진

- `context_window_manager.py`: `should_compact()`, `compact()` 미구현 → v3 Phase 5B에서 추가

Source: `docs/code_review/code-review.md:188`

## 2.9 파이프라인/보드


Source: `docs/code_review/code-review.md:204`

## 2.10 인프라/유틸리티

- `config_paths.py`: 모듈 레벨 상수 → import 시점 고정. Worker 프로세스 격리로 해결 (v3)

Source: `docs/code_review/code-review.md:214`

## 2.11 기타


Source: `docs/code_review/code-review.md:234`

## 2.12 진입점 및 빌드


Source: `docs/code_review/code-review.md:252`

## 3.1 Critical — 크래시 또는 데이터 손실 가능


Source: `docs/code_review/code-review.md:265`

## 3.2 High — 잘못된 동작


Source: `docs/code_review/code-review.md:274`

## 3.3 Medium — 성능/유지보수


Source: `docs/code_review/code-review.md:310`

## 3.4 이미 수정된 버그 (control/ 영역)


Source: `docs/code_review/code-review.md:335`

## 3.5 신규 기능 추가 (2026-04-03)

- **상세**: `trace_*.jsonl` (기존 유지, 변경 없음)

Source: `docs/code_review/code-review.md:348`


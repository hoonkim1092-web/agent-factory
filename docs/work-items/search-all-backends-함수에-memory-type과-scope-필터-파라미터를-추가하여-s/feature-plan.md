# Feature Plan

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `search-all-backends-함수에-memory-type과-scope-필터-파라미터를-추가하여-s` |
| owner | Backend Dev |
| status | pending |
| last_updated | 2026-04-26 |

---

## Background

Agent Factory의 memory facade는 여러 백엔드를 통합 조회하는 `search_all_backends()`를 제공한다. 그러나 동일 facade 내의 `search_semantic()`에는 이미 `memory_type`/`scope` 슬라이스 필터가 존재하는 반면, `search_all_backends()`에는 해당 파라미터가 없어 두 메서드 간 API 계약이 불일치한다.

기존 설계문서(`2026-04-24-unified-memory-facade-rag-extension.md §6.4`)는 `search_all_backends()` 호출부를 "변경 없음 — project_id 필터 없는 무차별 검색 유지"로 고정했다. 파라미터 추가는 하위 호환 방식(기본값 `None`)으로 적용되므로 해당 원칙과 충돌하지 않는다.

`MemoryScope.GLOBAL/LOCAL` 구분 로직은 v3 설계문서(`2026-04-24-unified-memory-facade-rag-extension-v3.md`)에 `scope = MemoryScope.GLOBAL if node.project_id is None else MemoryScope.LOCAL` 패턴으로 이미 정의되어 있어 구현 참고가 가능하다.

---

## Problem Statement

`search_all_backends()`가 `memory_type`/`scope` 필터를 지원하지 않음으로 인해 세 가지 문제가 발생한다.

1. **API 불일치**: `search_semantic()`과 시그니처가 달라 호출자가 두 메서드를 일관성 없이 사용해야 한다.
2. **책임 역전**: 호출자가 전수 결과를 받은 후 직접 필터링해야 하므로 중복 필터링 코드가 발생한다.
3. **테스트 불가**: 필터 동작을 단위 테스트로 검증할 진입점이 없다.

---

## Goals

1. `search_all_backends()` 시그니처에 `memory_type: MemoryType | None = None`, `scope: MemoryScope | None = None` 파라미터를 추가한다.
2. 필터 적용 로직을 `search_semantic()`과 동일한 방식으로 구현하여 동작 일관성을 확보한다.
3. `tests/test_phase10_memory_foundation.py`에 회귀 테스트 2건(memory_type 필터 1건, scope 필터 1건)을 추가하여 필터 동작을 자동으로 검증한다.
4. 기존 호출부를 무파괴(하위 호환) 상태로 유지한다.

---

## Non-Goals

- `search_all_backends()` 이외 다른 메서드의 시그니처 변경
- 새로운 `MemoryType` 또는 `MemoryScope` 값 추가
- 백엔드 스토리지 스키마 변경
- `project_id` 필터 추가 (기존 설계문서에서 `search_all_backends`는 project_id 무차별 검색 유지로 명시)

---

## Scope

### 수정 대상 파일

| 파일 | 변경 내용 |
|------|-----------|
| `core/memory_system/facade.py` | `search_all_backends()` 시그니처 확장 + 필터 로직 추가 |
| `tests/test_phase10_memory_foundation.py` | 회귀 테스트 2건 추가 |
| `Master_Blueprint.md` | §3 메서드 시그니처 + §12 변경 이력 업데이트 |

### 수정 대상 외 파일

- `search_all_backends()` 기존 호출부: 파라미터 미전달 시 `None` 기본값으로 동작하므로 변경 불필요

### 모듈별 구현 역할

| 모듈 ID | 담당 역할 | 산출물 |
|---------|-----------|--------|
| `backend_dev_module_1` | Backend Dev | `search_all_backends()` 시그니처 + scope/memory_type 파라미터 추가 |
| `backend_dev_module_2` | Backend Dev | `search_semantic()`과 동일한 필터 적용 로직 이식 (공통 헬퍼 추출 검토 포함) |
| `qa_engineer_module_3` | QA Engineer | `memory_type` 필터 회귀 테스트 1건 |
| `qa_engineer_module_4` | QA Engineer | `scope` 필터 회귀 테스트 1건 |

---

## Stakeholders

| 역할 | 이름/팀 | 관심 사항 |
|------|---------|-----------|
| Backend Dev | 구현 담당 | 시그니처 하위 호환, 필터 로직 중복 최소화 |
| QA Engineer | 검증 담당 | 회귀 테스트 커버리지, 픽스처 재사용 |
| 호출자 (미래 개발자) | facade 사용처 | 일관된 API 계약, 필터링 책임 소재 명확화 |

---

## Success Metrics

| 지표 | 기준 |
|------|------|
| 하위 호환성 | 기존 `search_all_backends()` 호출부 코드 무변경 상태에서 기존 동작 유지 |
| 필터 정확도 | `memory_type=X` 전달 시 반환 노드 전부 `memory_type == X` |
| 필터 정확도 | `scope=Y` 전달 시 반환 노드 전부 `scope == Y` |
| 필터 통과 | `memory_type=None, scope=None` 시 기존과 동일한 전체 결과 반환 |
| 회귀 테스트 | `pytest tests/test_phase10_memory_foundation.py` 신규 2건 포함 전 케이스 통과 |
| Review-Gate | af-test-runner → af-critic → af-cross-review 3단계 완주 후 커밋 |
| Blueprint 동기화 | `Master_Blueprint.md §3 + §12` 동일 커밋 업데이트 |

---

## Risks and Assumptions

### 리스크

| ID | 설명 | 심각도 | 완화 방안 |
|----|------|--------|-----------|
| R1 | `None` 처리 누락 시 필터 없는 기존 호출 결과 변경 위험 | 높음 | 필터 분기를 `if memory_type is not None` 형태로 명시적 guard 처리 |
| R2 | `search_semantic()`의 필터 구현이 백엔드별로 위임되어 있을 경우 `all_backends` 경로에 동일 로직 재현 시 중복 발생 | 중간 | 공통 헬퍼 함수(`_apply_filters()`) 추출 검토; 중복 2곳 이상 확인 시 즉시 추출 |
| R3 | `MemoryType`/`MemoryScope` Enum 값이 백엔드 스토리지 필드와 정확히 매핑되지 않아 필터 효과 없음(False Positive) | 중간 | 회귀 테스트에서 mock backend 노드의 실제 필드값과 enum 비교 일치 여부 검증 |

### 가정

- `MemoryType`·`MemoryScope` Enum은 `core/memory_system/facade.py` 내 `search_semantic()` 임포트 경로와 동일하게 이미 접근 가능한 상태이다.
- `tests/test_phase10_memory_foundation.py`의 기존 mock backend 픽스처와 `MemoryNode` 샘플이 재사용 가능하다.
- 기존 `search_all_backends()` 호출부는 위치 인자 또는 키워드 인자 없이 `query`만 전달하므로 기본값 `None` 추가로 충분하다.

---

## Evidence

| 출처 | 내용 |
|------|------|
| `docs/features/2026-04-24-unified-memory-facade-rag-extension.md §6.4` | `search_all_backends()` 호출부 변경 없음 명시 — 파라미터 추가는 하위 호환이므로 원칙 충돌 없음 |
| `docs/features/2026-04-24-unified-memory-facade-rag-extension-v3.md` | `scope = MemoryScope.GLOBAL if node.project_id is None else MemoryScope.LOCAL` 패턴 — scope 필터 비교 기준 |
| `docs/archive/code_review/memory_system_deep_review_2026-03-19.md` | `core/memory_system/facade.py` 중대 문제 2건 기록 — 기존 품질 이슈 인지 필요 |
| 현재 코드 | `facade.py`의 `search_semantic()` 시그니처와 필터 조건문을 직접 읽어 동일 패턴 추출 후 이식 |

---

## References

- `core/memory_system/facade.py` — `search_semantic()` 구현 (패턴 참조)
- `tests/test_phase10_memory_foundation.py` — 회귀 테스트 추가 대상 파일
- `Master_Blueprint.md §3` — facade 메서드 시그니처 명세
- `Master_Blueprint.md §12` — 변경 이력
- `docs/features/2026-04-24-unified-memory-facade-rag-extension.md` — 기존 설계 원칙
- `docs/features/2026-04-24-unified-memory-facade-rag-extension-v3.md` — scope 판별 로직

---

## Approval Request

본 계획은 아래 사항을 전제로 구현 착수를 요청한다.

1. **하위 호환 보장**: `memory_type=None, scope=None` 기본값으로 기존 호출부 동작 무변경
2. **필터 로직 단일화**: `search_semantic()`과 동일한 방식 또는 공통 헬퍼로 추출 — 중복 금지
3. **테스트 격리**: 신규 테스트 2건은 `tests/test_phase10_memory_foundation.py` 기존 파일에만 추가, 신규 파일 생성 금지
4. **Review-Gate 준수**: af-test-runner(tier 1) → af-critic(tier 2) → af-cross-review(tier 3) 3단계 완주 후 커밋
5. **Blueprint 동기화**: `Master_Blueprint.md §3 + §12` 동일 커밋 업데이트 필수

위 조건을 충족하는 구현이 완료되면 merge 준비 완료로 간주한다.

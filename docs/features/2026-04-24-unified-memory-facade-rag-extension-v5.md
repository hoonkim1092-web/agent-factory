# UnifiedMemoryFacade — RAG 대응 확장 설계 v5 (폐기)

> ⛔ **폐기됨 (2026-04-24)** — 사용자 결정: Q1=(a) → Q1=(b)로 변경. RAG 기능 정확성 확보가 drift 수용보다 우선.
> 최신: [`2026-04-24-unified-memory-facade-rag-extension-v6.md`](./2026-04-24-unified-memory-facade-rag-extension-v6.md)
>
> ---
>
> 날짜: 2026-04-24
> 상태: 폐기 (v6로 대체)
> 선행: v1~v4 (모두 폐기). v4에서 BLOCK 2 + 중요 드리프트 2건 추가 발견
> 형식: v3/v4 delta 문서 — 아래 변경만 최종 적용
> v4: [`2026-04-24-unified-memory-facade-rag-extension-v4.md`](./2026-04-24-unified-memory-facade-rag-extension-v4.md)
> v3: [`2026-04-24-unified-memory-facade-rag-extension-v3.md`](./2026-04-24-unified-memory-facade-rag-extension-v3.md)

---

## 0. v5 변경 요약

v4 교차검증(af-critic v4 BLOCK 2건 + af-cross-review v4 HOLD 2건)을 반영.

**사용자 결정 반영**:
- Q1 → **(a) 의도된 drift 수용**: `router.py:180` 미수정, 회귀 테스트로 의도 명시
- Q2 → **(b) Phase B에 cortex similarity 추출 포함**: Phase C는 CortexClient 파라미터화 + write만

---

## 1. v5 변경 내용

### 1.1 X1 해결 — `asyncio.gather` 표기 통일

v4 §1.2의 코드 스니펫과 §2 Phase D 체크리스트 표기 일관화:

```python
# 통일 버전 (v5 최종)
project_results, global_results = await asyncio.gather(
    asyncio.gather(*project_tasks, return_exceptions=True),
    asyncio.gather(*global_tasks, return_exceptions=True),
    return_exceptions=True,  # ★ 외부 gather에도 명시 (안쪽 gather 자체 crash 방어)
)
```

**규칙**: inner·outer 양쪽 모두 `return_exceptions=True` 명시. v4 §2 체크리스트도 같은 표기로 통일.

### 1.2 X2 해결 — `KnowledgeGraphAdapter` project_id 정규화 대칭화

v5 Phase A에 추가:

**문제**: 현재 `write` 경로는 `project_id=record.project_id or None`, read 경로(`_node_to_record`)는 `project_id=node.project_id or ""`로 비대칭 정규화. 빈 문자열 레코드에 대해 양 경로가 다른 값을 생성 → scope 분류 오류 가능.

**v5 수정 방향**:
```python
# write 경로 (core/memory_system/adapters/knowledge_graph.py)
node = KnowledgeNode(
    ...
    project_id=record.project_id or None,  # 기존 유지 — "" → None 정규화
)

# read 경로 (_node_to_record)
# 변경 전: project_id=node.project_id or ""
# 변경 후: project_id=node.project_id or ""  (유지)
# 단, scope 판정은 내부 node.project_id로 수행 (빈 문자열 / None 구분 없이 falsy 취급)
scope = MemoryScope.GLOBAL if not node.project_id else MemoryScope.PROJECT
```

**핵심**: scope 결정은 `not node.project_id` (falsy 체크)로 일관화. `is None`이 아니라 **truthy/falsy**로 평가. 이로써 `None`과 `""` 둘 다 GLOBAL로 분류.

### 1.3 X3 해결 — Q1=(a) 의도된 drift 수용

`router.py:180`의 `_recall_graph`는 **수정하지 않는다**. 대신 이 두 경로의 의미를 설계 문서에 명시:

| 경로 | scope 부여 | 용도 |
|------|----------|------|
| `KnowledgeGraphAdapter._node_to_record` (Phase A 수정됨) | PROJECT or GLOBAL | **영속 메모리 레이어** — facade 검색에서 사용 |
| `router._recall_graph` (v5에서 수정 안 함) | `MemoryScope.LOCAL` 하드코딩 유지 | **임시 BFS 세션 결과** — router 쿼리 응답용 임시 객체 |

**설계 선언**: `router._recall_graph`가 반환하는 `MemoryRecord`는 **이벤트성 객체**로, 영속 저장소의 scope와 별개. 이 drift는 의도된 것이며 두 용도의 분리를 보존한다.

**하위 호환 표** (v3 §6에 추가):

| 항목 | 영향 |
|------|------|
| `router._recall_graph` 반환 객체 scope | **LOCAL 유지 (의도)** — BFS 세션 임시값. `search_mixed_scope`에서 PROJECT/GLOBAL 분기로 집계되지 않음 |

### 1.4 X4 해결 — Q2=(b) Phase B/C 재조정

**v4 Phase 계획 수정**:

| Phase | v4 | v5 |
|-------|----|----|
| B | adapter tuple 래핑 (cortex_vector는 `(rec, 0.0)` 기본값) + facade tuple 처리 + 기존 테스트 | adapter tuple 래핑 + **cortex_vector는 `float(row.get("similarity", 0.0))` 실제 추출** + facade tuple 처리 + 기존 테스트 |
| C | cortex_vector similarity 추출 + CortexClient 파라미터화 + adapter write project_id | **CortexClient `recall`·`save_memory` 파라미터화** + `cortex_vector.write()` project_id 전달 |

**효과**: Phase B 커밋 직후에도 cortex_vector가 실제 similarity 반환 → rank_by_relevance 왜곡 없음.

**Phase B 라인 규모**: 약 **550 라인** (v4 500 + similarity 추출 코드 50)  
**Phase C 라인 규모**: 약 **100 라인** (CortexClient 시그니처 + adapter write)

### 1.5 Phase B 회귀 테스트 (X3 drift 명시)

`tests/test_memory_facade_rag_extension.py`에 신규 테스트 추가:

```python
def test_router_recall_graph_keeps_local_scope_intentionally():
    """router._recall_graph가 반환하는 MemoryRecord는 KG adapter 경로와 달리
    MemoryScope.LOCAL을 유지한다. 두 경로는 서로 다른 용도이며 이 drift는 의도된 것이다.
    (v5 X3 의사결정 — Q1=a)
    """
    from core.memory_system.router import MemoryRouter
    # ... router 초기화
    results = await router._recall_graph("query", limit=5)
    for record in results:
        assert record.scope == MemoryScope.LOCAL, (
            "router._recall_graph는 임시 BFS 세션 결과이므로 LOCAL 유지가 의도. "
            "adapter 경로와의 scope drift는 설계 문서 v5 X3에 명시됨."
        )
```

### 1.6 X2 회귀 테스트 (정규화 대칭)

```python
def test_knowledge_graph_empty_string_project_id_maps_to_global():
    """KnowledgeNode.project_id가 '' 또는 None인 경우 모두 scope=GLOBAL로 분류.
    write-read 정규화 비대칭 버그 방어 (v5 X2)."""
    adapter = KnowledgeGraphAdapter(...)
    
    # 빈 문자열 project_id 노드
    node_empty = KnowledgeNode(project_id="", ...)
    record_empty = adapter._node_to_record(node_empty)
    assert record_empty.scope == MemoryScope.GLOBAL
    
    # None project_id 노드
    node_none = KnowledgeNode(project_id=None, ...)
    record_none = adapter._node_to_record(node_none)
    assert record_none.scope == MemoryScope.GLOBAL
    
    # 실제 project_id
    node_real = KnowledgeNode(project_id="proj-A", ...)
    record_real = adapter._node_to_record(node_real)
    assert record_real.scope == MemoryScope.PROJECT
```

### 1.7 timing 기반 병렬 테스트 deterministic 패턴 (af-cross-review v4 SUGGEST S1)

v4 `test_search_mixed_scope_runs_project_and_global_in_parallel`를 타이밍 대신 event 동기화 기반으로 변경:

```python
async def test_search_mixed_scope_runs_project_and_global_in_parallel():
    """타이밍 대신 asyncio.Event로 병렬 실행 검증 (flaky 방지)."""
    started_project = asyncio.Event()
    started_global = asyncio.Event()
    
    class MockAdapter(MemoryBackendAdapter):
        async def search(self, query, *, limit=10, project_id=None):
            if project_id is not None:
                started_project.set()
                # global 분기가 시작될 때까지 대기
                await asyncio.wait_for(started_global.wait(), timeout=1.0)
            else:
                started_global.set()
                await asyncio.wait_for(started_project.wait(), timeout=1.0)
            return [(MemoryRecord(...), 0.5)]
    
    # 두 분기가 서로의 시작을 확인할 수 있다는 것은 병렬로 schedule됐다는 의미
    ...
    # timeout 걸리지 않고 결과 반환되면 병렬 실행 확인
```

### 1.8 테스트 ellipsis 구체화 (af-cross-review v4 SUGGEST S3)

v4 §1.4의 테스트 본문 `...` 제거, 각 테스트마다 최소 1~2줄 assertion 명시.

---

## 2. 최종 Phase 계획 (v5 확정)

| Phase | 내용 | 라인 규모 | 의존성 |
|-------|------|---------|-------|
| **A** | `MemoryScope.PROJECT` + cortex_vector scope try/except + knowledge_graph `_node_to_record` **falsy 기반 scope 결정** + 신규 테스트 4건 | ~60 | — |
| **B** | adapter interface tuple + 8 adapter tuple 래핑 (cortex_vector는 **실제 similarity 추출**) + facade `search_semantic`/`search_all_backends` tuple 처리 + `_deduplicate_with_scores` + `rank_by_relevance` semantic_scores 전달 + 기존 테스트 12건 수정 + 신규 테스트 8건 | ~550 | A |
| **C** | `CortexClient.recall`/`save_memory` 파라미터화 + `cortex_vector.write()` project_id 전달 + 신규 테스트 5건 | ~100 | A, B |
| **D** | `search_mixed_scope` (overfetch + min_score + timeout + 병렬 gather + PROJECT 분기 GLOBAL 제외 post-filter) + 신규 테스트 9건 | ~150 | A, B, C |

---

## 3. v5 신규 변경 파일 (v4 대비 추가)

| 파일 | 변경 |
|------|-----|
| `core/memory_system/adapters/knowledge_graph.py` | `_node_to_record` scope 결정을 `not node.project_id` falsy 체크로 변경 |
| `core/memory_system/adapters/cortex_vector.py` | Phase B에 similarity 추출 포함 (기존 Phase C 예정분 이동) |
| `tests/test_memory_facade_rag_extension.py` | `test_router_recall_graph_keeps_local_scope_intentionally`, `test_knowledge_graph_empty_string_project_id_maps_to_global` 추가 |

**변경 없는 파일**: `core/memory_system/router.py` (Q1=a 선택으로 수정 안 함)

---

## 4. 최종 체크리스트 (누적 17건)

### v1~v4 누적 BLOCK 15건
- v1 B1~B4 (4): ✅ 해결
- v2 N1~N5 (5): ✅ 해결
- v3 B1 (cortex tuple Phase 귀속): ✅ 해결 (v5 Phase B/C 재조정)
- v3 B2 (apply 경로): ✅ 해결 (v4 §1.3)
- v3 B3 (score 0.0 + rank_by_relevance): ✅ 해결 (v4 §1.1)
- v3 B4 (GLOBAL 이중 계산): ✅ 해결 (v4 §1.2 post-filter + v5 X2 falsy 대칭)

### v4 신규 BLOCK 2건
- X1 (gather 표기 불일치): ✅ 해결 (v5 §1.1 양쪽 return_exceptions=True)
- X2 (project_id `""` vs `None`): ✅ 해결 (v5 §1.2 falsy 기반 scope 결정 + 테스트)

### v4 cross-review HOLD 2건
- X3 (router.py:180 drift): ✅ 해결 (v5 §1.3 의도 drift 선언 + 회귀 테스트)
- X4 (Phase B 단독 cortex rank 왜곡): ✅ 해결 (v5 §1.4 Phase B 확장)

### v4 SUGGEST 3건
- S1 (timing 테스트 flaky): ✅ 반영 (v5 §1.7 event 동기화)
- S2 (cortex Phase B 포함): ✅ 반영 (X4와 동일)
- S3 (테스트 ellipsis): ✅ 반영 (v5 §1.8)

**17건 전부 해결.**

---

## 5. 구현 착수 조건

v5가 교차검증에서 BLOCK 0 확인되면 **Phase A부터 즉시 착수**.

각 Phase 커밋 후 `pytest tests/` 회귀 확인. BLOCK 발견 시 다음 Phase 중단.

---

## 6. v4 대비 변경 요약

| 이슈 | v4 | v5 |
|------|----|----|
| `asyncio.gather` return_exceptions 표기 | inner만 | **inner + outer 양쪽** |
| `KnowledgeGraphAdapter` project_id 정규화 | write `or None` / read `or ""` 비대칭 | **falsy 기반 scope 결정으로 통합** |
| `router.py:180` scope 하드코딩 | 미분석 | **의도 drift로 선언 + 회귀 테스트** (Q1=a) |
| Phase B 후 cortex score | 모두 0.0 (rank 왜곡) | **실제 similarity 추출** (Q2=b) |
| 병렬 테스트 | 타이밍 기반 (flaky 위험) | **asyncio.Event 동기화** |
| 테스트 본문 | `...` ellipsis | **1~2줄 assertion 명시** |

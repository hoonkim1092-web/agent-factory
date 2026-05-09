# UnifiedMemoryFacade — RAG 대응 확장 설계 v6 (폐기)

> ⛔ **폐기됨 (2026-04-24)** — 테스트 스니펫 API 오류 3건 (critic + cross-review 공통).
> 최신: [`2026-04-24-unified-memory-facade-rag-extension-v7.md`](./2026-04-24-unified-memory-facade-rag-extension-v7.md)
>
> ---
>
> 날짜: 2026-04-24
> 상태: 폐기 (v7로 대체)
> 선행: v1~v5 (모두 폐기). v5 교차검증에서 Q1=(a)→(b) 결정 변경 + 인라인 수정 4건
> 형식: v3/v4/v5 delta 문서 — 아래 변경만 최종 적용
> v5 base: [`v5`](./2026-04-24-unified-memory-facade-rag-extension-v5.md)
> v4 base: [`v4`](./2026-04-24-unified-memory-facade-rag-extension-v4.md)
> v3 base: [`v3`](./2026-04-24-unified-memory-facade-rag-extension-v3.md)

---

## 0. v6 변경 요약

v5 교차검증(af-critic BLOCK 2 + af-cross-review HOLD 1 + SUGGEST 3) 반영 + **사용자 결정 변경**: Q1=(a) → **Q1=(b)**.

| 변경 | v5 | v6 |
|------|----|----|
| **Q1 결정** | (a) 의도 drift 수용 | **(b) router.py:180도 PROJECT/GLOBAL로 수정** |
| dedup winner scope 비결정성 (af-critic WARN 6) | 잔존 | **자동 해소** (두 경로가 같은 scope) |
| RAG 검색에서 BFS 노드 포함 | 누락 (drift 부작용) | **포함** (일관성 확보) |
| §1.3 drift 선언 | 유지 | **삭제** |
| §1.5 회귀 테스트 | "LOCAL 유지" 검증 | **"adapter와 일관된 scope" 검증**으로 방향 반대 |
| B2 async def 오타 | 있음 | **수정** |
| §1.5 테스트 ellipsis | 있음 | **구체화** |
| §1.1 outer return_exceptions 주석 | 잘못된 설명 | **정정 or 제거** |
| §1.7 parallel 테스트 검증 로직 | event.wait timeout 의존 | **event.is_set() 명시 assertion** |

---

## 1. v6 변경 내용

### 1.1 Q1 = (b) — `router.py:180` 1줄 수정으로 scope 일관성 확보

**변경 대상**: `core/memory_system/router.py:180`

```python
# 기존 (v1~v5):
scope=MemoryScope.LOCAL,

# v6 변경:
scope=MemoryScope.GLOBAL if node.project_id is None or node.project_id == "" else MemoryScope.PROJECT,
```

**근거**:
- `_recall_graph`는 외부 caller 0건 확인 (grep 결과)
- adapter 경로(`KnowledgeGraphAdapter._node_to_record`)의 scope와 **완벽히 일관** 유지
- `search_mixed_scope` PROJECT 분기에서 BFS 노드 포함 → **RAG 검색 정확성** 확보
- dedup winner의 scope가 경로와 무관하게 같아짐 → **비결정성 제거**
- `node.project_id is None or == ""`의 falsy 체크는 v5 §1.2(X2 해결)와 동일 규칙

**Phase 귀속**: Phase A에 포함 (knowledge_graph `_node_to_record` scope 매핑과 같은 커밋)

### 1.2 §1.3 drift 선언 섹션 **삭제**

v5 §1.3 "X3 해결 — Q1=(a) 의도된 drift 수용" 섹션 전체 삭제. **drift 자체가 존재하지 않음** (v6에서 router도 함께 수정하므로).

하위 호환 표에서도 다음 행 **삭제**:

```
| router._recall_graph 반환 객체 scope | LOCAL 유지 (의도) |  ← 이 행 삭제
```

### 1.3 §1.5 회귀 테스트 방향 반대로

**v5 회귀 테스트 (삭제)**:
```python
def test_router_recall_graph_keeps_local_scope_intentionally():  # 삭제
```

**v6 신규 회귀 테스트** (같은 위치에 교체):

```python
import pytest
from core.memory_system.models import KnowledgeNode, MemoryScope, NodeType
from core.memory_system.router import MemoryRouter

@pytest.mark.asyncio
async def test_router_recall_graph_assigns_consistent_scope_with_adapter():
    """router._recall_graph가 반환하는 MemoryRecord는 KG adapter 경로와 동일한
    scope 규칙을 따른다 (v6 Q1=b).

    project_id 있음 → PROJECT
    project_id None/"" → GLOBAL
    """
    router = MemoryRouter(...)
    # KG에 세 노드 삽입: project_id 있음 / None / 빈 문자열
    node_proj = KnowledgeNode(node_type=NodeType.PROBLEM, label="proj_node",
                              project_id="proj-A", description="needle_A")
    node_global = KnowledgeNode(node_type=NodeType.PROBLEM, label="global_node",
                                project_id=None, description="needle_G")
    node_empty = KnowledgeNode(node_type=NodeType.PROBLEM, label="empty_node",
                               project_id="", description="needle_E")
    router._graph.add_node(node_proj)
    router._graph.add_node(node_global)
    router._graph.add_node(node_empty)

    results = await router._recall_graph("needle", limit=10)

    scope_by_label = {r.metadata.get("label"): r.scope for r in results}
    assert scope_by_label["proj_node"] == MemoryScope.PROJECT
    assert scope_by_label["global_node"] == MemoryScope.GLOBAL
    assert scope_by_label["empty_node"] == MemoryScope.GLOBAL  # "" → GLOBAL
```

### 1.4 B2 — `async def` 타이핑 오류 수정

v5 §1.6의 `test_knowledge_graph_empty_string_project_id_maps_to_global`도 검토 — `_node_to_record`는 동기 메서드이므로 `def`로 OK (await 미사용). 오타 없음 확인.

v5 §1.5 테스트가 async 필요했던 이유: `router._recall_graph`가 async. v6 §1.3 신규 테스트에 **`@pytest.mark.asyncio` + `async def`** 명시하여 해결.

### 1.5 §1.1 outer `return_exceptions=True` 주석 재작성

v5 §1.1 코드 블록의 `# ★ 외부 gather에도 명시 (안쪽 gather 자체 crash 방어)` 주석이 잘못됨 (inner가 이미 `return_exceptions=True`면 outer로 exception 전파 불가). v6 수정:

```python
project_results, global_results = await asyncio.gather(
    asyncio.gather(*project_tasks, return_exceptions=True),
    asyncio.gather(*global_tasks, return_exceptions=True),
    # outer gather는 inner의 예외가 아닌 gather 객체 생성 실패 같은
    # 드문 환경 예외만 대비. 실질 방어는 inner의 return_exceptions=True에서.
)
```

outer의 `return_exceptions=True` 제거해도 동작 동일. v6는 **제거**를 선택 (과잉 방어는 가독성 저하):

```python
project_results, global_results = await asyncio.gather(
    asyncio.gather(*project_tasks, return_exceptions=True),
    asyncio.gather(*global_tasks, return_exceptions=True),
)
```

### 1.6 §1.7 병렬 테스트 검증 로직 명시 (H-v5-1)

v5 §1.7의 event 기반 테스트에 **양쪽 event가 모두 set되었는지** 명시 assertion 추가:

```python
@pytest.mark.asyncio
async def test_search_mixed_scope_runs_project_and_global_in_parallel():
    """타이밍 대신 asyncio.Event로 병렬 실행 검증 (flaky 방지)."""
    started_project = asyncio.Event()
    started_global = asyncio.Event()

    class MockAdapter(MemoryBackendAdapter):
        backend_name = "mock"
        async def search(self, query, *, limit=10, project_id=None):
            if project_id is not None:
                started_project.set()
                # global 분기가 시작되기를 기다림 (병렬 schedule 증명)
                await asyncio.wait_for(started_global.wait(), timeout=0.5)
            else:
                started_global.set()
                await asyncio.wait_for(started_project.wait(), timeout=0.5)
            return [(MemoryRecord(content=f"hit_{project_id}"), 0.5)]

    facade = UnifiedMemoryFacade(project_id="p")
    facade.register_adapter(MockAdapter())
    await facade.initialise()

    results = await facade.search_mixed_scope("q", limit=5, include_global=True)

    # 병렬 실행의 필수 조건: 양쪽 event 모두 set되어야 함
    assert started_project.is_set(), "PROJECT 분기가 실행되지 않음"
    assert started_global.is_set(), "GLOBAL 분기가 실행되지 않음"
    # 두 hit 모두 포함되어야 함 (dedupe 없이)
    contents = {r.content for r in results}
    assert "hit_p" in contents
    assert "hit_None" in contents
```

**핵심**: `event.is_set()` 어서션 + timeout=0.5로 flaky 방지 (timeout 발생 시 asyncio.wait_for가 즉시 raise → 테스트 실패로 명시).

### 1.7 §1.5/§1.6 ellipsis 구체화 (S-v5-1)

v6 §1.3의 회귀 테스트는 완전 body 제공 (facade 초기화 생략 안 함). v5 §1.6의 테스트도 이미 body 있음 — OK.

### 1.8 af-critic WARN 6 자동 해소 명시

v5에서 남아있던 "Q1=a drift로 `_deduplicate_with_scores` winner scope 비결정성" 이슈는 **v6 Q1=(b)로 자동 해결**. 설계 문서에 명시:

> router BFS 경로와 adapter 경로가 같은 KG 노드에 동일 scope를 부여하므로, dedup winner의 scope는 어느 경로가 먼저 arrive하든 **동일**. 비결정성 자체가 존재하지 않음.

---

## 2. 최종 Phase 계획 (v6 확정)

| Phase | 내용 | 변경 |
|-------|------|-----|
| **A** | v5 Phase A + **`router.py:180` 1줄 수정** | +1 파일, +1 줄 |
| **B** | v5 Phase B 그대로 | 변경 없음 |
| **C** | v5 Phase C 그대로 | 변경 없음 |
| **D** | v5 Phase D + §1.6 테스트 검증 로직 수정 | 테스트 로직만 |

---

## 3. 변경 파일 (v6 추가)

| 파일 | v5 | v6 |
|------|----|----|
| `core/memory_system/router.py` | 수정 없음 | **1줄 수정** (§1.1) |
| `tests/test_memory_facade_rag_extension.py` | v5 §1.5 LOCAL 검증 테스트 | **방향 반대로 교체** (§1.3) + parallel 테스트 완전 body (§1.6) |
| v5 §1.3 drift 선언 | 있음 | **제거** |
| v5 §1.1 outer return_exceptions | 있음 | **제거** (과잉 방어) |

---

## 4. 최종 누적 체크리스트 (18건)

### v1 B1~B4 (4): ✅
### v2 N1~N5 (5): ✅
### v3 B1~B4 (4): ✅
### v4 X1~X4 (4): ✅
### v5 critic B1 (cortex project isolation): ✅ "기존 제약의 연속, Phase C에서 해결" — 재분류 (cross-review 검증으로 확인)
### v5 critic B2 (async def 오타): ✅ v6 §1.3에서 수정
### v5 SUGGEST S-v5-1 (ellipsis): ✅ v6 §1.3/§1.6 완전 body
### v5 SUGGEST S-v5-3 (outer return_exceptions 주석 오류): ✅ v6 §1.5에서 제거
### v5 HOLD H-v5-1 (parallel 검증 flaky): ✅ v6 §1.6 `event.is_set()` 명시
### v5 WARN 6 (dedup winner 비결정성): ✅ **Q1=(b) 선택으로 자동 해소** (v6 §1.1)

**총 18건 전부 해결.**

---

## 5. v6에서 새로 생긴 이슈?

Q1=(b) 선택으로:
- 추가 기능적 리스크: 없음 (`_recall_graph` 외부 caller 없음 확인됨)
- 추가 테스트 부담: 1건 (v6 §1.3의 scope 일관성 테스트)
- 추가 코드 복잡도: router.py:180 조건 표현식 1줄

**신규 BLOCK 없음 예상**.

---

## 6. 구현 착수 조건

v6 교차검증 BLOCK 0 확인 → Phase A부터 즉시 착수.

### Phase A 체크리스트 (v6 확정)
- [ ] `core/memory_system/models.py`: `MemoryScope.PROJECT` 추가
- [ ] `core/memory_system/adapters/cortex_vector.py`: `_cortex_to_record` scope try/except + LOCAL fallback
- [ ] `core/memory_system/adapters/knowledge_graph.py`: `_node_to_record`의 scope 결정을 `not node.project_id` falsy 체크로
- [ ] **`core/memory_system/router.py:180`: `scope=MemoryScope.LOCAL` → `scope=MemoryScope.GLOBAL if ... else MemoryScope.PROJECT` (1줄)** ← v6 신규
- [ ] 신규 테스트 5건:
  - `test_memory_scope_project_value`
  - `test_cortex_vector_unknown_scope_falls_back_local`
  - `test_knowledge_graph_project_id_maps_to_project_scope`
  - `test_knowledge_graph_empty_string_project_id_maps_to_global`
  - **`test_router_recall_graph_assigns_consistent_scope_with_adapter`** ← v6 신규

### Phase B 체크리스트 (v5와 동일)
- v5 §2 참조

### Phase C 체크리스트 (v5와 동일)
- v5 §2 참조

### Phase D 체크리스트 (v5 + v6 §1.6 반영)
- v5 §2 참조 + parallel 테스트를 v6 §1.6 로직으로 구현

---

## 7. v5 대비 변경 요약 (v6)

| 이슈 | v5 | v6 |
|------|----|----|
| router.py:180 | 수정 안 함 (drift 수용) | **1줄 수정** (scope 일관화) |
| dedup winner scope 비결정성 | WARN 잔존 | **자동 해소** |
| RAG 검색에서 BFS 노드 | 누락 | **포함** |
| 회귀 테스트 | LOCAL 유지 검증 | 일관된 scope 검증 |
| async def 오타 | 있음 | 수정 |
| parallel 테스트 검증 | event.wait timeout만 | `is_set()` 명시 |
| outer gather return_exceptions | 잘못된 주석 | 제거 |

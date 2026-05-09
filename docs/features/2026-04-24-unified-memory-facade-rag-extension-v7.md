# UnifiedMemoryFacade — RAG 대응 확장 설계 v7 (최종)

> 날짜: 2026-04-24
> 상태: 설계 v7 (교차검증 대기 — 통과 시 Phase A 즉시 착수)
> 선행: v1~v6 (모두 폐기)
> 형식: v6 delta — 테스트 스니펫 API 교정만
> v6 base: [`v6`](./2026-04-24-unified-memory-facade-rag-extension-v6.md)

---

## 0. v7 변경 요약

v6 교차검증(critic + cross-review 공통 BLOCK 3건)은 **모두 설계 문서 내 테스트 스니펫의 API 오류**였다. 프로덕션 설계(Q1=b, router.py 1줄, Phase A~D) 자체는 검증 통과.

v7는 **테스트 스니펫만 실제 API에 맞게 교정**한다.

| v6 BLOCK | v7 해결 |
|---------|--------|
| B1: `router._graph.add_node` 존재 안 함 | facade + `KnowledgeGraphAdapter` 패턴으로 교체 |
| B2: `MockAdapter.backend_name` 추상 프로퍼티 누락 | `backend_name = "mock"` 추가 |
| B3: `keyword_similarity` 통과 미보장 + ellipsis 잔존 | description을 단일 토큰 "needle"로 포함 + facade 초기화 완전 body |

## 1. v6 §1.3 회귀 테스트 완전 교체

v6 §1.3의 테스트를 아래로 교체 (v7 §1):

```python
import pytest
from core.memory_system.adapters.knowledge_graph import KnowledgeGraphAdapter
from core.memory_system.facade import UnifiedMemoryFacade
from core.memory_system.models import KnowledgeNode, MemoryScope, NodeType
from core.memory_system.router import MemoryRouter


@pytest.mark.asyncio
async def test_router_recall_graph_assigns_consistent_scope_with_adapter(tmp_path):
    """router._recall_graph가 반환하는 MemoryRecord는 KG adapter 경로와 동일한
    scope 규칙을 따른다 (v7 Q1=b).

    project_id 있음 → PROJECT
    project_id None/"" → GLOBAL
    """
    # Facade + KnowledgeGraphAdapter 초기화
    kg_adapter = KnowledgeGraphAdapter(workspace=str(tmp_path))
    facade = UnifiedMemoryFacade(project_id="test-proj")
    facade.register_adapter(kg_adapter)
    await facade.initialise()

    # 세 노드 삽입: project_id 값이 다른 3종.
    # description에 "needle"을 단일 토큰으로 포함 (keyword_similarity > 0.15 보장)
    node_proj = KnowledgeNode(
        node_type=NodeType.PROBLEM,
        label="proj_node",
        description="needle for proj case",
        project_id="proj-A",
    )
    node_global = KnowledgeNode(
        node_type=NodeType.PROBLEM,
        label="global_node",
        description="needle for global case",
        project_id=None,
    )
    node_empty = KnowledgeNode(
        node_type=NodeType.PROBLEM,
        label="empty_node",
        description="needle for empty case",
        project_id="",
    )
    kg_adapter.add_node(node_proj)
    kg_adapter.add_node(node_global)
    kg_adapter.add_node(node_empty)

    # router 생성 + BFS 쿼리 실행
    router = MemoryRouter(facade)
    results = await router._recall_graph("needle", limit=10)

    assert len(results) >= 3, "BFS가 세 노드 모두 seed로 채택해야 함"
    scope_by_label = {r.metadata.get("label"): r.scope for r in results}
    assert scope_by_label["proj_node"] == MemoryScope.PROJECT
    assert scope_by_label["global_node"] == MemoryScope.GLOBAL
    assert scope_by_label["empty_node"] == MemoryScope.GLOBAL  # "" → GLOBAL (falsy)
```

**변경 포인트**:
- `router._graph.add_node` **삭제** → `kg_adapter.add_node` 호출
- `facade.register_adapter + await facade.initialise()` **추가**
- `description`을 `"needle for X case"` 형태로 작성 → `keyword_similarity("needle", "proj_node needle for proj case")`의 token intersection = {"needle"} → 정상적으로 threshold 통과
- `MemoryRouter(facade)` **완전 body** (ellipsis 제거)
- `tmp_path` fixture 사용 (storage_dir 인자)

**구현 시 확인 사항**:
- `KnowledgeGraphAdapter.__init__(storage_dir=...)` 실제 시그니처와 일치하는지 — 다르면 적절한 인자로 교체
- `kg_adapter.add_node(...)` 메서드 존재 확인 — 없으면 `kg_adapter._nodes[node.node_id] = node` 직접 삽입

## 2. v6 §1.6 MockAdapter 완전 교체

v6 §1.6의 parallel 테스트를 아래로 교체:

```python
import asyncio
import pytest
from core.memory_system.adapters.base import MemoryBackendAdapter
from core.memory_system.facade import UnifiedMemoryFacade
from core.memory_system.models import MemoryRecord


class _MockParallelAdapter(MemoryBackendAdapter):
    """병렬 실행 검증용 — asyncio.Event로 동기화."""

    def __init__(self, started_project: asyncio.Event, started_global: asyncio.Event):
        self._started_project = started_project
        self._started_global = started_global

    @property
    def backend_name(self) -> str:
        return "mock_parallel"

    async def read(self, record_id):
        return None

    async def write(self, record):
        return True

    async def update(self, record):
        return True

    async def delete(self, record_id):
        return True

    async def search(self, query, *, limit=10, project_id=None):
        # Phase B 이후 계약: list[tuple[MemoryRecord, float]]
        if project_id is not None:
            self._started_project.set()
            # global 분기가 시작되기를 기다림 (병렬 schedule 증명)
            await asyncio.wait_for(self._started_global.wait(), timeout=0.5)
            return [(MemoryRecord(content="hit_project", scope=MemoryScope.PROJECT), 0.5)]
        else:
            self._started_global.set()
            await asyncio.wait_for(self._started_project.wait(), timeout=0.5)
            return [(MemoryRecord(content="hit_global", scope=MemoryScope.GLOBAL), 0.5)]

    async def list_recent(self, *, limit=10, project_id=None):
        return []


@pytest.mark.asyncio
async def test_search_mixed_scope_runs_project_and_global_in_parallel():
    """asyncio.Event 기반 병렬 실행 검증 (flaky 방지)."""
    started_project = asyncio.Event()
    started_global = asyncio.Event()
    adapter = _MockParallelAdapter(started_project, started_global)

    facade = UnifiedMemoryFacade(project_id="p")
    facade.register_adapter(adapter)
    await facade.initialise()

    results = await facade.search_mixed_scope("q", limit=5, include_global=True)

    # 병렬 실행의 필수 조건: 양쪽 event 모두 set됨
    assert started_project.is_set(), "PROJECT 분기가 실행되지 않음"
    assert started_global.is_set(), "GLOBAL 분기가 실행되지 않음"
    # 두 hit 모두 포함 (PROJECT/GLOBAL scope 각각)
    contents = {r.content for r in results}
    assert "hit_project" in contents
    assert "hit_global" in contents
```

**변경 포인트**:
- `backend_name` property 구현 **추가** (abstract 만족)
- 모든 abstract 메서드(read/write/update/delete/list_recent) 구현 추가
- `search()` 반환을 `list[tuple[MemoryRecord, float]]`로 Phase B 계약 준수
- `scope=MemoryScope.PROJECT/GLOBAL` 명시하여 `search_mixed_scope` post-filter 검증 가능

## 3. v6 §1.1의 조건식 일관화 (선택 사항 — SUGGEST 수준)

v6 §1.1의 router.py 수정:
```python
# v6 안:
scope=MemoryScope.GLOBAL if node.project_id is None or node.project_id == "" else MemoryScope.PROJECT,
```

→ v7는 **adapter와 같은 falsy 표현으로 통일** (가독성 ↑):
```python
# v7 최종:
scope=MemoryScope.GLOBAL if not node.project_id else MemoryScope.PROJECT,
```

**이유**: `knowledge_graph._node_to_record`가 `not node.project_id`를 사용하므로 표기 일관화. 결과는 동등(`str | None` 타입에서는 `None`/`""`가 falsy).

## 4. v6 §4 체크리스트 정정

v6는 "18건 전부 해결"이라 주장했으나, v5 SUGGEST 목록은 3건이 아니라 2건(S-v5-1, S-v5-3)이었다. v7는 실제 카운트로 정정:

- v1 B1~B4 (4)
- v2 N1~N5 (5)
- v3 B1~B4 (4)
- v4 X1~X4 (4)
- v5 critic B1 재분류 + B2 수정 (2)
- v5 SUGGEST S-v5-1, S-v5-3 (2)
- v5 HOLD H-v5-1 (1)
- v5 WARN 6 자동 해소 (1)
- **누적 23건** → 전부 해결

**cross-review 추가 지적 (v6에서 미처 반영 안 됨)**:
- `knowledge_graph.search()` line 139 필터 `if project_id and node.project_id and ...` — 기존 행동과 동일하므로 **regression 아님**. v7는 이를 **알려진 기존 제약**(v3 §9 "알려진 한계")에 추가로 기록:

> **한계 6 (v7 추가)**: `KnowledgeGraphAdapter.search()`의 project_id 필터는 `""`과 `None`을 둘 다 "필터 스킵"으로 처리하여, 빈 문자열 project_id 노드가 모든 쿼리에서 반환된다. 이는 기존 코드 동작이며, v7 변경 대상 아님. 향후 필요 시 별도 리팩토링.

## 5. Phase A 체크리스트 최종 (v7 확정)

| # | 항목 | 파일 | 라인 |
|---|-----|------|-----|
| 1 | `MemoryScope.PROJECT` enum 추가 | `core/memory_system/models.py` | +1 |
| 2 | `_cortex_to_record` scope try/except + LOCAL fallback | `core/memory_system/adapters/cortex_vector.py` | +3 |
| 3 | `_node_to_record` scope를 `not node.project_id` falsy 기반으로 | `core/memory_system/adapters/knowledge_graph.py` | +1 |
| 4 | `_recall_graph`의 MemoryRecord scope를 동일 falsy 기반으로 (Q1=b) | `core/memory_system/router.py:180` | +1 |
| 5 | 신규 테스트 5건 | `tests/test_memory_facade_rag_extension.py` | +120 |

**신규 테스트**:
- `test_memory_scope_project_value`
- `test_cortex_vector_unknown_scope_falls_back_local`
- `test_knowledge_graph_project_id_maps_to_project_scope`
- `test_knowledge_graph_empty_string_project_id_maps_to_global` (v5 §1.6)
- `test_router_recall_graph_assigns_consistent_scope_with_adapter` (v7 §1)

## 6. v6 대비 변경 요약 (v7)

| 항목 | v6 | v7 |
|------|----|----|
| router 회귀 테스트 | `router._graph.add_node` (존재 안 함) | `kg_adapter.add_node` + facade 초기화 |
| parallel 테스트 MockAdapter | abstract method 누락 | **모든 abstract method 구현** |
| `keyword_similarity` 통과 | 토큰 매칭 미보장 | **"needle"을 단일 토큰으로 포함** |
| 테스트 ellipsis | `router = MemoryRouter(...)` 잔존 | **완전 body** |
| router.py 조건식 | `is None or == ""` | `not node.project_id` (adapter와 통일) |
| v6 체크리스트 카운트 | "18건" (오집계) | **23건** (정확한 누적 카운트) |
| `knowledge_graph.search()` line 139 필터 | 미언급 | **기존 제약 명시** (§9 한계 6) |

## 7. 구현 착수 조건

v7이 교차검증 BLOCK 0 확인되면 **Phase A 즉시 착수**.

이번 v7는 **테스트 스니펫 교정**만 포함하므로 BLOCK 재발 가능성 낮음. 혹시 v7에서도 BLOCK이 나온다면 실제 구현 중에 자연 수정하는 편이 효율적.

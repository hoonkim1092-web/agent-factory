# UnifiedMemoryFacade — RAG 대응 확장 설계 v3 (폐기)

> ⛔ **폐기됨 (2026-04-24)** — af-critic BLOCK 4건 추가 발견.
> 최신 설계: [`2026-04-24-unified-memory-facade-rag-extension-v4.md`](./2026-04-24-unified-memory-facade-rag-extension-v4.md) (v3 delta 형식)
>
> ---
>
> 날짜: 2026-04-24
> 상태: 폐기 (v4로 대체)
> 선행: v1 (폐기), v2 (폐기) — v2에서 BLOCK 5건 추가 발견
> 목적: 후속 영속 RAG 설계의 전제 인프라 구축

## 1. v2에서 추가 발견된 5 BLOCK (v3 해결 대상)

| BLOCK | v2 문제 | v3 해결 |
|-------|--------|--------|
| **N1** | `_cortex_to_record` 반환형을 tuple로 바꿨으나 `read()`/`_search_by_hash()` 계약(단일 `MemoryRecord`) 위반 | `_cortex_to_record`는 **기존 시그니처 유지** (`MemoryRecord` 반환). tuple은 `search()` 내부에서만 조립 |
| **N2** | `search_all_backends()` 변경 누락 → P1 커밋 즉시 크래시 | 변경 파일 목록 + 구현에 **`search_all_backends` 포함** |
| **N3** | Phase 분할에서 P1 단독 커밋 시 facade 크래시 | **P1 → P2 → P3을 원자 단위로 재정의**, 테스트까지 포함 |
| **N4** | `save_memory()`도 `PROJECT_ID` 하드코딩이나 v2는 `recall()`만 파라미터화 | `save_memory()`와 `recall()` **동시 파라미터화** |
| **N5** | `search_mixed_scope` adapter 호출에 `asyncio.wait_for` 없음 → 블록 위험 | 모든 `asyncio.gather` 대상을 `asyncio.wait_for`로 래핑 |

**참고**: v1 BLOCK 4건(similarity 버려짐·PROJECT_ID 하드코딩·_score 영속 누수·over-fetch 부재)은 v2에서 이미 해결되었으며 v3도 동일한 접근 유지.

---

## 2. 핵심 아키텍처 (v3)

### 2.1 Adapter interface — tuple 반환 (B3 + N1 해결)

`core/memory_system/adapters/base.py`:

```python
@abstractmethod
async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    project_id: str | None = None,
) -> list[tuple[MemoryRecord, float]]:
    """Returns (record, score) tuples. Score ∈ [0.0, 1.0].

    Score is EPHEMERAL and must NOT be stored on the record itself.
    Implementations unsure of similarity return 0.0.
    """
```

**N1 교훈 반영** — `_cortex_to_record`는 **`MemoryRecord`만 반환** (시그니처 보존). tuple은 `search()` 내부 루프에서 조립:

```python
# core/memory_system/adapters/cortex_vector.py
def _cortex_to_record(self, row: dict) -> MemoryRecord:
    """계약 유지 — MemoryRecord 반환. similarity 추출은 호출자 책임."""
    meta = row.get("metadata", {}) or {}
    try:
        scope = MemoryScope(meta.get("scope", "local"))
    except ValueError:
        scope = MemoryScope.LOCAL  # mixed-version compat (v2 SUGGEST T7)
    return MemoryRecord(...)

async def search(self, query, *, limit=10, project_id=None):
    effective_pid = project_id if project_id is not None else self._project_id
    resp = self._client.recall(query, limit=limit, project_id=effective_pid)
    if not resp.get("ok"):
        return []
    results: list[tuple[MemoryRecord, float]] = []
    for row in resp.get("results", []):
        rec = self._cortex_to_record(row)
        score = float(row.get("similarity", 0.0))  # RPC 전용 필드, PostgREST 경로 호출은 없음
        results.append((rec, score))
    return results

async def read(self, record_id: str) -> MemoryRecord | None:
    # 기존 그대로 — _cortex_to_record가 MemoryRecord 반환이라 변경 불필요
    ...

async def _search_by_hash(self, content_hash: str) -> MemoryRecord | None:
    # 기존 그대로
    ...
```

**기타 7개 adapter (core_memory, ast_hub, continuity, knowledge_graph, sync_compyne, trace_log, InMemoryAdapter 테스트 하네스)**:

```python
async def search(self, query, *, limit=10, project_id=None):
    results = ... (기존 로직)
    return [(r, 0.0) for r in results]  # 기계적 tuple 래핑
```

### 2.2 Facade tuple 처리 — `search_semantic` + `search_all_backends` 동시 (N2 해결)

**`search_semantic`** (facade.py:164~218):

```python
async def search_semantic(self, query, *, limit=10, memory_type=None, scope=None):
    self._ensure_initialised()
    timeout = get_config().timeouts.search_timeout

    tasks = [
        asyncio.wait_for(
            adapter.search(query, limit=limit, project_id=self.project_id),
            timeout=timeout,
        )
        for adapter in self._adapters.values()
    ]
    all_tuples: list[tuple[MemoryRecord, float]] = []
    score_map: dict[str, float] = {}

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, BaseException):
            # 로깅 기존과 동일
            continue
        for rec, sc in res:
            all_tuples.append((rec, sc))
            if sc > score_map.get(rec.record_id, 0.0):
                score_map[rec.record_id] = sc

    # type/scope filter
    if memory_type:
        all_tuples = [(r, s) for r, s in all_tuples if r.memory_type == memory_type]
    if scope:
        all_tuples = [(r, s) for r, s in all_tuples if r.scope == scope]

    # TTL 만료 제거
    records_only = [r for r, _ in all_tuples]
    decay_mgr = MemoryDecayManager()
    active, expired = decay_mgr.collect_expired(records_only)
    # expired 로깅 기존과 동일

    # dedupe — score_map과 연계
    deduped = _deduplicate_with_scores(active, score_map)

    # rank
    scored = decay_mgr.rank_by_relevance(deduped, semantic_scores=score_map)
    return [rec for rec, _ in scored[:limit]]
```

**`search_all_backends`** (facade.py:239~271, **v3 신규 추가**):

```python
async def search_all_backends(self, query: str, *, limit: int = 10):
    self._ensure_initialised()
    timeout = get_config().timeouts.search_timeout

    tasks = [
        asyncio.wait_for(
            adapter.search(query, limit=limit, project_id=None),
            timeout=timeout,
        )
        for adapter in self._adapters.values()
    ]
    all_records: list[MemoryRecord] = []
    score_map: dict[str, float] = {}

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, BaseException):
            continue
        for rec, sc in res:
            all_records.append(rec)
            if sc > score_map.get(rec.record_id, 0.0):
                score_map[rec.record_id] = sc

    deduped = _deduplicate_with_scores(all_records, score_map)
    scored = MemoryDecayManager().rank_by_relevance(deduped, semantic_scores=score_map)
    return [rec for rec, _ in scored[:limit]]
```

**신규 헬퍼 `_deduplicate_with_scores`** (facade.py module-level):

```python
def _deduplicate_with_scores(
    records: list[MemoryRecord],
    score_map: dict[str, float],
) -> list[MemoryRecord]:
    """Deduplicate by content_hash. Winner selection priority:
       1. Higher semantic score (from score_map)
       2. Higher access_count (기존 `_deduplicate` 호환)
    """
    seen: dict[str, MemoryRecord] = {}
    for r in records:
        key = r.content_hash if r.content_hash else r.record_id
        if key not in seen:
            seen[key] = r
            continue
        existing = seen[key]
        r_score = score_map.get(r.record_id, 0.0)
        existing_score = score_map.get(existing.record_id, 0.0)
        if r_score > existing_score:
            seen[key] = r
        elif r_score == existing_score and r.access_count > existing.access_count:
            seen[key] = r
    return list(seen.values())
```

**기존 `_deduplicate` 유지** — facade 내부 다른 경로(없음)와 테스트 fixture 호환. Cross-review S4가 지적한 dedupe 기준 차이 해소.

### 2.3 `search_mixed_scope` — timeout + over-fetch (B4 + N5 해결)

```python
async def search_mixed_scope(
    self,
    query: str,
    *,
    limit: int = 10,
    memory_type: MemoryType | None = None,
    include_global: bool = True,
    project_id_override: str | None = None,
    min_score: float = 0.0,
    overfetch_multiplier: int = 3,
) -> list[MemoryRecord]:
    if limit <= 0:
        return []
    self._ensure_initialised()
    timeout = get_config().timeouts.search_timeout
    effective_pid = project_id_override or self.project_id
    overfetch = limit * max(1, overfetch_multiplier)

    # PROJECT scope 쿼리 — wait_for로 timeout 보장
    project_tasks = [
        asyncio.wait_for(
            adapter.search(query, limit=overfetch, project_id=effective_pid),
            timeout=timeout,
        )
        for adapter in self._adapters.values()
    ]
    global_tasks = []
    if include_global:
        global_tasks = [
            asyncio.wait_for(
                adapter.search(query, limit=overfetch, project_id=None),
                timeout=timeout,
            )
            for adapter in self._adapters.values()
        ]

    all_tuples: list[tuple[MemoryRecord, float]] = []
    for res in await asyncio.gather(*project_tasks, return_exceptions=True):
        if not isinstance(res, BaseException):
            all_tuples.extend(res)
    for res in await asyncio.gather(*global_tasks, return_exceptions=True):
        if not isinstance(res, BaseException):
            # GLOBAL scope만 post-filter
            all_tuples.extend((r, s) for r, s in res if r.scope == MemoryScope.GLOBAL)

    # memory_type filter
    if memory_type:
        all_tuples = [(r, s) for r, s in all_tuples if r.memory_type == memory_type]

    # min_score filter
    if min_score > 0.0:
        all_tuples = [(r, s) for r, s in all_tuples if s >= min_score]

    # dedupe — content_hash 기준, score 우선
    by_hash: dict[str, tuple[MemoryRecord, float]] = {}
    for r, s in all_tuples:
        key = r.content_hash or r.record_id
        if key not in by_hash or by_hash[key][1] < s:
            by_hash[key] = (r, s)
    records_only = [r for r, _ in by_hash.values()]
    score_map = {r.record_id: s for r, s in by_hash.values()}

    # rank
    scored = MemoryDecayManager().rank_by_relevance(records_only, semantic_scores=score_map)
    return [rec for rec, _ in scored[:limit]]
```

### 2.4 CortexClient — `recall` + `save_memory` 동시 파라미터화 (B2 + N4 해결)

**`skills/core/cortex.py`**:

```python
_DEFAULT_PROJECT_ID = os.path.basename(os.getcwd())  # 하위 호환 fallback

class CortexClient:
    def recall(
        self,
        query: str,
        *,
        threshold: float = 0.5,
        limit: int = 10,
        project_id: str | None = None,
    ) -> dict:
        effective_pid = project_id or _DEFAULT_PROJECT_ID
        filter_obj = {"project_id": effective_pid}
        ...

    def save_memory(
        self,
        content: str,
        metadata: dict | None = None,
        *,
        project_id: str | None = None,
    ) -> dict:
        metadata = dict(metadata or {})
        effective_pid = project_id or metadata.get("project_id") or _DEFAULT_PROJECT_ID
        # metadata의 project_id 덮어쓰기 대신 effective_pid로 통합
        payload = {
            "content": content,
            "metadata": {**metadata, "project_id": effective_pid},
            ...
        }
        ...
```

**`CortexVectorAdapter.write()`** 수정:

```python
async def write(self, record: MemoryRecord) -> bool:
    effective_pid = record.project_id or self._project_id
    meta = {**record.metadata, "record_id": record.record_id, ...}
    resp = self._client.save_memory(record.content, meta, project_id=effective_pid)
    return resp.get("ok", False)
```

### 2.5 `MemoryScope.PROJECT` + knowledge_graph 매핑 (SUGGEST S5 해결)

**`core/memory_system/models.py`**:

```python
class MemoryScope(str, Enum):
    LOCAL = "local"
    PROJECT = "project"   # 신규
    GLOBAL = "global"
    SESSION = "session"
```

**`core/memory_system/adapters/knowledge_graph.py:206` 변경**:

```python
# 기존:
# scope=MemoryScope.GLOBAL if node.project_id is None else MemoryScope.LOCAL,

# v3:
scope=MemoryScope.GLOBAL if node.project_id is None else MemoryScope.PROJECT,
```

**의미 변경 주의**: 기존 저장된 knowledge graph 노드는 `scope="local"` (MemoryScope.LOCAL)로 DB에 있음. v3 이후 신규 노드는 `scope="project"`로 저장. **기존 저장 레코드는 마이그레이션 스크립트 불필요** — search에서 LOCAL 노드도 함께 검색하려면 `search_mixed_scope(include_global=True)`가 **`LOCAL`도 포함**하도록 filter 완화 고려해야 하나, 보수적으로 유지: `search_mixed_scope`는 `PROJECT` + `GLOBAL`만. LOCAL은 기존 `search_semantic`으로.

Cross-review S5 권고: `docs/` 내 "scope 의미 변화" 주석 추가 — **v3의 `KnowledgeGraphAdapter`는 신규 노드에 PROJECT scope 부여. 기존 LOCAL 노드는 `search_mixed_scope`의 PROJECT 분기에 노출되지 않으므로, 필요 시 별도 마이그레이션 경로 추가**.

### 2.6 실측 adapter 수 정정 (SUGGEST S1)

`core/agent_runner.py:1015~1046`에서 실제 등록되는 adapter는 **7개**: core_memory, knowledge_graph, ast_hub, continuity, trace_log, cortex_vector, sync_compyne.

- `search_mixed_scope` 최대 쿼리: **3 (overfetch) × 2 (PROJECT + GLOBAL) × 7 (adapter) = 42x**
- 기존 v2의 "48x" 는 오기. 본 문서 §8 KPI도 42x 기준

---

## 3. 변경 파일 목록 (v3 완전)

| 파일 | 변경 |
|------|-----|
| `core/memory_system/models.py` | `MemoryScope.PROJECT` 추가 |
| `core/memory_system/adapters/base.py` | `search` 반환 타입 → `list[tuple[MemoryRecord, float]]` |
| `core/memory_system/adapters/cortex_vector.py` | `search()`가 tuple 반환 (similarity 추출) + scope try/except + write는 `project_id` 명시 전달 |
| `core/memory_system/adapters/core_memory.py` | `search()` tuple 래핑 (+3줄) |
| `core/memory_system/adapters/ast_hub.py` | 동일 |
| `core/memory_system/adapters/continuity.py` | 동일 |
| `core/memory_system/adapters/knowledge_graph.py` | 동일 + `_node_to_record`에서 project_id 있으면 `MemoryScope.PROJECT` |
| `core/memory_system/adapters/sync_compyne.py` | 동일 |
| `core/memory_system/adapters/trace_log.py` | 동일 |
| `core/memory_system/facade.py` | `search_semantic` tuple 처리 + `search_all_backends` tuple 처리 + `_deduplicate_with_scores` 헬퍼 신규 + `search_mixed_scope` 신규 (asyncio.wait_for 래핑) |
| `skills/core/cortex.py` | `recall`·`save_memory`에 `project_id` 파라미터 + `_DEFAULT_PROJECT_ID` 리네임 |
| `tests/test_phase10_memory_foundation.py` | InMemoryAdapter tuple 래핑 + 관련 assertion 수정 (7건) |
| `tests/test_phase11_adapters.py` | adapter 테스트 tuple 형태 assertion 업데이트 (4건) |
| `tests/test_phase13_knowledge_graph.py` | 동일 (1건) |
| `tests/test_memory_facade_rag_extension.py` | **신규** — 신규 기능 단위 테스트 |

---

## 4. Phase 계획 (v3 — 원자 커밋 단위)

**Cross-review N3 반영** — P1만 커밋 시 facade 크래시 위험. 따라서 Phase 분할을 재정의:

| Phase | 내용 | 원자 단위 | 독립 커밋 |
|-------|------|---------|-----------|
| **A** | `MemoryScope.PROJECT` + 전 adapter scope try/except + `KnowledgeGraphAdapter` scope 매핑 | 단일 | ✅ |
| **B** | Adapter interface tuple 변경 (base + 7 adapter + InMemoryAdapter) + facade `search_semantic`/`search_all_backends` tuple 처리 + `_deduplicate_with_scores` + 기존 테스트 수정 | **원자 커밋** (쪼개면 크래시) | ✅ |
| **C** | `CortexClient.recall`/`save_memory` + adapter write project_id 전달 + cortex_vector `search()`가 similarity 실제 추출 | 단일 | ✅ (A+B 필요) |
| **D** | `search_mixed_scope` 신규 + overfetch + min_score + timeout 래핑 + `tests/test_memory_facade_rag_extension.py` | 단일 | ✅ (A+B+C 필요) |

Phase **B**가 가장 큰 단일 커밋. 여기서 tuple interface 변경은 모든 호출부(facade 두 메서드 + 테스트)를 **동시 수정**하는 것이 유일하게 안전.

---

## 5. 테스트 전략

`tests/test_memory_facade_rag_extension.py` 신규:

```python
# Phase A
def test_memory_scope_project_value(): ...
def test_cortex_vector_unknown_scope_falls_back_local(): ...
def test_knowledge_graph_project_id_maps_to_project_scope(): ...

# Phase B
def test_adapter_search_returns_tuples(): ...
def test_score_not_leaked_to_record_metadata(): ...
async def test_search_semantic_uses_tuple_scores(): ...
async def test_search_all_backends_uses_tuple_scores(): ...
async def test_deduplicate_with_scores_prefers_higher_score(): ...

# Phase C
async def test_cortex_recall_accepts_project_id_override(): ...
async def test_cortex_save_memory_accepts_project_id(): ...
async def test_cortex_write_passes_effective_project_id(): ...
async def test_cortex_search_reads_similarity_from_rpc(): ...

# Phase D
async def test_search_mixed_scope_combines_project_and_global(): ...
async def test_search_mixed_scope_applies_memory_type_post_filter(): ...
async def test_search_mixed_scope_applies_min_score_filter(): ...
async def test_search_mixed_scope_overfetch_respects_limit(): ...
async def test_search_mixed_scope_wraps_adapter_calls_with_wait_for(): ...
async def test_search_mixed_scope_handles_adapter_timeout_gracefully(): ...
async def test_search_mixed_scope_limit_zero_returns_empty(): ...

# 회귀 방지
async def test_existing_search_semantic_returns_memory_records(): ...
async def test_existing_search_all_backends_returns_memory_records(): ...
```

**기존 테스트 수정 패턴** — `results[0].content` → `results[0][0].content` (tuple unpack):

```python
# Before (test_phase11_adapters.py:188):
# results = await adapter.search("query", limit=5)
# assert results[0].content == "..."

# After:
# results = await adapter.search("query", limit=5)
# assert results[0][0].content == "..."  # tuple[MemoryRecord, float]
# assert results[0][1] == 0.0  # 추가 가능 (CoreMemoryAdapter의 경우)
```

수정 범위: test_phase10/11/13 합쳐 **최대 12개 assertion 업데이트**.

---

## 6. 하위 호환

| 항목 | 영향 | 비고 |
|------|------|------|
| `MemoryScope.LOCAL` 기존 레코드 | 없음 | 마이그레이션 불필요 |
| `facade.search_semantic()` 외부 호출부 | 없음 | 반환 타입 `list[MemoryRecord]` 유지 |
| `facade.search_all_backends()` 외부 호출부 | 없음 | 반환 타입 유지 (tuple은 내부만) |
| `adapter.search()` 외부 호출 | 없음 | cross-review T4 확인 — facade 외 caller 0 |
| 기존 `_deduplicate()` | 유지 | 새 `_deduplicate_with_scores`와 병존. 기존 호출부(없으면 제거 가능) 미변경 |
| `CortexClient.recall/save_memory` 기존 호출 | 없음 | keyword-only `project_id` 추가. 기본값 `None`로 기존 동작 |
| 구버전 AF가 `scope="project"` 레코드 읽기 | 보호됨 | Phase A의 try/except로 LOCAL fallback |
| `KnowledgeGraphAdapter` 기존 LOCAL 노드 | 유지 (자연스러운 drift) | 마이그레이션 스크립트는 별도 필요 시 |

---

## 7. Blast Radius

| 영향 | 수준 |
|------|------|
| `memory_system/models.py` | Low (enum 1줄) |
| `memory_system/adapters/` 8개 | Medium (interface 변경) |
| `memory_system/facade.py` | High (3개 메서드 수정 + 1 헬퍼 신규) |
| `skills/core/cortex.py` | Low (시그니처 확장) |
| `tests/` 3개 파일 | Medium (12개 assertion + 신규 테스트) |
| 기존 외부 호출부 | **None** |
| 성능 (search_mixed_scope) | P95 ≈ 800~1000ms (42x 쿼리) |
| 후속 RAG 설계 | Enabler (v1 BLOCK 4 + v2 BLOCK 5 모두 해제) |

---

## 8. KPI

| 지표 | 측정 | 목표 |
|------|------|------|
| 기존 테스트 통과율 | `pytest tests/test_memory_*` | 100% (회귀 없음) |
| 신규 테스트 통과율 | `pytest tests/test_memory_facade_rag_extension.py` | 100% |
| `_score` metadata 부재 | 자동 단위 테스트 | 통과 |
| `search_mixed_scope` P95 | 실측 (overfetch 3, 7 adapter) | < 1000ms |
| `search_mixed_scope` timeout 발생 시 부분 결과 반환 | 단위 테스트 | 통과 |

---

## 9. 알려진 한계 (v3도 해결 안 함)

1. **`cortex.recall`이 동기 `urllib`** — event loop blocking. v3 scope 밖 (async HTTP 별도 리팩토링)
2. **`core_memory` adapter substring 매칭** — semantic 기여 0. embedding 기반 교체는 별도 설계
3. **`KnowledgeGraphAdapter` 기존 LOCAL 노드 마이그레이션** — 필요 시 별도 스크립트. 자동 마이그레이션 안 함
4. **projects/minesweeper/agents/\*/tools/cortex.py 복제본** — v3는 core의 `skills/core/cortex.py`만 수정. 복제본은 자체 관리

---

## 10. 체크리스트

- [ ] 설계 교차검증 v3 (af-critic + af-cross-review 병렬, BLOCK 0 확인)
- [ ] Phase A: `MemoryScope.PROJECT` + 전 adapter scope try/except + KnowledgeGraphAdapter 매핑
- [ ] Phase B: adapter tuple + facade `search_semantic`/`search_all_backends` + `_deduplicate_with_scores` + 기존 테스트 수정 (**원자 커밋**)
- [ ] Phase C: `CortexClient` `recall`·`save_memory` 파라미터화 + `cortex_vector` similarity 실제 추출
- [ ] Phase D: `search_mixed_scope` + timeout + overfetch + 신규 테스트
- [ ] `docs/features/2026-04-24-persistent-rag-system.md` v3 전제로 재작성
- [ ] `Master_Blueprint.md` §3 memory_system 업데이트
- [ ] code-review.md 업데이트
- [ ] v1, v2 문서 상단 `⛔ 폐기` 배너 확인

---

## 11. v2 대비 변경 요약

| 이슈 | v2 | v3 |
|------|----|----|
| `_cortex_to_record` 반환형 | tuple (read/_search_by_hash 위반) | `MemoryRecord` 유지, search 내부에서 tuple 조립 |
| `search_all_backends` 변경 | 미포함 | 포함 |
| Phase 분할 | P1 단독 커밋 크래시 | Phase B 원자 커밋으로 재정의 |
| `save_memory` project_id | 미언급 | 파라미터화 |
| `asyncio.wait_for` 래핑 | search_mixed_scope 누락 | 전체 적용 |
| adapter 실측 수 | 8 (오기) | 7 (실측) |
| 테스트 파일 변경 | 미언급 | test_phase10/11/13 명시 |
| `KnowledgeGraphAdapter` scope 매핑 | 미언급 | `PROJECT` 적용 |
| dedupe 기준 차이 | 미명시 | `_deduplicate_with_scores` 신규로 통합 |

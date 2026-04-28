# UnifiedMemoryFacade — RAG 대응 확장 설계 v2 (폐기)

> ⛔ **폐기됨 (2026-04-24)** — af-critic BLOCK 3건 + af-cross-review BLOCK 3건으로 추가 수정 필요.
> 최신 설계: [`2026-04-24-unified-memory-facade-rag-extension-v3.md`](./2026-04-24-unified-memory-facade-rag-extension-v3.md)
>
> ---
>
> 날짜: 2026-04-24
> 상태: 폐기 (v3로 대체)
> 선행: v1 (폐기) — af-critic BLOCK 4 + af-cross-review BLOCK 2 + SUGGEST 5건
> 목적: RAG 인프라 전제 수선. 후속 영속 RAG 설계의 선행 작업

## 1. v1에서 무엇이 틀렸나 (교차검증 발견)

v1 설계는 "metadata에 `_score` 한 줄 추가"로 끝내려 했으나 **4개 BLOCK + 5 SUGGEST**가 나왔다:

| BLOCK | 실제 문제 |
|-------|---------|
| **B1** | `CortexVectorAdapter._cortex_to_record()`가 RPC 응답의 **top-level `similarity` 필드를 읽지 않고 버림**. "이미 score 보유" 전제 허위 |
| **B2** | `CortexClient.recall()`이 `os.getcwd()` import 시점 `PROJECT_ID`로 하드코딩 → adapter `project_id` 파라미터가 DB 쿼리에 전달 안 됨 |
| **B3** | `metadata["_score"]`가 `adapter.write()` 경로에서 **DB에 영속화** → 이후 stale score가 재랭킹 오염 |
| **B4** | `search_mixed_scope`의 `memory_type`/`min_score` 필터가 **post-filter**인데 over-fetch 전략 부재 → `limit` 의미 붕괴 |

v2는 이를 근본적으로 해결한다.

## 2. 설계 목표 (v2)

1. **점수는 레코드 밖으로** — adapter는 `(record, score)` tuple 반환. score가 `MemoryRecord` 객체에 **절대** 주입되지 않음 → write 경로 오염 원천 차단 (B3 해결)
2. **CortexVectorAdapter 실질 수정** — RPC `similarity` 필드 읽기 + PostgREST 경로 비대칭 명시 (B1 해결)
3. **CortexClient.recall 파라미터화** — `project_id` 명시 전달, import 시점 고정 제거 (B2 해결)
4. **over-fetch 전략 명시** — `search_mixed_scope`에서 `limit * 3` 선조회 후 post-filter → rank → top-N (B4 해결)
5. **기존 호출부 영향 최소** — facade 외부 API는 `list[MemoryRecord]` 유지 (tuple은 내부 파이프라인에서만)
6. **mixed-version compat** — cortex_vector에도 scope 파싱 try/except + LOCAL fallback (core_memory와 대칭)

---

## 3. 아키텍처 핵심 변경

### 3.1 Adapter interface — tuple 반환 (B3 근본 해결)

**`core/memory_system/adapters/base.py`**:

```python
@abstractmethod
async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    project_id: str | None = None,
) -> list[tuple[MemoryRecord, float]]:
    """Search by relevance.

    Returns:
        List of (record, score) tuples. Score in [0.0, 1.0], where:
        - 1.0 = exact semantic match
        - 0.0 = no meaningful score (e.g., substring adapter, or similarity unavailable)

        Score is NEVER stored on the record itself. It is an ephemeral query-time
        value that must be discarded after ranking.
    """
```

**왜 tuple이 옳은 선택인가**:
- score가 `MemoryRecord.metadata`에 절대 안 들어감 → `to_dict()`/`write()` 경로로 영속화 불가 (B3 해결)
- 반환 타입이 명시적 → "score 있음/없음" 암묵 규약 제거
- 기존 adapter 8개 중 1개(`cortex_vector`)만 실질 로직 수정, 나머지 7개는 `return [(rec, 0.0) for rec in ...]` 패턴으로 기계적 변환

**기존 호출부**:
- facade 내부: tuple을 풀어서 처리 (아래 3.3 참조)
- facade 외부 API: 여전히 `list[MemoryRecord]` 반환 → **외부 호출부 영향 없음**
- `adapter.search()` 직접 호출: cross-review가 확인한 대로 facade 외 caller 없음

### 3.2 CortexVectorAdapter 실질 수정 (B1 해결)

현재 `_cortex_to_record(row)`는 `row.get("similarity")`를 읽지 않음. 수정:

**`core/memory_system/adapters/cortex_vector.py`**:

```python
# 기존 (버그):
# def _cortex_to_record(self, row: dict) -> MemoryRecord:
#     meta = row.get("metadata", {}) or {}
#     ...
#     return MemoryRecord(...)

# 수정 (v2):
def _cortex_to_record(self, row: dict) -> tuple[MemoryRecord, float]:
    meta = row.get("metadata", {}) or {}
    # scope 파싱에 try/except 추가 (mixed-version compat, v1 cross-review T7)
    try:
        scope = MemoryScope(meta.get("scope", "local"))
    except ValueError:
        scope = MemoryScope.LOCAL

    record = MemoryRecord(
        record_id=meta.get("record_id", ""),
        scope=scope,
        ...
    )
    score = float(row.get("similarity", 0.0))  # ★ RPC 응답 top-level에서 추출
    return (record, score)
```

**경로별 score 비대칭 명시**:

| 호출 경로 | score 제공 |
|----------|----------|
| `search()` (RPC `match_cortex_memory`) | ✅ `row["similarity"]` 읽음 |
| `_search_by_hash()` (PostgREST GET) | ❌ `similarity` 없음 → 0.0 |
| `read()` (PostgREST GET) | ❌ `similarity` 없음 → 0.0 |

`_search_by_hash`와 `read`는 dedup/fetch 용도이지 관련도 검색이 아니므로 score=0.0이 의미적으로도 올바르다.

### 3.3 CortexClient.recall 파라미터화 (B2 해결)

**`skills/core/cortex.py`** 현재 상태:
```python
PROJECT_ID = os.path.basename(os.getcwd())  # import 시점 고정

class CortexClient:
    def recall(self, query, threshold=0.5, limit=10):
        filter_obj = {"project_id": PROJECT_ID}  # ★ 하드코딩
        ...
```

**수정**:
```python
_DEFAULT_PROJECT_ID = os.path.basename(os.getcwd())  # 하위 호환용 기본값

class CortexClient:
    def recall(
        self,
        query: str,
        *,
        threshold: float = 0.5,
        limit: int = 10,
        project_id: str | None = None,  # ★ 신규
    ) -> dict:
        effective_pid = project_id or _DEFAULT_PROJECT_ID
        filter_obj = {"project_id": effective_pid}
        ...
```

**`CortexVectorAdapter.search()` 변경**:
```python
async def search(self, query, *, limit=10, project_id=None):
    effective_pid = project_id if project_id is not None else self._project_id
    resp = self._client.recall(query, limit=limit, project_id=effective_pid)  # 전달
    ...
```

**중요**: `project_id=None` 의미 유지 — "현재 프로젝트로 검색". `None`과 빈 문자열 구분 필요.

### 3.4 Facade `search_semantic` 변경 (B3 해결)

**`core/memory_system/facade.py:164~218`** 수정 요약:

```python
async def search_semantic(self, query, *, limit=10, memory_type=None, scope=None):
    ...
    # 기존:
    # tasks = [adapter.search(query, limit=limit, project_id=self.project_id) ...]
    # all_records: list[MemoryRecord] = []
    # for res in results: all_records.extend(res)
    # ...
    # scored = decay_mgr.rank_by_relevance(deduped)

    # v2:
    tasks = [adapter.search(query, limit=limit, project_id=self.project_id) ...]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # adapter 결과가 이제 list[tuple[MemoryRecord, float]]
    all_records: list[MemoryRecord] = []
    score_map: dict[str, float] = {}  # record_id → score (ephemeral, facade local)

    for i, res in enumerate(results):
        if isinstance(res, BaseException):
            # 로깅 동일
            continue
        for rec, sc in res:
            all_records.append(rec)
            if sc > score_map.get(rec.record_id, 0.0):
                score_map[rec.record_id] = sc  # 여러 adapter 반환 시 max

    # type/scope filter (기존)
    ...

    # dedupe (기존)
    deduped = _deduplicate(active)

    # ★ semantic_scores를 rank_by_relevance에 전달
    scored = decay_mgr.rank_by_relevance(deduped, semantic_scores=score_map)
    return [rec for rec, _ in scored[:limit]]
```

**외부 API 영향**: 없음. 반환 타입 `list[MemoryRecord]` 유지.

### 3.5 `MemoryScope.PROJECT` 추가 (RAG 준비)

```python
class MemoryScope(str, Enum):
    LOCAL = "local"
    PROJECT = "project"   # ★ 신규 — 프로젝트 lifetime
    GLOBAL = "global"
    SESSION = "session"
```

**의미**:
- `LOCAL`: 단일 task/agent 내 임시 (기존)
- `PROJECT`: 한 프로젝트 전체 lifetime (신규, RAG 기본 스코프)
- `GLOBAL`: 모든 프로젝트가 참조 가능 (기존)
- `SESSION`: 프로세스 수명 (기존)

**하위 호환**: 기존 LOCAL 레코드 마이그레이션 불필요. cortex_vector에 try/except 추가로 구버전 크래시 방지 (3.2에서 이미 반영).

### 3.6 `search_mixed_scope` — over-fetch 전략 명시 (B4 해결)

**신규 메서드**:

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
    overfetch_multiplier: int = 3,  # ★ 명시
) -> list[MemoryRecord]:
    """Search PROJECT + optionally GLOBAL scope with ranking.

    Strategy (post-filter 순서 명시):
      1. adapter.search(limit = limit * overfetch_multiplier)
         - 2 queries per adapter (project_id=<target>, project_id=None)
         - project_id=None 결과에서 scope=GLOBAL만 유지 (post-filter)
      2. filter by memory_type (if specified)
      3. filter by min_score (from tuple score, not metadata)
      4. dedupe by content_hash
      5. rank_by_relevance with semantic_scores from tuples
      6. return top `limit`
    """
    effective_pid = project_id_override or self.project_id
    overfetch = limit * max(1, overfetch_multiplier)

    # Step 1: PROJECT scope query (project_id filter 적용)
    project_tasks = [
        adapter.search(query, limit=overfetch, project_id=effective_pid)
        for adapter in self._adapters.values()
    ]
    # Step 1-2: GLOBAL scope query (project_id=None → post-filter GLOBAL만)
    global_tasks = []
    if include_global:
        global_tasks = [
            adapter.search(query, limit=overfetch, project_id=None)
            for adapter in self._adapters.values()
        ]

    all_tuples: list[tuple[MemoryRecord, float]] = []
    for res in await asyncio.gather(*project_tasks, return_exceptions=True):
        if not isinstance(res, BaseException):
            all_tuples.extend(res)
    for res in await asyncio.gather(*global_tasks, return_exceptions=True):
        if not isinstance(res, BaseException):
            # post-filter GLOBAL only
            all_tuples.extend((r, s) for r, s in res if r.scope == MemoryScope.GLOBAL)

    # Step 2: memory_type filter
    if memory_type:
        all_tuples = [(r, s) for r, s in all_tuples if r.memory_type == memory_type]

    # Step 3: min_score filter
    if min_score > 0.0:
        all_tuples = [(r, s) for r, s in all_tuples if s >= min_score]

    # Step 4: dedupe (content_hash) — 같은 hash 중 score 높은 것 유지
    by_hash: dict[str, tuple[MemoryRecord, float]] = {}
    for r, s in all_tuples:
        key = r.content_hash or r.record_id
        if key not in by_hash or by_hash[key][1] < s:
            by_hash[key] = (r, s)
    deduped = list(by_hash.values())

    # Step 5: rank
    score_map = {r.record_id: s for r, s in deduped}
    records_only = [r for r, _ in deduped]
    scored = MemoryDecayManager().rank_by_relevance(records_only, semantic_scores=score_map)

    # Step 6: top-N
    return [rec for rec, _ in scored[:limit]]
```

**over-fetch 비용**: 3x overfetch × 2 scope (PROJECT+GLOBAL) × 8 adapter = 최대 48 adapter 호출. cortex_vector(가장 느림) 기준 P95 ≈ 600~800ms. 허용 가능. 비용이 문제되면 `overfetch_multiplier=1`로 호출자가 조절 가능.

---

## 4. 변경 파일 목록 (v2)

| 파일 | 변경 유형 | 라인 증감 |
|------|---------|---------|
| `core/memory_system/models.py` | `MemoryScope.PROJECT` 추가 | +1 |
| `core/memory_system/adapters/base.py` | `search` 반환 타입 → tuple | 타입 변경 |
| `core/memory_system/adapters/cortex_vector.py` | `_cortex_to_record` tuple + similarity 읽기 + scope try/except + `search` 시그니처 업데이트 | +15 |
| `core/memory_system/adapters/core_memory.py` | `search` → tuple 반환 (score=0.0 래핑) | +3 |
| `core/memory_system/adapters/` 나머지 6개 | 동일하게 기계적 tuple 래핑 | 각 +3 |
| `core/memory_system/facade.py` | `search_semantic` tuple 처리 + `search_mixed_scope` 신규 | +80 |
| `skills/core/cortex.py` | `recall` `project_id` 파라미터 | +3 |
| `tests/test_memory_facade_rag_extension.py` | **신규** — 8개 단위 테스트 | +180 |

**미수정**:
- `core/memory_system/decay.py` — `rank_by_relevance(semantic_scores=...)` 이미 지원
- `core/memory_system/cross_project.py` — 기존 API 유지 (v2 기능 활용은 후속 RAG 설계에서)

---

## 5. Phase별 구현 순서 (작은 PR로 분할)

| Phase | 내용 | 독립 커밋 가능 |
|-------|------|-------------|
| **P0** | `MemoryScope.PROJECT` enum 추가 + cortex_vector scope try/except | ✅ |
| **P1** | Adapter interface tuple 반환 변경 (8개 adapter 기계적 변환) | ✅ |
| **P2** | `facade.search_semantic` tuple 처리 + `semantic_scores` 전달 | ✅ (P1 필요) |
| **P3** | `CortexClient.recall` project_id 파라미터화 + adapter 전달 | ✅ (독립) |
| **P4** | `cortex_vector._cortex_to_record` similarity 실제 읽기 | ✅ (P1 필요) |
| **P5** | `facade.search_mixed_scope` 신규 메서드 | ✅ (P2, P3 필요) |

각 Phase가 **독립 테스트 가능**하며, 전체 롤아웃 중 어느 시점에도 기존 동작이 깨지지 않는다.

---

## 6. 테스트 전략 (v2 신규 관점 반영)

`tests/test_memory_facade_rag_extension.py`:

```python
# P0
def test_memory_scope_project_exists(): ...
def test_cortex_vector_handles_unknown_scope_gracefully():
    """scope='project' 레코드를 구버전 cortex_vector가 읽어도 crash 안 됨 (LOCAL fallback)."""

# P1
def test_adapter_search_returns_tuples():
    """모든 adapter가 list[tuple[MemoryRecord, float]] 반환."""

def test_score_does_not_leak_to_metadata():
    """adapter search 결과의 record.metadata에 '_score' 키 없음."""

# P2
async def test_search_semantic_uses_tuple_scores():
    """high-score tuple이 랭킹 상위로 오름."""

# P3
async def test_cortex_client_recall_accepts_project_id_override():
    """CortexClient.recall(project_id=X) → filter_obj.project_id=X."""

async def test_cortex_adapter_threads_project_id():
    """CortexVectorAdapter.search(project_id=X) → recall(project_id=X) 호출."""

# P4
async def test_cortex_adapter_reads_similarity_from_rpc():
    """mock recall 응답의 similarity=0.87 → tuple score 0.87."""

async def test_cortex_postgrest_path_returns_zero_score():
    """_search_by_hash와 read는 score=0.0 (similarity 없는 경로)."""

# P5
async def test_search_mixed_scope_combines_project_and_global(): ...
async def test_search_mixed_scope_applies_memory_type_post_filter(): ...
async def test_search_mixed_scope_applies_min_score_filter(): ...
async def test_search_mixed_scope_overfetch_respects_limit():
    """overfetch_multiplier=3으로 limit=5 요청 → 내부 15 조회 후 top 5 반환."""

# 회귀 방지
async def test_existing_search_semantic_returns_memory_records():
    """외부 API 반환 타입 list[MemoryRecord] 유지 확인."""
```

---

## 7. 하위 호환

| 항목 | 영향 |
|------|------|
| `MemoryScope.LOCAL` 기존 레코드 | 없음. 마이그레이션 불필요 |
| `facade.search_semantic()` 외부 호출부 | 없음. 반환 타입 `list[MemoryRecord]` 유지 |
| `facade.search_all_backends()` | 변경 없음 |
| `adapter.search()` 외부 호출 | **없음** (cross-review T4 확인 — facade 외 caller 존재 안 함) |
| 기존 `tests/test_memory_*` | `semantic_scores` 변경으로 랭킹 결과는 달라질 수 있으나, 기존 테스트는 `len()`/`dedupe` 위주라 영향 없음 (cross-review T3 확인) |
| 구버전 AF가 `scope="project"` 레코드 읽기 | P0의 try/except로 LOCAL fallback 보호 |

---

## 8. Blast Radius

| 영향 대상 | 수준 | 설명 |
|---------|------|------|
| `models.py` | **Low** | enum 1줄 추가 |
| `adapters/base.py` | **Medium** | 반환 타입 변경 (인터페이스 변경) |
| `adapters/*.py` (8개) | **Low** | cortex_vector만 실질 수정, 7개는 기계적 tuple 래핑 |
| `facade.py` | **Medium** | `search_semantic` 내부 + 신규 메서드 |
| `skills/core/cortex.py` | **Low** | 파라미터 추가 |
| 기존 facade 호출부 | **None** | 외부 API 불변 |
| 후속 RAG 설계 | **Enabler** | 4개 BLOCK 모두 해제 |
| 성능 | **Low** | mixed-scope 2x 쿼리 + overfetch 3x (호출자가 조절 가능) |

---

## 9. 알려진 한계 (v2도 해결 안 함 — v3로 연기)

1. **`cortex.recall`이 동기 `urllib`** — async 환경에서 event loop blocking. v2 scope 밖. 별도 async HTTP 리팩토링 필요 (cross-review T6)
2. **`core_memory` adapter는 substring 매칭** — semantic 관련도 없음. 향후 embedding 기반 adapter로 교체 필요
3. **`search_mixed_scope` overfetch 3x**가 실측에서 부족할 수 있음 — 필드 테스트 후 조정

---

## 10. KPI

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| 기존 테스트 통과율 | `pytest tests/test_memory_*` | 100% (회귀 없음) |
| score 주입 검증 | 신규 단위 테스트 | 모두 통과 |
| `_score` metadata 부재 검증 | `assert "_score" not in record.metadata` | 모두 통과 |
| 랭킹 품질 (수동) | cortex_vector 포함 쿼리에서 관련도 높은 결과 상승 | 주관적 개선 확인 |
| mixed-scope latency P95 | 실측 | < 1000ms (overfetch 3x, 8 adapter) |

---

## 11. 체크리스트

- [ ] 설계 교차검증 (af-critic + af-cross-review 병렬 재검증)
- [ ] P0: `MemoryScope.PROJECT` + cortex scope try/except
- [ ] P1: adapter interface tuple 반환 (8개 adapter)
- [ ] P2: `facade.search_semantic` tuple 처리
- [ ] P3: `CortexClient.recall` project_id 파라미터화
- [ ] P4: `cortex_vector` similarity 실제 읽기
- [ ] P5: `search_mixed_scope` 구현
- [ ] 회귀 테스트 확인
- [ ] `docs/features/2026-04-24-persistent-rag-system.md` 재작성 (v2 전제)
- [ ] `Master_Blueprint.md` §3 memory_system 업데이트
- [ ] code-review.md 업데이트
- [ ] v1 문서를 `docs/features/deprecated/`로 이동 or 상단에 `> ⛔ 폐기: v2 사용` 배너

---

## 12. v1 대비 변경 요약

| 이슈 | v1 처리 | v2 처리 |
|------|--------|--------|
| score 전달 | `metadata["_score"]` 주입 | **tuple 반환** (레코드 밖) |
| CortexVector similarity | "이미 보유" (틀림) | `row["similarity"]` **실제 읽기 추가** |
| CortexClient project_id | 언급 없음 | `recall(project_id=...)` 파라미터화 |
| over-fetch | 명시 없음 | `overfetch_multiplier=3` + 필터 순서 1~6단계 명시 |
| mixed-version compat | 언급 없음 | cortex_vector scope try/except 추가 |
| dedup + score 관계 | 불명확 | dedupe 단계에서 **score 높은 것 유지** 명시 |
| 구현 순서 | 단일 단위 | 6 Phase로 분할 (독립 커밋) |

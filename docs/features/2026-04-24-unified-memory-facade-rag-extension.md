# UnifiedMemoryFacade — RAG 대응 확장 설계 (v1, 폐기)

> ⛔ **폐기됨 (2026-04-24)** — af-critic BLOCK 4 + af-cross-review BLOCK 2로 근본 수정 필요.
> 최신 설계: [`2026-04-24-unified-memory-facade-rag-extension-v2.md`](./2026-04-24-unified-memory-facade-rag-extension-v2.md)
>
> ---
>
> 날짜: 2026-04-24
> 상태: 폐기 (v2로 대체)
> 목적: 후속 영속 RAG 설계(`2026-04-24-persistent-rag-system.md`)의 전제 인프라를 먼저 구축
> 선행 판정: af-critic BLOCK 4건 (2026-04-24) — 현 facade가 RAG 청크 retrieval에 필요한 API 미지원

## 1. 문제 정의 (af-critic이 밝혀낸 4개 인프라 갭)

| 갭 | 현 코드 상태 | RAG에 필요한 것 |
|----|------------|---------------|
| **G1** | `MemoryScope` enum = `{LOCAL, GLOBAL, SESSION}`. `PROJECT` 없음 | 프로젝트별 자료 격리용 `PROJECT` 스코프 |
| **G2** | `search_semantic()`이 `rank_by_relevance(deduped)`를 **`semantic_scores=None`으로 호출** (facade.py:215). cosine 유사도는 adapter 내부에만 존재, facade에 전달 안 됨 | adapter가 (record, score) 쌍을 반환하고 facade가 score dict를 `rank_by_relevance`에 전달 |
| **G3** | `search_semantic(project_id)`는 **singleton의 `self.project_id` 고정**. `search_all_backends()`는 project_id 필터 **완전 제거**. 두 극단만 존재 | PROJECT=this + GLOBAL 혼합 검색 (mixed-scope query) |
| **G4** | adapter `search()` 반환 타입이 `list[MemoryRecord]` — score 포함 안 됨 | `list[tuple[MemoryRecord, float]]` 또는 metadata에 score 주입 |

## 2. 설계 목표

1. **G1~G4를 최소 변경으로 해결** — 기존 API 깨지 않음
2. **adapter interface 점진적 확장** — 기존 adapter가 score 반환 안 해도 동작 (float=0.0 기본값)
3. **기존 호출부 영향 없음** — `search_semantic(scope=None)` 같은 기존 시그니처 유지, 새 파라미터는 옵셔널
4. **테스트 우선** — 각 변경마다 단위 테스트

## 3. 아키텍처

### 3.1 G1 — `MemoryScope.PROJECT` 추가

`core/memory_system/models.py`:

```python
class MemoryScope(str, Enum):
    LOCAL = "local"         # 개별 task/session (기존)
    PROJECT = "project"     # 프로젝트 단위 (신규)
    GLOBAL = "global"       # cross-project (기존)
    SESSION = "session"     # 현재 프로세스 (기존)
```

**의미 분리**:
- `LOCAL`: 단일 task/agent 내 임시 (기존과 동일)
- `PROJECT`: 한 프로젝트 전체 lifetime (RAG 자료 기본)
- `GLOBAL`: 모든 프로젝트가 참조 가능한 재사용 자료
- `SESSION`: 프로세스 수명 (휘발성)

**하위 호환**: 기존 `MemoryScope.LOCAL` 저장 레코드는 변경 없음. 마이그레이션 불필요.

### 3.2 G2, G4 — adapter가 score를 반환

**adapter base 변경** (`core/memory_system/adapters/base.py`):

```python
@abstractmethod
async def search(
    self,
    query: str,
    *,
    limit: int = 10,
    project_id: str | None = None,
) -> list[MemoryRecord]:
    """Free-text or semantic search. Results sorted by relevance.

    Adapters that compute a similarity score should set record.metadata["_score"]
    to a float in [0, 1]. Adapters without a meaningful score leave it unset
    (facade treats absence as 0.0 for ranking purposes).
    """
```

**접근 방식**: 반환 타입은 그대로 `list[MemoryRecord]` 유지. score는 **`record.metadata["_score"]`에 주입**. 이유:
- 기존 adapter 모두 변경 최소화 (단지 metadata 한 줄 추가)
- `MemoryRecord` dataclass 수정 불필요
- tuple 반환 타입 변경이 전 호출부 영향

**facade 변경** (`core/memory_system/facade.py:215`):

```python
# 변경 전
scored = decay_mgr.rank_by_relevance(deduped)

# 변경 후
semantic_scores = {
    r.record_id: float(r.metadata.get("_score", 0.0))
    for r in deduped
}
scored = decay_mgr.rank_by_relevance(deduped, semantic_scores=semantic_scores)
```

**adapter 업데이트 (CortexVectorAdapter — 이미 cosine score 보유)**:

```python
# 현재 _search_by_hash에서 score를 이미 계산하므로 metadata에 주입만 추가
record.metadata["_score"] = similarity  # cosine result
```

**CoreMemoryAdapter (substring) 처리**: substring match에는 의미 있는 score 없음 → `_score` 미주입 → ranking에서 semantic 기여 0.0. 현재 동작과 동일.

### 3.3 G3 — mixed-scope 검색 API 신설

**신규 메서드** (`facade.py`):

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
) -> list[MemoryRecord]:
    """Search PROJECT scope (current or overridden project_id) + optionally GLOBAL scope.

    Unlike search_semantic (single project_id filter) and search_all_backends
    (no filter at all), this executes two adapter.search() calls per adapter:
    one with project_id=<target>, one with project_id=None (filtered to GLOBAL
    scope post-hoc).

    Args:
        project_id_override: override the facade's bound project_id. If None,
            uses self.project_id.
        include_global: if True, merge GLOBAL scope records from all projects.
        min_score: filter out records with metadata["_score"] < min_score.

    Returns deduped list ranked by relevance (semantic + recency + frequency).
    """
```

**구현 전략**:
1. 각 adapter에 대해 2개 쿼리 실행: `project_id=<target>`, `project_id=None`
2. 두 번째 쿼리 결과를 `scope=GLOBAL`만 post-filter
3. 합쳐서 dedupe (`content_hash`)
4. `min_score` threshold로 필터
5. `rank_by_relevance` (G2에서 수정됨)

**기존 `search_semantic` / `search_all_backends`는 유지** — 각자 명확한 단일 목적.

### 3.4 `CrossProjectRecall`과의 관계

`core/memory_system/cross_project.py:19`의 `CrossProjectRecall`은 **계속 유효**. 역할 재정의:

| 메서드 | 용도 |
|-------|------|
| `recall_global(query)` | GLOBAL scope 레코드만 (knowledge asset) |
| `recall_all_projects(query)` | 모든 프로젝트 무차별 (solution reuse) |
| `search_mixed_scope(query)` | **신규** — 현재 프로젝트 + GLOBAL 혼합 (RAG의 기본 retrieval 모드) |

---

## 4. 함수 시그니처 (확정)

```python
# core/memory_system/models.py
class MemoryScope(str, Enum):
    LOCAL = "local"
    PROJECT = "project"   # 신규
    GLOBAL = "global"
    SESSION = "session"

# core/memory_system/adapters/base.py — interface 그대로, docstring만 업데이트
async def search(self, query, *, limit=10, project_id=None) -> list[MemoryRecord]:
    """record.metadata['_score']에 [0,1] similarity 주입 권장."""

# core/memory_system/facade.py
async def search_semantic(self, query, *, limit=10, memory_type=None, scope=None):
    # 변경: semantic_scores dict를 rank_by_relevance에 전달
    ...

async def search_mixed_scope(
    self, query, *,
    limit=10,
    memory_type=None,
    include_global=True,
    project_id_override=None,
    min_score=0.0,
) -> list[MemoryRecord]:
    # 신규
    ...
```

---

## 5. 코드 변경 파일

| 파일 | 변경 | 라인 증감 |
|------|-----|---------|
| `core/memory_system/models.py` | `MemoryScope.PROJECT` 추가 | +1 |
| `core/memory_system/facade.py` | `search_semantic` score 전달 + `search_mixed_scope` 신규 | +60 |
| `core/memory_system/adapters/base.py` | docstring 업데이트 ("_score" 규약) | +5 |
| `core/memory_system/adapters/cortex_vector.py` | cosine score를 `metadata["_score"]`에 주입 | +5 |
| `core/memory_system/adapters/core_memory.py` | substring match는 score 생략 (현 동작 유지) | 0 |
| 기타 adapter 6개 | score 생략 허용 (facade가 0.0 fallback) | 0 |
| `tests/test_memory_facade_rag_extension.py` | **신규** | +120 |

**미수정**:
- `core/memory_system/decay.py` — `rank_by_relevance`가 이미 `semantic_scores` 파라미터 지원
- `core/memory_system/cross_project.py` — 기존 API 유지
- adapter 8개 중 cortex_vector 외 7개는 변경 없음

---

## 6. 하위 호환

### 6.1 기존 `MemoryScope.LOCAL` 데이터

- 변경 없음. `PROJECT`는 신규 스코프로, 기존 레코드는 그대로 `LOCAL` 유지
- 향후 RAG 청크만 `PROJECT` 스코프로 저장. 기존 코드는 계속 `LOCAL` 또는 `GLOBAL` 사용

### 6.2 기존 adapter의 `search()` 반환

- `metadata["_score"]` 주입은 **선택 사항**
- 미주입 시 facade는 0.0으로 처리 → semantic 가중치 없이 recency+frequency로 랭킹 (현 동작)

### 6.3 기존 `search_semantic` 호출부

- 시그니처 변경 없음 (`scope`, `memory_type`, `limit` 파라미터 그대로)
- 내부 랭킹이 semantic score를 반영하게 되므로 결과 순서가 개선됨 — **기존 호출부에는 긍정적 영향**

### 6.4 기존 `search_all_backends` 호출부

- 변경 없음. project_id 필터 없는 무차별 검색 유지

---

## 7. Blast Radius

| 영향 대상 | 수준 | 설명 |
|---------|------|------|
| `memory_system/models.py` | **Low** | enum 추가 |
| `memory_system/facade.py` | **Medium** | `search_semantic` 내부 변경 + 신규 메서드 |
| `memory_system/adapters/cortex_vector.py` | **Low** | metadata 한 줄 |
| 기존 테스트 | **Low** | 결과 순서가 개선되는 방향이라 테스트 깨질 가능성 낮음. 단 snapshot 형태 assert면 업데이트 필요 |
| RAG 후속 설계 | **Enabler** | 4개 BLOCK이 모두 해제됨 |
| `CrossProjectRecall` | **None** | 기존 메서드 유지, `search_mixed_scope`는 addition |
| Supabase 미설정 환경 | **None** | cortex_vector 어댑터가 disabled되어 score도 미주입. 현 동작과 동일 |

---

## 8. 테스트 전략

`tests/test_memory_facade_rag_extension.py` 신규:

```python
# G1
def test_memory_scope_project_exists():
    assert MemoryScope.PROJECT.value == "project"

# G2
async def test_search_semantic_uses_score_from_metadata():
    # fixture: mock adapter that returns records with metadata["_score"]
    # assert: high-score record ranks higher than low-score
    ...

# G3
async def test_search_mixed_scope_combines_project_and_global():
    # fixture: 2 adapters with PROJECT scope records (proj_A) + GLOBAL records
    # call search_mixed_scope(project_id_override="proj_A", include_global=True)
    # assert: both proj_A records and GLOBAL records returned
    ...

async def test_search_mixed_scope_min_score_filter():
    # records with score 0.5 and 0.8, min_score=0.7
    # assert: only 0.8 returned
    ...

# G4
async def test_adapter_without_score_uses_zero_fallback():
    # CoreMemoryAdapter-like: no _score in metadata
    # assert: ranking still works (recency+frequency only)
    ...

# 하위 호환
async def test_existing_search_semantic_unchanged():
    # 기존 호출 패턴 (scope=None, memory_type=None)
    # assert: 반환 타입과 레코드 구성 이전과 동일
    ...
```

---

## 9. KPI

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| 랭킹 품질 | semantic score 전달 전/후 top-3 hit 비교 (수동 평가) | 개선 확인 |
| mixed-scope latency | 단일 scope 쿼리 대비 P95 | < 2x |
| 기존 테스트 통과율 | pytest tests/test_memory_* | 100% |

---

## 10. 체크리스트

- [ ] 설계 교차검증 (af-critic + af-cross-review 병렬)
- [ ] G1: `MemoryScope.PROJECT` 추가 + 테스트
- [ ] G2: `search_semantic`이 semantic_scores 전달 + 테스트
- [ ] G4: `CortexVectorAdapter.search`가 metadata["_score"] 주입 + 테스트
- [ ] G3: `search_mixed_scope` 메서드 구현 + 테스트
- [ ] adapter base docstring 업데이트 ("_score" 규약 문서화)
- [ ] 기존 테스트 회귀 확인 (`tests/test_memory_*`)
- [ ] `docs/2026-04-24-persistent-rag-system.md` 재작성 (이 확장을 전제로)
- [ ] `Master_Blueprint.md` §3 memory_system 섹션 업데이트
- [ ] code-review.md 업데이트

---

## 11. 다음 문서

이 facade 확장이 완료되면 `2026-04-24-persistent-rag-system.md`를 다음 전제로 재작성:

1. `MemoryScope.PROJECT` 사용 가능
2. `facade.search_mixed_scope(project_id_override, include_global, min_score=0.7)`로 RAG retrieval
3. `CortexVectorAdapter`가 cosine score를 `_score`에 주입 → threshold 필터 작동

**async/sync 충돌(BLOCK 3)**은 이 확장이 아닌 RAG 설계 쪽에서 `asyncio.run()` 래퍼 또는 `researcher` async 전환으로 별도 해결.

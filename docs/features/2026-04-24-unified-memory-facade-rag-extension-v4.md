# UnifiedMemoryFacade — RAG 대응 확장 설계 v4 (폐기)

> ⛔ **폐기됨 (2026-04-24)** — af-critic BLOCK 2건 + af-cross-review HOLD 2건으로 추가 수정.
> 최신: [`2026-04-24-unified-memory-facade-rag-extension-v5.md`](./2026-04-24-unified-memory-facade-rag-extension-v5.md)
>
> ---
>
> 날짜: 2026-04-24
> 상태: 폐기 (v5로 대체)
> 선행: v1, v2, v3 (모두 폐기) — v3에서 BLOCK 4건 추가 발견
> 형식: v3 delta 문서 — v3 전체 내용을 상속, **변경된 부분만** 본 문서에 명시
> v3 원본: [`2026-04-24-unified-memory-facade-rag-extension-v3.md`](./2026-04-24-unified-memory-facade-rag-extension-v3.md)

---

## 0. v4 변경 요약

v3 구조(§1~§11)는 그대로 유효하다. v4는 af-critic v3 리뷰의 **BLOCK 4건 + SUGGEST 4건**을 문서 수정 수준으로 반영한다. 아키텍처 근본 변경 없음.

| # | v3 BLOCK | v4 해결 |
|---|---------|--------|
| **v3-B1** | Phase B/C 경계에서 cortex_vector tuple 래핑 귀속 모호 → Phase B 커밋 직후 cortex 쓰는 환경 크래시 | **Phase 재배치**: cortex_vector의 tuple 래핑을 **Phase B로 이동**. Phase C는 similarity 실제 추출만 |
| **v3-B2** | `skills/core/cortex.py:180` `apply()` 함수가 `save_memory(inp, metadata)` positional 호출 — v3가 영향 미분석 | **명시**: `apply()`는 수정하지 않음. `save_memory`에 `project_id` 전달 안 함 → `_DEFAULT_PROJECT_ID` fallback. 기존 동작과 동일 |
| **v3-B3** | `_deduplicate_with_scores` score 0.0 동점 access_count fallback **테스트 누락** + Phase B 요약에 `rank_by_relevance` semantic_scores 전달 **명시 누락** | **테스트 추가** + Phase B 체크리스트에 "facade `search_semantic`/`search_all_backends`에 `semantic_scores` dict 전달" 명시 |
| **v3-B4** | `KnowledgeGraphAdapter` GLOBAL 노드가 PROJECT 분기·GLOBAL 분기 **양쪽에서 반환** → 이중 계산 구조 (dedupe로 해결되나 비효율) | **PROJECT 분기 post-filter 추가**: `search_mixed_scope`의 PROJECT 쿼리 결과에서 `r.scope != MemoryScope.GLOBAL`만 유지 |

| SUGGEST | 해결 |
|---------|------|
| S5: `_DEFAULT_PROJECT_ID` pytest cwd 불안정 | 알려진 한계 §9에 추가 + 신규 테스트에서 `monkeypatch.chdir` 사용 지시 |
| S6: Phase B에 `rank_by_relevance` 명시 누락 | v4 §2 체크리스트에 포함 (B3과 동일) |
| S7: `CrossProjectRecall.recall_global` 영향 분석 누락 | §6 하위 호환 섹션에 명시 |
| S8: `search_mixed_scope` 두 `asyncio.gather` 순차 실행 → 병렬화 가능 | **병렬화 적용**: `asyncio.gather(asyncio.gather(*project_tasks), asyncio.gather(*global_tasks))` 패턴 |

---

## 1. 변경 내용 (v3 대비)

### 1.1 §4 Phase 계획 재배치 (v3-B1 해결)

**v3 Phase 계획:**
| Phase | 내용 |
|-------|------|
| A | MemoryScope.PROJECT + scope try/except + knowledge_graph 매핑 |
| B | Adapter interface tuple 변경 + facade 두 메서드 + 기존 테스트 |
| C | **cortex_vector `search()`가 similarity 실제 추출** + CortexClient 파라미터화 |
| D | search_mixed_scope + timeout + overfetch |

**v4 Phase 계획 (수정):**
| Phase | 내용 | 근거 |
|-------|------|-----|
| A | MemoryScope.PROJECT + scope try/except + knowledge_graph 매핑 | 변경 없음 |
| B | Adapter interface tuple 변경 + **cortex_vector 포함 전 8개 adapter `(rec, 0.0)` 래핑** + facade `search_semantic`/`search_all_backends` tuple 처리 + `_deduplicate_with_scores` + **`rank_by_relevance`에 `semantic_scores` 전달** + 기존 테스트 수정 | **cortex_vector의 tuple 래핑을 Phase B에 포함** (v3-B1). facade가 tuple unpack 시작할 때 모든 adapter가 이미 tuple 반환 상태 보장 |
| C | **cortex_vector `search()`가 `row["similarity"]` 실제 추출** (이전 Phase C에서 B1 지적된 "tuple 래핑"은 Phase B로 이동) + `CortexClient.recall`/`save_memory` 파라미터화 + adapter `write` project_id 전달 | similarity 추출은 Phase B의 `(rec, 0.0)` 기본값 위에 덮어쓰는 최적화 |
| D | search_mixed_scope + **병렬 gather (S8)** + overfetch + min_score + timeout + 신규 테스트 | 병렬화 반영 |

**Phase B → C 전환 시 동작**:
- Phase B 커밋 직후: cortex_vector는 `(rec, 0.0)` 반환 (score는 모두 0.0이지만 동작은 정상)
- Phase C 커밋 후: cortex_vector는 `(rec, 0.87)` 반환 (실제 similarity)

즉 Phase B에서 "interface 변경"은 완결, Phase C에서 "score 값 최적화"만 추가. 각 Phase가 독립적으로 pytest 통과.

### 1.2 §2.3 `search_mixed_scope` 수정 (v3-B4 + S8 해결)

```python
async def search_mixed_scope(
    self, query, *,
    limit=10, memory_type=None, include_global=True,
    project_id_override=None, min_score=0.0,
    overfetch_multiplier=3,
) -> list[MemoryRecord]:
    if limit <= 0:
        return []
    self._ensure_initialised()
    timeout = get_config().timeouts.search_timeout
    effective_pid = project_id_override or self.project_id
    overfetch = limit * max(1, overfetch_multiplier)

    project_tasks = [
        asyncio.wait_for(
            adapter.search(query, limit=overfetch, project_id=effective_pid),
            timeout=timeout,
        )
        for adapter in self._adapters.values()
    ]
    global_tasks = [
        asyncio.wait_for(
            adapter.search(query, limit=overfetch, project_id=None),
            timeout=timeout,
        )
        for adapter in self._adapters.values()
    ] if include_global else []

    # ★ S8 반영: PROJECT/GLOBAL 쿼리를 병렬 실행
    project_results, global_results = await asyncio.gather(
        asyncio.gather(*project_tasks, return_exceptions=True),
        asyncio.gather(*global_tasks, return_exceptions=True),
    )

    all_tuples: list[tuple[MemoryRecord, float]] = []
    for res in project_results:
        if isinstance(res, BaseException):
            continue
        # ★ v3-B4 반영: PROJECT 분기에서 GLOBAL 노드 제외 (knowledge_graph 이중 계산 방지)
        all_tuples.extend(
            (r, s) for r, s in res if r.scope != MemoryScope.GLOBAL
        )
    for res in global_results:
        if isinstance(res, BaseException):
            continue
        # GLOBAL 분기에서는 GLOBAL scope만 유지 (기존 로직 동일)
        all_tuples.extend((r, s) for r, s in res if r.scope == MemoryScope.GLOBAL)

    # memory_type + min_score + dedupe + rank (v3와 동일)
    ...
```

**v3-B4 효과**: `KnowledgeGraphAdapter`가 `project_id=effective_pid`로 쿼리받아도 `node.project_id is None`(GLOBAL) 노드를 함께 반환 → v4는 이를 PROJECT 분기에서 post-filter로 제거. GLOBAL 분기에서만 한 번 집계.

### 1.3 §2.4 `CortexClient` 파라미터화 명시 보강 (v3-B2 해결)

v3 §2.4의 `save_memory` 파라미터화 설계는 유지. **추가 명시**:

> **`apply()` 경로 (cortex.py:180) 미수정**:
>
> 기존 `apply()`는 `self.client.save_memory(inp, metadata)`를 positional 2-arg로 호출한다. v4도 이 호출부는 수정하지 않는다. v4 `save_memory` 시그니처 `save_memory(content, metadata, *, project_id=None)`이 keyword-only 파라미터를 기본값 `None`으로 받으므로 기존 호출은 **그대로 동작**한다.
>
> `project_id=None` → `effective_pid = None or metadata.get("project_id") or _DEFAULT_PROJECT_ID`로 `_DEFAULT_PROJECT_ID` fallback이 발동. **`apply()`의 기존 동작(현재 cwd 기반 프로젝트)과 완전히 동일**.
>
> 의도: Skill의 `apply()`는 현재 프로젝트 컨텍스트에서 호출되므로 `_DEFAULT_PROJECT_ID`가 올바른 값. 별도 파라미터 주입 불필요.

### 1.4 §5 테스트 보강 (v3-B3 해결)

v3 §5의 테스트 목록에 아래 **신규 추가**:

```python
# v3-B3: score 0.0 동점 + access_count fallback
async def test_deduplicate_with_scores_score_zero_tie_uses_access_count():
    """비벡터 adapter 여러 곳에서 동일 content_hash 반환 시 (모두 score=0.0),
    access_count 높은 레코드가 유지되어야 한다."""
    ...

# v3-B3: rank_by_relevance semantic_scores 전달 확인
async def test_search_semantic_passes_semantic_scores_to_rank():
    """mock rank_by_relevance가 semantic_scores=score_map을 받는지 검증."""
    ...

async def test_search_all_backends_passes_semantic_scores_to_rank():
    """동일하게 search_all_backends도 검증."""
    ...

# v3-B4: PROJECT 분기 GLOBAL 제외 검증
async def test_search_mixed_scope_project_branch_excludes_global_scope():
    """project_id 전달로 반환된 결과 중 scope=GLOBAL인 레코드는 PROJECT 분기에서 제외,
    GLOBAL 분기에서만 한 번 집계되는지 검증."""
    ...

# S8: 병렬 gather 검증
async def test_search_mixed_scope_runs_project_and_global_in_parallel():
    """project/global gather가 직렬이 아닌 병렬로 실행되는지 타이밍 검증."""
    ...

# S5: pytest cwd 안정화
def test_cortex_default_project_id_respects_monkeypatch_chdir(monkeypatch, tmp_path):
    """monkeypatch.chdir(tmp_path) 이후 CortexClient 재import 시 _DEFAULT_PROJECT_ID가
    tmp_path 이름으로 설정되는지."""
    ...
```

### 1.5 §6 하위 호환 보강 (SUGGEST S7 반영)

v3 §6에 아래 행 추가:

| 항목 | 영향 | 비고 |
|------|------|------|
| `CrossProjectRecall.recall_global` | **변경 없음, 의미 drift** | Phase A에서 `KnowledgeGraphAdapter._node_to_record`가 project_id 있는 노드에 `MemoryScope.PROJECT` 부여. `recall_global(scope=GLOBAL)` 필터에서 이 노드들은 기존에도 제외됐으므로 실질 변화 없음. 단 향후 `recall_project(scope=PROJECT)` 같은 API를 추가할 시 방향성 확보 |

### 1.6 §9 알려진 한계 보강 (SUGGEST S5 반영)

v3 §9에 항목 5 추가:

> **5. `_DEFAULT_PROJECT_ID` 테스트 환경 불안정성**
>
> `_DEFAULT_PROJECT_ID = os.path.basename(os.getcwd())`는 모듈 import 시점에 계산됨. pytest가 프로세스 시작 시 cwd를 repo root로 설정한 뒤 import하므로 일반적으로 `"agent-factory"`로 고정. **단, 테스트 내에서 `os.chdir()` 호출 시 이미 계산된 `_DEFAULT_PROJECT_ID`는 변경되지 않음**. 명시적 `project_id` 전달을 권장.

---

## 2. Phase 체크리스트 (v4 확정)

### Phase A (단일 커밋, ~50 라인)
- [ ] `core/memory_system/models.py`: `MemoryScope.PROJECT` 추가
- [ ] `core/memory_system/adapters/cortex_vector.py`: `_cortex_to_record`에 `MemoryScope()` try/except + LOCAL fallback
- [ ] `core/memory_system/adapters/knowledge_graph.py:206`: `GLOBAL if project_id is None else PROJECT`
- [ ] 신규 테스트 3건 (`test_memory_scope_project_value`, `test_cortex_vector_unknown_scope_falls_back_local`, `test_knowledge_graph_project_id_maps_to_project_scope`)

### Phase B (원자 커밋, ~400~500 라인)
- [ ] `core/memory_system/adapters/base.py`: `search` 반환 타입 → `list[tuple[MemoryRecord, float]]`
- [ ] **8개 adapter** 전부 `(rec, 0.0)` 래핑 (cortex_vector 포함, similarity 추출은 Phase C로 연기)
- [ ] InMemoryAdapter (test_phase10 내 fixture) tuple 래핑
- [ ] `core/memory_system/facade.py`: `search_semantic` + `search_all_backends` tuple unpack → `score_map` 구성 → `_deduplicate_with_scores` → **`rank_by_relevance(semantic_scores=score_map)` 전달** ← v3-B3/S6 명시
- [ ] `_deduplicate_with_scores` 헬퍼 신규 (content_hash 키, score 우선, 동점 시 access_count)
- [ ] 기존 테스트 수정: `test_phase10/11/13` assertion `results[0].x` → `results[0][0].x` 패턴 (12건)
- [ ] 신규 테스트: `test_adapter_search_returns_tuples`, `test_score_not_leaked_to_record_metadata`, `test_search_semantic_uses_tuple_scores`, `test_search_all_backends_uses_tuple_scores`, `test_deduplicate_with_scores_prefers_higher_score`, `test_deduplicate_with_scores_score_zero_tie_uses_access_count`, `test_search_semantic_passes_semantic_scores_to_rank`, `test_search_all_backends_passes_semantic_scores_to_rank`

### Phase C (A+B 필요)
- [ ] `skills/core/cortex.py`:
  - [ ] `PROJECT_ID` → `_DEFAULT_PROJECT_ID` 리네임
  - [ ] `recall(..., project_id=None)` 파라미터 추가
  - [ ] `save_memory(content, metadata, *, project_id=None)` 파라미터 추가
  - [ ] `apply()` 호출부 **미수정** (v3-B2 명시)
- [ ] `core/memory_system/adapters/cortex_vector.py`:
  - [ ] `search()`에서 `row.get("similarity", 0.0)` 실제 추출 → Phase B의 `(rec, 0.0)` 덮어쓰기
  - [ ] `write()`가 `project_id=effective_pid` 명시 전달
- [ ] 신규 테스트: `test_cortex_recall_accepts_project_id_override`, `test_cortex_save_memory_accepts_project_id`, `test_cortex_write_passes_effective_project_id`, `test_cortex_search_reads_similarity_from_rpc`, `test_cortex_default_project_id_respects_monkeypatch_chdir`

### Phase D (A+B+C 필요)
- [ ] `core/memory_system/facade.py`: `search_mixed_scope` 신규
  - [ ] `asyncio.gather(asyncio.gather(*project), asyncio.gather(*global))` 병렬화 ← S8
  - [ ] PROJECT 분기 post-filter `r.scope != GLOBAL` ← v3-B4
  - [ ] `asyncio.wait_for` 래핑 (v2-N5)
  - [ ] `overfetch_multiplier=3` + `limit<=0` early exit
- [ ] 신규 테스트: `test_search_mixed_scope_combines_project_and_global`, `test_search_mixed_scope_applies_memory_type_post_filter`, `test_search_mixed_scope_applies_min_score_filter`, `test_search_mixed_scope_overfetch_respects_limit`, `test_search_mixed_scope_wraps_adapter_calls_with_wait_for`, `test_search_mixed_scope_handles_adapter_timeout_gracefully`, `test_search_mixed_scope_limit_zero_returns_empty`, `test_search_mixed_scope_project_branch_excludes_global_scope`, `test_search_mixed_scope_runs_project_and_global_in_parallel`
- [ ] 회귀 확인: `test_existing_search_semantic_returns_memory_records`, `test_existing_search_all_backends_returns_memory_records`

---

## 3. v3 대비 미변경 부분 (그대로 유효)

- §2.1~§2.6의 아키텍처 설계 (tuple 분리, `_cortex_to_record` MemoryRecord 유지, knowledge_graph scope 매핑, 42x 쿼리 수)
- §3 변경 파일 목록 전반
- §7 Blast Radius
- §8 KPI (단 §8에 병렬 gather로 P95 ≈ **400~600ms**로 개선 예상)
- §10~§11

---

## 4. 최종 체크리스트 (교차검증 재확인 대상)

양쪽 리뷰(af-critic + af-cross-review)가 체크해야 할 사항:

1. v1 BLOCK 4건 유지 (✅ v3에서 확인)
2. v2 BLOCK 5건 유지 (✅ v3에서 확인)
3. v3 BLOCK 4건 해결
   - [ ] v3-B1: Phase B가 cortex_vector tuple 래핑 포함
   - [ ] v3-B2: `apply()` 경로 명시
   - [ ] v3-B3: score 0.0 동점 테스트 + `rank_by_relevance` 명시
   - [ ] v3-B4: PROJECT 분기 GLOBAL 제외 post-filter
4. v3 SUGGEST 4건 반영
   - [ ] S5: 알려진 한계 추가
   - [ ] S6: Phase B에 명시 (B3과 동일)
   - [ ] S7: 하위 호환 표에 CrossProjectRecall
   - [ ] S8: 병렬 gather
5. 새 BLOCK이 v4에서 생겼는가?

---

## 5. 구현 착수 조건

v4가 교차검증에서 BLOCK 0 확인되면 즉시 Phase A부터 착수. 각 Phase는 독립 커밋이며 pytest 통과 시 다음 Phase 진행.

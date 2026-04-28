# 영속 RAG 시스템 설계

> 날짜: 2026-04-24
> 상태: 설계 v1 (교차검증 대기)
> 선행 판정: [`docs/참고/2026-04-24-paperclip-ing-analysis.md`](../참고/2026-04-24-paperclip-ing-analysis.md) — FIRST_RAG
> 대상 파일: `core/researcher.py`, `core/document_index.py`, `core/document_chunker.py`, `core/persistent_rag.py` (신규), `core/memory_system/facade.py`
> 연관 인프라: `core/memory_system/` 전반 (이미 존재하는 `UnifiedMemoryFacade` 활용)

## 1. 문제 정의

### 1.1 현재 상태

`core/researcher.py:507` `collect_project_evidence()`가 다음을 생성한다:

| 자산 | 현재 처리 | 문제 |
|------|----------|------|
| `local_references` | `DocumentIndex` (세션성) | 세션 종료 시 소실 |
| `web_references` (Tavily) | `ingest_external_chunks()` → 같은 DocumentIndex | 매 프로젝트마다 Tavily 재호출 |
| `llm_prior_references` | 동일 | 매번 LLM 재생성 |
| `notebook_summary` | **plain text 문자열** | 청크화 안 됨 → retrieval 불가 |
| `evidence_summary` | 리스트 | workflow에서 소비 후 사라짐 |

### 1.2 구조적 공백

`core/memory_system/cross_project.py`에 `CrossProjectRecall` 클래스가 **이미 존재**하며 `UnifiedMemoryFacade.search_semantic(scope=GLOBAL)`을 통해 cross-project 검색 축을 제공한다. 그러나:

- `researcher.py`가 이 facade를 **쓰지 않음** — DocumentIndex만 사용
- NotebookLM synthesis는 `MemoryRecord`로 변환되지 않고 소실
- 결과: **cross-project memory 레이어는 있는데 evidence 레이어는 세션성**인 기형

### 1.3 비용 측면

- Tavily: 프로젝트마다 재호출 (월 크레딧 소진)
- NotebookLM: 유료 API 호출을 매번 반복
- LLM prior knowledge: 토큰 비용

동일 도메인(예: 로또 관련 프로젝트 2번) 재실행 시 **이전 evidence를 재활용할 수 없는 것이 손실**.

---

## 2. 설계 목표

1. **NotebookLM synthesis를 청크화·영속화** — retrieval 가능한 자산으로 변환
2. **web/local/llm_prior/notebook 모두를 `UnifiedMemoryFacade`로 영속화** — 기존 메모리 인프라 재활용
3. **cross-project retrieval** — 현재 프로젝트에 없는 자료를 과거 프로젝트에서 가져옴
4. **기존 `DocumentIndex` ephemeral 인터페이스 100% 유지** — 하위 호환
5. **도메인 오염 방지** — `project_id` 스코프 + source_url 키 기반 중복 제거
6. **Fallback** — facade 장애 시 현재 ephemeral RAG로 graceful degradation
7. **Staleness 정책** — 웹 자료는 90일 TTL, NotebookLM synthesis는 프로젝트 lifetime

---

## 3. 아키텍처

### 3.1 기존 인프라 활용 (parallel stack 금지)

```
┌─────────────────────────────────────────────────────┐
│  researcher.py  collect_project_evidence()          │
│   ├─ local refs      ───┐                           │
│   ├─ web refs (Tavily)  │                           │
│   ├─ llm_prior_refs     │  make_virtual_chunk()      │
│   └─ notebook_summary ──┤                           │
└────────────────────────┬┴────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  core/persistent_rag.py (신규 — 얇은 어댑터)           │
│    ingest(chunks, project_id)  →  두 곳에 동시 저장:   │
│    ① DocumentIndex (ephemeral, 기존 그대로)          │
│    ② UnifiedMemoryFacade.store(MemoryType.SEMANTIC)  │
│        └─ scope: PROJECT (기본) or GLOBAL (옵션)      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Retrieval (역방향)                                   │
│   ① DocumentIndex.search(query)  ← 현재 세션 자료     │
│   ② facade.search_semantic(query,                   │
│        scope=GLOBAL or PROJECT=this,                 │
│        memory_type=SEMANTIC)                         │
│   → merge + dedupe by source_url/content_hash       │
└─────────────────────────────────────────────────────┘
```

**핵심**: `UnifiedMemoryFacade`는 이미 embedding·scope·backend 추상화를 제공한다. 새 벡터DB 인프라를 **만들지 않고** 이걸 쓴다.

### 3.2 청크 영속화 스키마

`make_virtual_chunk()` 출력을 `MemoryRecord`로 변환:

```python
MemoryRecord(
    content=chunk.content,
    memory_type=MemoryType.SEMANTIC,
    scope=MemoryScope.PROJECT,  # or GLOBAL for 재사용성 높은 자료
    metadata={
        "source_type": "web|local|llm_prior|notebook_synthesis",
        "source_url": chunk.source_url or "",
        "title": chunk.title,
        "weight": chunk.weight,  # web 0.9, local 1.0, llm_prior 0.4, notebook 0.95
        "verified": chunk.verified,
        "project_id": project_id,
        "captured_at": iso_utc(),
        "ttl_days": 90 if source_type == "web" else None,
    },
)
```

### 3.3 NotebookLM synthesis 청크화 (P1 핵심)

현재 `notebook_summary`는 단일 문자열. 다음 전략으로 청크화:

1. **문단 단위 split** — `\n\n` 기준 분할, 각 문단이 독립 청크
2. **Section heading 보존** — `## Key Findings` 같은 heading이 있으면 section별 청크
3. **메타데이터 강화** — `source_type="notebook_synthesis"`, `weight=0.95` (verified=True)
4. **길이 제한** — 단일 청크 800자 이하, 초과 시 추가 분할

`core/document_chunker.py`에 `make_notebook_chunks(synthesis_text, task_input)` 추가.

### 3.4 Retrieval 통합

`researcher._collect_local_references()` 경로에 **cross-project 사전 조회** 삽입:

```python
def _collect_local_references(self, task_input, workspace, limit=6):
    # 기존: 로컬 파일 DocumentIndex 검색
    local_hits = current_implementation(...)

    # ★ 신규: facade에서 PROJECT=this + GLOBAL 검색
    persistent_hits = self._query_persistent(task_input, limit=8)

    # 현재 session DocumentIndex에 merge (기존 ingest_external_chunks 재사용)
    pipeline = self._local_pipelines[workspace]
    pipeline.ingest_external_chunks(persistent_hits_as_virtual_chunks)

    return local_hits  # 기존 반환 타입 유지
```

### 3.5 도메인 오염 방지

**두 계층 방어**:

1. **primary**: `scope=MemoryScope.PROJECT`를 기본값으로. cross-project 활용은 `scope=GLOBAL`로 승격된 자료만.
2. **secondary**: retrieval 시 **semantic score threshold** (0.7 이상)만 채택. 무관한 도메인은 score가 낮아 자동 배제.

GLOBAL 승격 조건 (P3에서 구현):
- NotebookLM synthesis (weight 0.95)
- `verified=True` web references 중 관찰 빈도 N회 이상
- 사용자가 명시적으로 승격 (`/promote-memory`)

### 3.6 Staleness 정책

| source_type | TTL | 만료 시 동작 |
|-------------|-----|-----------|
| `web` | 90일 | retrieval에서 제외, nightly_tick에서 삭제 |
| `notebook_synthesis` | 프로젝트 lifetime | 프로젝트 완료 시 GLOBAL 승격 후 원본 삭제 |
| `local` | 파일 mtime 기반 | 원본 파일 변경 시 재인덱싱 |
| `llm_prior` | 30일 | 만료 시 제거 (LLM 모델 업데이트 시 stale) |

TTL 검사는 `facade.search_semantic()`의 `filter_expired` 파라미터로 이미 지원됨(`facade.py:208` "filtered %d expired records" 로그 존재).

---

## 4. Phase별 구현

### Phase 1: NotebookLM synthesis 청크화 (최우선)

**이유**: 체감 가치 가장 큼. 현재 plain text 문자열이 retrieval asset으로 전환됨.

**파일 변경**:
- `core/document_chunker.py`: `make_notebook_chunks(synthesis, task_input) -> list[VirtualChunk]` 추가
- `core/researcher.py:562` (`_collect_notebook_summary`): 반환 전에 `make_notebook_chunks()` 호출 + ephemeral pipeline에 ingest
- 아직 영속화 안 함 — P2에서 연결

**검증**: 청크가 retrieval에서 반환되는지 단위 테스트.

### Phase 2: 영속화 레이어 (persistent_rag 모듈)

**파일 신규**: `core/persistent_rag.py`

```python
class PersistentRAGStore:
    def __init__(self, facade: UnifiedMemoryFacade): ...
    async def ingest(self, chunks: list[VirtualChunk], project_id: str, scope=MemoryScope.PROJECT): ...
    async def query(self, task_input: str, project_id: str, *,
                    include_global: bool = True, limit: int = 10) -> list[VirtualChunk]: ...
    async def evict_expired(self): ...  # nightly_tick에서 호출
```

**파일 변경**:
- `core/researcher.py`: `collect_project_evidence()` 말미에 `PersistentRAGStore.ingest()` 호출
- `core/researcher.py:_collect_local_references`: `PersistentRAGStore.query()` 결과를 ephemeral pipeline에 병합
- `scripts/nightly_tick.py` (이미 존재): `evict_expired()` 추가

**Fallback**: facade가 unavailable하면 silently skip (현재 동작과 동일).

### Phase 3: cross-project 재사용 + GLOBAL 승격

**파일 변경**:
- `core/persistent_rag.py`: `promote_to_global(chunk_ids)` 메서드 추가
- `core/researcher.py:query()`: `include_global=True` 기본. 단 retrieval score threshold 0.7
- `core/project_pipeline.py`: 프로젝트 완료 시 NotebookLM synthesis 청크 자동 GLOBAL 승격

---

## 5. 함수 시그니처

```python
# core/document_chunker.py
def make_notebook_chunks(
    synthesis: str,
    task_input: str,
    *,
    max_chunk_chars: int = 800,
) -> list[VirtualChunk]: ...

# core/persistent_rag.py (신규)
class PersistentRAGStore:
    async def ingest(
        self,
        chunks: list[VirtualChunk],
        project_id: str,
        *,
        scope: MemoryScope = MemoryScope.PROJECT,
    ) -> int: ...  # 저장된 청크 수

    async def query(
        self,
        task_input: str,
        project_id: str,
        *,
        include_global: bool = True,
        limit: int = 10,
        min_score: float = 0.7,
    ) -> list[VirtualChunk]: ...

    async def evict_expired(self) -> int: ...  # 삭제된 청크 수
    async def promote_to_global(self, chunk_ids: list[str]) -> int: ...

# core/researcher.py — 기존 메서드 확장 (시그니처 유지)
# collect_project_evidence() 내부에서 rag_store 옵셔널로 주입
```

---

## 6. 코드 변경 파일 목록

| 파일 | 변경 | 라인 증감 예상 |
|------|-----|--------------|
| `core/document_chunker.py` | `make_notebook_chunks()` 추가 | +50 |
| `core/persistent_rag.py` | **신규** | +180 |
| `core/researcher.py` | ingest 호출 + query 병합 | +40 |
| `scripts/nightly_tick.py` | `evict_expired()` 주기 호출 | +10 |
| `tests/test_persistent_rag.py` | **신규** | +120 |
| `tests/test_document_chunker.py` | 노트북 청크 테스트 추가 | +30 |

**미수정**: `core/document_index.py` (ephemeral 계층 그대로 유지), `core/memory_system/facade.py` (기존 API로 충분).

---

## 7. Fallback / 호환성

### 7.1 UnifiedMemoryFacade 장애

- `PersistentRAGStore.ingest/query`는 예외를 삼키고 빈 결과 반환
- researcher는 기존 ephemeral DocumentIndex로 계속 동작
- 로그 레벨 WARNING으로 기록

### 7.2 embedding API 장애 (Gemini embeddings)

- `DocumentIndex`의 `_DenseIndex`는 이미 `_is_available` 플래그로 graceful degradation 구현됨
- Facade도 동일 패턴 유지 — dense 실패 시 sparse fallback

### 7.3 신규 프로젝트 (아직 영속 자료 없음)

- `query()`가 빈 리스트 반환 → 현재 동작과 동일 (Tavily fallback)

### 7.4 하위 호환

- `researcher.collect_project_evidence()` 시그니처 **변경 없음**
- `DocumentIndex` public API **변경 없음**
- 기존 테스트 모두 통과 (새 기능은 PersistentRAGStore가 주입되지 않으면 스킵)

---

## 8. Blast Radius

| 영향 대상 | 수준 | 설명 |
|---------|------|------|
| `core/researcher.py` | **Medium** | collect/query 경로에 옵셔널 분기 추가 |
| `core/document_chunker.py` | **Low** | 신규 함수만 추가 |
| `core/persistent_rag.py` | **신규** | 신규 파일 |
| `core/memory_system/facade.py` | **None** | 기존 API만 소비 |
| `scripts/nightly_tick.py` | **Low** | evict 주기 호출 추가 |
| 기존 LLM 문서 생성 파이프라인 | **None** | evidence 품질만 향상 |
| LLM 비용 | **Low (↓)** | 재실행 시 Tavily/Notebook 호출 감소 |
| Storage | **Medium** | Facade backend에 따라 disk/DB 증가. 프로젝트당 ~5-20MB 예상 |
| 테스트 | **Low** | 기존 테스트 영향 없음, 신규 단위 테스트 추가 |

---

## 9. KPI

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| Tavily 호출 감소율 | evidence 수집 로그에서 Tavily 스킵율 측정 | 3주 후 30%+ 감소 |
| 동일 도메인 재실행 시간 | `collect_project_evidence` latency 비교 | 40%+ 단축 |
| brief 품질 | `(edit required)` 개수, AC 수, EARS 표기율 | 현재 대비 저하 없음 (+ 개선 가능) |
| retrieval precision | unit test: 무관 도메인 쿼리에 대해 score<0.7 필터링 | 도메인 오염 0건 |
| facade storage 증가 | 디스크 사용량 주간 측정 | 프로젝트당 <50MB |

---

## 10. 교차검증 대상 항목 (설계 레벨 리스크)

1. **embedding 비용**: 프로젝트당 청크 100~200개 × 임베딩 호출 → 비용 추정 필요
2. **facade backend 적합성**: 현재 facade가 vector search 성능을 보장하는가? (chromadb 백엔드인지 확인)
3. **scope 오염**: PROJECT vs GLOBAL 경계를 런타임에서 어떻게 강제하는가?
4. **청크 ID 충돌**: 동일 URL이 다른 프로젝트에서 수집될 때 dedup 전략
5. **동시성**: `ingest()`가 에이전트 여러 개에서 호출될 때 race condition
6. **GLOBAL 승격 UX**: 사용자가 언제 어떻게 승격을 판단하는가? (자동 vs 수동)

---

## 11. 체크리스트

- [ ] 설계 교차검증 (af-critic + af-cross-review 병렬)
- [ ] Phase 1: `make_notebook_chunks()` 구현 + 단위 테스트
- [ ] Phase 1: `researcher._collect_notebook_summary` 연결
- [ ] Phase 2: `core/persistent_rag.py` 구현
- [ ] Phase 2: `researcher.collect_project_evidence` ingest 연결
- [ ] Phase 2: `researcher._collect_local_references` query 연결
- [ ] Phase 2: `nightly_tick.py`에 `evict_expired()` 연결
- [ ] Phase 3: `promote_to_global` + 프로젝트 완료 훅 연결
- [ ] KPI 측정 스크립트 (`scripts/rag_kpi_report.py`)
- [ ] `Master_Blueprint.md` §3/§10/§12 업데이트
- [ ] code-review.md 업데이트

---

## 12. 병행 가능한 준비 작업 (별도 트랙)

Codex 제안 — `RunBudget` per-agent 분리는 RAG와 독립적이므로 Week 1에 병행 가능. Paperclip 이식 준비 작업으로, 본 설계와는 별도 PR/설계문서로 분리.

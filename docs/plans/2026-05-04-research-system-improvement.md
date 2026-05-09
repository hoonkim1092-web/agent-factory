# Research 시스템 개선 플랜 (2026-05-04, v1)

> **Scope**: `core/research_router.py` + `core/researcher.py` 5개 결함 정정.
> **Out of scope**: research_verifier 4-metric 재설계, 신규 mode 추가, multi-provider 추상화.
> **검증 시나리오**: "8인 네트워크 포커게임 만들어줘" 자연어 입력.
> **검증 정책**: af-cross-review 본 라운드 생략 (사용자 결정). 자동 3-tier(test-runner/critic)는 정상 발화.

---

## §1. Goal / Non-goal

### Goal
8인 포커게임 시뮬레이션과 실제 코드 대조에서 발견한 5건 결함을 Phase 단위로 분리·픽스. 각 Phase는 독립 commit + 회귀 테스트 통과를 acceptance로 가진다.

### Non-goal
- 신규 ResearchGap enum 추가 (9종 잠금 유지 — `research_router.py:20-32`)
- ResearchRouter.detect_complexity_gaps의 max retry=1 제한 변경 (의도적 한계)
- 임베딩 기반 mode 분류 도입 (별도 spec 필요)
- Tavily 외 다중 provider 추상화 (G3는 fallback 1개만 추가)

---

## §2. 결함 목록 (5건, 메모리 v2 정정 반영)

| ID | 영역 | 위치 | 증상 | Severity |
|----|------|------|------|----------|
| G1 | Token 분류 | `research_router.py:132-169` 7개 frozenset | 한국어 자연어 일부 미매칭 ("최근", "8인", "공신력") | Med |
| G2 | Mode 분기 | `researcher.py:690-692` | `fast_synthesis`가 secondary `requires_web`를 무시하는 실 버그 | High |
| G3 | 외부 의존 | `researcher.py:311, 695, 701` | TAVILY_API_KEY 미설정 → 외부검색 SKIP, fallback 빈약 | High |
| G4 | 동시성 | `researcher.py:654 collect_project_evidence` | local→web→notebook→synthesize 순차 실행 | Med |
| G5 | LLM 보장 | `researcher.py:406-485 + tests/test_research_router_phase1b.py:140-211` | structured_evidence claim 0개 가능, 최소 보장 없음 | Med |

### v1 → v2 정정 footnote
- 메모리 v1의 "HIGH-3 detect_complexity_gaps 미호출 (dead code)" 주장은 **거짓**. 실제: `researcher.py:784`에서 호출, hint_gaps 기반 max 1 retry 정상 작동. 별도 결함 후보였던 "max retry=1 제한"은 의도적 설계로 본 플랜에서 다루지 않음.
- v1의 "MED-6 단위 테스트 부재"는 **부분 거짓**. `tests/test_research_router_phase1b.py:160-211`에 4건 존재(success/llm_failure/bad_json/research_mode_default). 본 플랜은 "claim 최소 개수 보장 부재"로 좁혀 G5에 재기술.

---

## §3. Phase 분할 (P0~P5)

| Phase | 결함 | 변경 파일 | Tier (예상) | 의존 |
|-------|------|----------|-------------|------|
| P0 | (없음) | `tests/test_research_system_regression.py` (신규) | T1 | — |
| P1 | G2 fast_synthesis secondary 무시 | `researcher.py:690-692` | T2~T3 | P0 |
| P2 | G1 토큰 보강 | `research_router.py:132-169` | T2 | P0 |
| P3 | G3 Tavily fallback | `researcher.py` 311/695/701 분기 | T3 | P0 |
| P4 | G5 claim 최소 보장 | `researcher.py:406-485` | T3 | P0 |
| P5 | G4 병렬화 | `researcher.py:654` collect_project_evidence | T3 | P1, P3 |

각 Phase는 **독립 commit + 자동 3-tier 통과**. P3의 변경 분기(`_collect_llm_prior_knowledge` 토글)는 G2 픽스(line 690-692 if-elif)와 코드 흐름이 직접 의존하지 않으므로 P0만 의존. P5는 web/local 양쪽 결과를 사용하므로 P1·P3 후 진입.

---

## §4. Phase 상세

### §4.1 Phase 0 — 회귀 baseline (T1)

**목적**: 5건 결함 모두에 대한 RED 테스트 사전 확립. 이후 Phase별 GREEN 전환을 acceptance로 사용.

**변경**
- `tests/test_research_system_regression.py` (신규)

**테스트 케이스** (전부 초기 RED 또는 baseline 캡처)
1. `test_g1_korean_freshness_token_match`: "최근 출시된 SDK" → `_FRESHNESS_TOKENS` 매칭 1+. 현재 fail (현재 토큰셋엔 "최신"만, "최근" 없음).
2. `test_g1_korean_player_count_match`: "8인 포커게임" → ResearchRouter.plan() mode가 deep_source_research 또는 fresh_lookup 분류. 현재 baseline 측정.
3. `test_g2_fast_synthesis_secondary_fresh_lookup`: ResearchPlan(mode="fast_synthesis", secondary_modes=["fresh_lookup"], requires_web=True) 입력 시 `collect_project_evidence`가 `_collect_web_references`를 호출. 현재 fail (line 690 if-pass).
4. `test_g3_tavily_unset_fallback_path`: TAVILY_API_KEY 미설정 monkeypatch + Claude WebSearch tool stub → web_refs 비어있지 않음. 현재 fail (현재는 `_collect_llm_prior_knowledge`로만 fallback).
5. `test_g4_evidence_parallel_runs_within_budget`: collect_project_evidence 호출 시간 측정 (mock latency). 현재 baseline (P5 후 절반 이하 목표).
6. `test_g5_claim_count_minimum_when_sources_present`: source_pack에 sources≥3 → result["source_backed_claims"] 길이 ≥ 1. 현재 baseline (LLM stub 따라 0~N 변동).
7. `test_g4_local_web_no_pipeline_race`: ThreadPoolExecutor로 `_collect_local_references` + `_collect_web_references`(또는 동등 mock 2개) 동시 2회 호출 시 virtual chunk 인덱스(`researcher.py:707-708` 캐싱 pipeline) 무결성 assert. 현재 직렬 흐름이라 trivially PASS — P5 진입 전 race 표면 사전 검증용. P5에서 동일 케이스가 GREEN 유지되어야 acceptance.

**Acceptance**
- 7개 테스트 모두 의도대로 fail/baseline 측정 또는 trivial PASS(case #7). 후속 Phase에서 하나씩 GREEN 전환.
- pytest 실행 시 collection 정상.

**Tier**: T1 (tests/만)
**Commit msg**: `test(research): P0 — 5건 결함 회귀 baseline 7개 케이스(race 사전포함)`

---

### §4.2 Phase 1 — G2 fast_synthesis secondary 픽스 (T2~T3)

**증상 재현**
```
mode == "fast_synthesis"
research_plan.secondary_modes == ["fresh_lookup"]
research_plan.requires_web == True   # ResearchPlan.for_mode() line 99-102가 secondary fresh_lookup → True 설정
```
현재 흐름 (`researcher.py:690-704`):
```python
if mode == "fast_synthesis":
    pass                     # ← elif 분기로 이행 안 함, requires_web=True 무시
elif research_plan.requires_web:
    ...                      # 도달 불가
elif not sufficient:
    ...
```

**변경**
```python
if mode == "fast_synthesis" and not research_plan.requires_web:
    pass
elif research_plan.requires_web:
    ...
```

**Acceptance**
- P0 `test_g2_fast_synthesis_secondary_fresh_lookup` GREEN.
- 기존 `test_research_router_modes.py` / `test_research_router_phase1b.py` 회귀 PASS.

**Risk**
- secondary fresh_lookup 추가로 API 호출 빈도 증가 가능. ResearchPlan.for_mode 정책이 의도한 결과이므로 정상.

**Tier**: scripts/blast_radius.py 분류 (`core/researcher.py` → 자동 T2~T3 가능). 자동 3-tier 발화 시 그대로 통과.

**Commit msg**: `fix(researcher): P1 G2 — fast_synthesis도 secondary requires_web이면 web 진입`

---

### §4.3 Phase 2 — G1 토큰 보강 (T2)

**현재 토큰셋 분석** (`research_router.py:132-169`)
- `_FRESHNESS_TOKENS`: "최신"은 있고 "최근"은 없음. 한국어 사용 빈도 비슷.
- `_OPERATIONAL_RISK_TOKENS`: "동시접속"은 있으나 "동시 접속"(공백) 변형 미처리.
- 메모리 v2에서 "8인", "공신력" 미존재 확인.

**변경 (data-only, 로직 유지)**
```python
_FRESHNESS_TOKENS = frozenset({
    ..., "최신", "최근", "릴리스", ...      # "최근" 추가
})

_DEEP_DECISION_TOKENS = frozenset({
    ..., "공신력", "권위 있는", ...           # 신뢰도 신호
})

_OPERATIONAL_RISK_TOKENS = frozenset({
    ..., "동시접속", "동시 접속", ...        # 띄어쓰기 변형
    "8인", "다인용", "멀티유저",              # 인원 신호
})
```
정확한 추가 셋은 P0의 baseline grep + 테스트 통과를 기준으로 결정. 임의 추가는 노이즈.

**Acceptance**
- P0 `test_g1_korean_freshness_token_match` GREEN.
- P0 `test_g1_korean_player_count_match` baseline → 분류 mode가 deep_source_research/fresh_lookup으로 안정.
- 기존 18케이스 `test_router_mode_distribution` 회귀 PASS (≥80% 정확도 유지).

**Risk**
- 토큰 과추가 시 분류 false positive(deep로 과도 escalation). 테스트로 제어.

**Tier**: T2.

**Commit msg**: `feat(research-router): P2 G1 — 한국어 토큰 누락 보강 + 띄어쓰기 변형`

---

### §4.4 Phase 3 — G3 Tavily fallback (T3)

**현재 흐름** (`researcher.py:311-318, 695-704`)
- TAVILY_API_KEY 미설정 → web_refs 빈 채로 LLM prior로 fallback.
- LLM prior는 사실성/citation_validity 점수에 기여하지 못함.

**변경 옵션** (Claude Code/Codex의 WebSearch tool 직접 호출은 AF runtime이 자식 프로세스 실행이므로 tool 위임 불가 — 비현실, 검토 제외)
1. **옵션 B**: `core/web_search.py`에 외부 검색 adapter 추가(DuckDuckGo HTML / Brave Search / Bing Search API 등). 외부 키 미설정 시 자동 사용.
2. **옵션 C**: TAVILY_API_KEY 미설정 시 명확한 사용자 경고 (현재 동작) + AF runtime 환경변수로 명시적 fallback 토글.

**채택 (P3)**: **옵션 C 1차, 옵션 B는 후속 Phase 분리.** 옵션 C는 저비용·안전(외부 adapter 없음).
- 신규 환경변수 `AF_RESEARCH_LLM_FALLBACK=1` 시 기존 `_collect_llm_prior_knowledge` 결과를 web_refs와 동일 weight로 evidence_summary에 포함 (citation_validity 점수 영향은 verifier 책임).
- TAVILY_API_KEY 미설정 + AF_RESEARCH_LLM_FALLBACK 미설정 시: 현재 동작(빈 web_refs + 경고 1회) 유지.

**Acceptance**
- P0 `test_g3_tavily_unset_fallback_path` GREEN (LLM prior가 web_refs 슬롯에 들어가는 경로 검증).
- TAVILY_API_KEY 설정 환경에서 기존 동작 회귀 없음.
- `core/research_verifier.py` 4-metric 점수 변화 추적 (별도 측정만, 기준 미변경).

**Risk**
- LLM prior를 web_refs로 취급 시 citation_validity 점수 noise 증가. verifier 4-metric 임계 재조정은 별도 spec.
- 옵션 B(외부 검색 adapter)는 별도 spec — 본 Phase 미포함.

**Tier**: T3 (외부 의존 변경).

**Commit msg**: `feat(researcher): P3 G3 — TAVILY 미설정 시 LLM prior fallback 토글`

---

### §4.5 Phase 4 — G5 claim 최소 보장 (T3)

**현재 흐름** (`researcher.py:406-485`)
- LLM 호출 → JSON 파싱. 실패 시 `_FALLBACK` 빈 배열.
- source_pack에 sources≥3여도 `source_backed_claims`가 0개 가능.

**변경**
- LLM prompt에 명시적 룰 추가: "If sources>=3, include at least min(N_sources, 3) source_backed_claims unless none are factually supported."
- LLM 응답에서 `source_backed_claims` 길이가 0이고 sources>=3일 때 1회 retry (다른 prompt). retry 후에도 0이면 fallback 유지.

**의사 코드**
```python
def _synthesize_structured_evidence(...):
    result = _call_llm(prompt)
    if (
        len(source_pack.get("sources", [])) >= 3
        and len(result.get("source_backed_claims") or []) == 0
    ):
        retry_prompt = prompt + "\n\nNote: previous response had no claims. Provide at least 1."
        result = _call_llm(retry_prompt)
    return result
```

**Acceptance**
- P0 `test_g5_claim_count_minimum_when_sources_present` GREEN.
- 기존 `test_research_router_phase1b.py:160-211` 4건 회귀 PASS.
- 신규 테스트: source 0개 → fallback empty 유지 (현재 동작).

**Risk**
- LLM retry 비용 1회 추가. 빈도 측정 후 임계 조정.
- prompt 강화로 false claim 생성 가능성. claims는 source_ids 명시 필수이므로 verifier가 사후 검증.

**Tier**: T3 (LLM 동작 변경).

**Commit msg**: `feat(researcher): P4 G5 — sources>=3 시 source_backed_claims 1회 retry`

---

### §4.6 Phase 5 — G4 병렬화 (T3)

**현재 흐름** (`researcher.py:654-796 collect_project_evidence`)
1. workspace_notes
2. local_refs (line 682)
3. sufficiency gate
4. web_refs / llm_prior_refs (line 695-704)
5. virtual chunk indexing
6. notebook (Tavily extract)
7. structured_evidence synthesis
8. detect_complexity_gaps + retry

**병렬 가능 단위 분석**
- (2)(4) local + web: **독립**, 병렬 가능.
- (5) virtual chunk indexing: (2)(4) 결과 의존 — 직렬 유지.
- (6) notebook: (4) web 결과 의존성 약함, 검토 필요. 보수적으로 직렬 유지.
- (7) synthesis: source_pack 빌드 후 — 직렬 유지.

**변경**
- (2)(4)만 `concurrent.futures.ThreadPoolExecutor(max_workers=2)`로 병렬화.
- 예외는 future.result() 시점에 수집, 한쪽 실패해도 다른 결과 사용.

**Acceptance**
- P0 `test_g4_evidence_parallel_runs_within_budget`: mock latency local=2s, web=2s 시 총 시간 < 3.5s (직렬 4s+ 대비 단축).
- P0 `test_g4_local_web_no_pipeline_race` GREEN 유지 (P0 trivial PASS → P5 적용 후에도 PASS 필수). race 발견 시 P5 rollback.
- 기존 `test_research_router_phase1b.py` / `test_research_router_modes.py` 회귀 PASS.

**Risk**
- 모듈 캐시(예: virtual chunk indexing이 의존하는 `_collect_local_references`의 pipeline 객체)가 thread-safe하지 않을 가능성. P5 진입 전 단위 테스트로 사전 검증.
- `_collect_web_references` 내부 Tavily client가 thread-safe인지 확인.

**Tier**: T3 (race condition 위험).

**Commit msg**: `perf(researcher): P5 G4 — local/web evidence 수집 ThreadPoolExecutor 병렬화`

---

## §5. 회귀 시나리오 — 8인 포커게임

각 Phase 완료 후 수동 검증 (자동 테스트와 별개):

```python
from core.research_router import ResearchRouter
plan = ResearchRouter().plan("8인 네트워크 포커게임 만들어줘. 동시 접속, 최근 보안 권장사항 반영")
assert plan.mode in ("deep_source_research", "fresh_lookup")
assert plan.requires_web
```

**P0 측정**: 현재 mode 분류 결과 + scores 캡처.
**P2 (G1) 후**: "최근", "8인", "동시 접속" 매칭으로 점수 증가 확인.
**P5 (G4) 후**: 직렬 baseline 대비 latency 30%+ 단축 (mock 측정).

---

## §6. Risk & Rollback

### 공통 Risk
- **fast_synthesis API 호출 빈도 증가** (P1 G2): secondary fresh_lookup 트리거가 빈번하면 비용 상승. P0 baseline에서 빈도 측정 후 결정.
- **토큰 과추가 노이즈** (P2 G1): 18케이스 정확도 80% 임계 위반 시 P2 미반영.
- **LLM retry 비용** (P4 G5): 1회 retry 가정. 통과율 측정 후 retry 횟수 조정.

### Rollback
- 각 Phase는 독립 commit이므로 `git revert <hash>` 가능.
- P5(병렬화)만 race condition 의심 시 rollback 우선순위 높음.
- 환경변수 `AF_RESEARCH_LLM_FALLBACK`(P3), `AF_RESEARCH_PARALLEL=0`(P5)로 런타임 비활성화 옵션 검토.

---

## §7. 외부 변경 영향 (Master_Blueprint 동기화)

| Phase | Blueprint 섹션 |
|-------|---------------|
| P0 | §0 빠른 참조 (tests 신규) |
| P1, P3, P4, P5 | §3 researcher 서브시스템 + last_updated |
| P2 | §3 research_router + last_updated |
| 전체 | §12 변경 이력 (5건 commit hash 추가) |

각 Phase commit에 Blueprint 동기화 포함 (CLAUDE.md 정책).

---

## §8. 작업 순서 및 명령

```bash
# Phase 0
git add tests/test_research_system_regression.py Master_Blueprint.md
git commit -m "test(research): P0 — 5건 결함 회귀 baseline 6개 케이스"

# Phase 1 (G2 — 1줄 수정 + 회귀 GREEN)
# ... 자동 3-tier 발화 → PASS 시 commit
# Phase 2~5 동일 패턴
```

각 Phase commit 직후 자동 3-tier가 발화한다. BLOCK 시 정정 후 재발화. WARN-only는 advisory(자동 수정 의무 없음).

**Phase 1 진입 권장**: 다음 세션 작업 즉시 P0부터.

---

## §9. 변경 이력

| 일자 | 버전 | 변경 |
|------|------|------|
| 2026-05-04 | v1 | 최초 작성 (af-cross-review 본 라운드 생략, 사용자 결정) |
| 2026-05-04 | v2 | af-doc-qa WARN 3건 정정 — W1(§4.4 옵션 A 자기모순 제거) / W2(§4.1 P0 case #7 race 사전 추가, §4.6 Acceptance에 GREEN 유지 명시) / W3(§3 P3 의존을 P0 단독으로) |

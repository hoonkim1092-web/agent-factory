# Research Router + Structured Evidence 설계

> 날짜: 2026-04-29 (최초), 2026-05-01 (v1.1), 2026-05-02 (v1.2 갱신)
> 상태: 설계 v1.2 (af-cross-review BLOCK 4건 반영)
> 대상 파일: `core/project_pipeline.py`, `core/researcher.py`, `core/web_search.py`, `core/research_verifier.py`, `core/work_item_generator.py`, `core/project_task_board.py`, **`core/research_router.py` (신규)**, `af.spec`
> 적용 원칙: 1차 적용은 `Research Router -> mode별 리서치 -> structured evidence -> project_brief`까지로 제한한다. 이후 `role_plan`, `task_board`, `work-item docs`, `skill reuse/enhance/forge`는 기존 파이프라인을 그대로 탄다.

## 0. 파일 책임 분리 (v1.1 추가)

`core/retrieval_router.py`(기존)와 `core/research_router.py`(신규)는 이름이 비슷하지만 책임이 완전히 다르다. 같은 파일에 합치지 않는다.

| 파일 | 책임 | 입력 → 출력 |
|------|------|------|
| `core/retrieval_router.py` (기존) | local retrieval 전략 선택 | query → BM25 / dense / hybrid strategy |
| `core/research_router.py` (신규) | project research mode 결정 | request → fast / fresh / archive / deep / live mode + secondary |

`research_router.py`는 다음 두 책임을 한 파일에 둔다.

1. `plan(request) -> ResearchPlan` — 요청을 mode로 분류
2. `detect_complexity_gaps(request, evidence, final_mode) -> list[ResearchGap]` — 수집된 evidence가 요청의 complexity obligation을 충족하는지 검사 (Phase 1a lightweight detector)

두 함수는 동일한 `_compute_signal_scores(request)`를 공유한다 (signal drift 방지).

## 1. 문제 정의

### 1.1 현재 파이프라인

현재 `ProjectPipeline.prepare_brief()`의 리서치 흐름은 다음과 같다.

```text
사용자 요청
-> ProjectPipeline.prepare_brief()
-> Himari.collect_project_evidence()
-> local references 수집
-> local 근거가 부족하면 Tavily 검색
-> risk_level normal 이상이면 NotebookLM 질의
-> ResearchVerifier.verify_with_retry()
-> Himari.research_project_brief()
-> project_brief.json
-> 기존 role_plan / task_board / docs / skill pipeline
```

핵심 구현 위치:

| 영역 | 파일 | 현재 역할 |
|------|------|-----------|
| Phase 1 진입 | `core/project_pipeline.py` | evidence 수집 후 brief 생성 |
| evidence 수집 | `core/researcher.py` | local/web/NotebookLM 요약 수집 |
| 웹 검색 | `core/web_search.py` | Tavily Search 결과 반환 |
| NotebookLM 질의 | `core/research_engine.py` | archive 노트북 기본 질의 |
| evidence 검증 | `core/research_verifier.py` | reference 존재 여부 중심 점수화 |
| 문서 생성 | `core/work_item_generator.py`, `core/project_task_board.py` | `project_brief` 기반 산출물 생성 |

### 1.2 현재 구조의 한계

현재 구조는 요청의 성격이 달라도 거의 같은 리서치 경로를 사용한다.

```text
모든 요청
-> local 검색
-> 부족하면 Tavily snippet
-> NotebookLM 요약 시도
-> project_brief 생성
```

이 방식은 두 방향 모두에서 비효율이 생긴다.

1. 단순 요청에는 외부 리서치가 과하다.
   - 예: "간단한 todo 웹앱 만들어줘"
   - Tavily/NotebookLM 없이 local RAG + skill registry + LLM synthesis로 충분하다.

2. 복잡한 요청에는 리서치가 얕다.
   - 예: "8인 서버 권위형 네트워크 포커 웹앱 만들어줘"
   - 실시간 네트워크, room/session, reconnect, state machine, multi-client test까지 분해해야 하지만 현재 evidence는 snippet 중심이다.

3. Tavily 결과가 리서치 자산으로 충분히 보존되지 않는다.
   - `core/web_search.py`에서 `content`가 500자로 잘린다.
   - `core/researcher.py`에서 다시 260자 excerpt로 줄어든다.
   - UI 표시용 excerpt와 분석용 원문이 분리되어 있지 않다.

4. NotebookLM이 강점과 다른 방식으로 호출된다.
   - 현재 evidence 경로는 `query_notebooklm(prompt)`만 호출한다.
   - `notebook_id`를 넘기지 않으므로 archive 노트북으로 질의한다.
   - Tavily가 방금 찾은 URL은 NotebookLM 소스로 주입되지 않는다.
   - 결과적으로 "장문 다중 소스 분석"이 아니라 "짧은 snippet 재요약"에 가깝다.

5. verifier가 도구 호출 여부에 점수를 준다.
   - `notebook_summary`가 존재하면 점수를 받는다.
   - 실제로 task에 도움이 됐는지, 기술스택/스킬/검증 계획에 반영됐는지는 보지 않는다.

## 2. 설계 목표

1. 요청별 리서치 모드를 먼저 결정한다.
2. 단순 요청은 빠르게 처리하고, 복잡한 요청에만 비싼 리서치를 사용한다.
3. Tavily는 최신 웹 소스 수집/원문 확보 계층으로 사용한다.
4. NotebookLM은 archive 또는 deep source research에서만 사용한다.
5. LLM은 리서치 결과를 파이프라인이 소비 가능한 구조화 evidence로 정규화한다.
6. 1차 적용에서는 뒤 파이프라인을 유지한다.
7. 2차 적용에서 뒤 파이프라인이 새 evidence 필드를 더 적극적으로 쓰도록 확장한다.

## 3. 목표 아키텍처

### 3.1 Phase 1 적용 범위

1차 적용은 다음 구간만 바꾼다.

```text
사용자 요청
-> Research Router
-> mode별 리서치
-> source_pack
-> structured_evidence
-> project_brief
```

그 뒤는 기존 파이프라인을 그대로 사용한다.

```text
project_brief
-> role_plan
-> task_board
-> work-item docs
-> skill install / reuse / forge
-> execution 준비
```

### 3.2 전체 흐름 (v1.1)

```text
User Request
-> ProjectPipeline.prepare_brief()
-> ResearchRouter.plan()                              # mode 결정
-> Himari.collect_project_evidence(mode-aware)        # mode별 Tavily/NotebookLM gating
-> ResearchRouter.detect_complexity_gaps()            # Phase 1a lightweight detector
   -> if gap detected: escalation (max retry=1, gap-driven direct-jump)
   -> re-collect evidence with upgraded mode
-> ResearchVerifier.verify()                          # Phase 1b부터: deterministic 4-metric
-> Himari.synthesize_structured_evidence()            # Phase 1b부터
-> Himari.research_project_brief()
-> 기존 prepare_documents()
-> 기존 role/task/docs/skill pipeline
```

**Phase 1a 단계**에서 `synthesize_structured_evidence()`는 fresh/deep/archive 모드에서만 호출된다. fast 모드는 기존 `research_project_brief()` LLM 호출에 합쳐 LLM 호출 횟수를 1회로 유지한다.

### 3.3 도구 역할 분리

| 도구 | 역할 | 기본 호출 여부 |
|------|------|----------------|
| Local RAG | 현재 프로젝트의 진실. 코드, 문서, 기존 work-item, memory 기반 | 항상 |
| Skill Registry | 실행 가능한 capability 후보 탐색 | 항상 |
| Tavily | 최신 웹 소스 검색, 공식 문서 탐색, 원문 추출 | 모드 기반 |
| NotebookLM archive | 사용자가 축적한 archive 지식 질의 | archive 관련 시 |
| NotebookLM source injection | 긴 소스 묶음의 다중 문서 분석 | deep research 시 |
| LLM | capability 추출, evidence 정규화, project_brief 생성 | 항상 |
| Verifier | 근거 품질, 실행 가능성, skill gap 품질 검증 | 항상 |

## 4. Research Mode

### 4.1 모드 목록

| 모드 | 대상 요청 | Tavily | NotebookLM | 핵심 산출 |
|------|-----------|--------|------------|-----------|
| `fast_synthesis` | 단순 앱, CRUD, 작은 UI, 명확한 구현 | OFF | OFF | 빠른 `project_brief` |
| `fresh_lookup` | 최신 버전, API, SDK, 가격, 보안, 라이선스 | ON | 기본 OFF | 최신 근거 기반 기술 판단 |
| `archive_research` | 기존 archive 자료 기반 판단 | 필요 시 | archive ON | 사용자 자료 기반 insight |
| `deep_source_research` | 아키텍처 비교, 기술스택 선택, 고위험 설계 | ON | source injection ON | 다중 소스 deep synthesis |
| `live_project_analysis` | 운영 중인 대규모 코드베이스 분석/유지보수 | 제한적 ON | 필요 시 | 영향 범위, migration, regression |
| `skill_evolution` | 스킬 재사용/보강/생성/등록 판단 | 필요 시 | 기본 OFF | reuse/enhance/forge 후보 |

`skill_evolution`은 독립 모드라기보다 대부분의 모드 뒤에 붙는 후속 분석으로 취급한다.

### 4.2 모드 판정 기준

`ResearchRouter`는 다음 신호를 점수화한다.

```text
freshness_score:
  latest, current, 2026, 최신, 버전, 릴리스, 가격, 보안

external_stack_score:
  websocket, sdk, api, framework, redis, deployment, browser, mobile

operational_risk_score:
  realtime, multiplayer, network, scheduler, payment, auth, scaling, migration

data_pipeline_score:
  수집, 누적, 통계, 분석, 주기적 업데이트, 데이터베이스

live_project_score:
  현재 프로젝트, 유지보수, 리팩터링, 영향 범위, 회귀 테스트

deep_decision_score:
  비교, trade-off, architecture, 기술스택 선택, 고위험 결정

archive_score:
  기존 자료, 내 노트북, archive, 과거 설계, 회사 문서
```

예시 판정:

| 요청 | 판정 |
|------|------|
| "todo 웹앱 만들어줘" | `fast_synthesis` |
| "최신 Next.js 기준으로 SaaS starter 만들어줘" | `fresh_lookup` |
| "우리 기존 설계 문서 기준으로 인증 구조 검토해줘" | `archive_research` |
| "8인 풀네트워크 포커 웹앱 만들어줘" | `deep_source_research` + `skill_evolution` |
| "로또 800회차 데이터를 수집하고 매주 통계를 누적하는 웹앱 만들어줘" | `fresh_lookup` + `data_pipeline` + `skill_evolution` |
| "라이브 프로젝트 인증 모듈 리팩터링해줘" | `live_project_analysis` + `skill_evolution` |

### 4.2.1 Mode 선택 알고리즘 `_select_mode` (v1.2 추가)

`plan()`이 호출하는 `_select_mode(scores)`의 결정 규칙을 명시한다. 의사코드만 두면 fixture(§12.5) calibration이 trial-error 루프가 되므로 v1.2 진입 시점에 초기치를 잠근다. 임계는 §12.5 fixture 결과로만 calibration 가능 (코드 임의 수정 금지).

```text
def _select_mode(scores) -> ResearchPlan:

    # 1) Primary mode 결정 (precedence 순, 첫 매칭에서 종료)
    if scores["archive_score"] >= 2:
        primary = "archive_research"
    elif scores["live_project_score"] >= 2:
        primary = "live_project_analysis"
    elif scores["deep_decision_score"] >= 2 or scores["operational_risk_score"] >= 3:
        primary = "deep_source_research"
    elif scores["freshness_score"] >= 2:
        primary = "fresh_lookup"
    else:
        primary = "fast_synthesis"

    # 2) Secondary modes (primary 외에 부착)
    secondary = []
    if scores["data_pipeline_score"] >= 1 and primary != "data_pipeline":
        secondary.append("data_pipeline")
    if scores["external_stack_score"] >= 2 and primary == "fast_synthesis":
        secondary.append("fresh_lookup")  # primary 승격은 안 함 (보조 fetch만)
    # skill_evolution은 §4.1 정책상 대부분의 모드 뒤에 부착되는 후속 분석.
    # 별도 정책 (capability gap 존재 시 무조건 부착)으로 후속 단계에서 결정.

    return ResearchPlan(mode=primary, secondary_modes=secondary, scores=scores)
```

**Precedence 의도**:
- `archive_score`가 가장 먼저 — "내 자료/우리 기존" 같은 명시적 archive 신호는 mode를 강제한다.
- `live_project_score`는 운영 중 코드베이스 분석 신호 — 외부 리서치보다 우선.
- `deep > fresh` — 고위험/아키텍처 결정은 fresh보다 먼저 매칭 (단순 freshness만으로는 deep을 못 트리거함).
- `operational_risk_score >= 3`은 deep로 분류 — `realtime/multiplayer/scaling/payment` 등 고위험 키워드 다수 동시 발화 시.

**임계값 v1.2 초기치**:

| 점수 키 | Primary 트리거 임계 | 비고 |
|---------|---------------------|------|
| `archive_score` | >= 2 | 매칭 시 즉시 archive_research 확정 |
| `live_project_score` | >= 2 | archive 다음 우선 |
| `deep_decision_score` | >= 2 | OR 조건으로 deep 트리거 |
| `operational_risk_score` | >= 3 | deep 트리거 (단독) |
| `freshness_score` | >= 2 | primary fresh_lookup 트리거 |
| `external_stack_score` | >= 2 | secondary fresh_lookup 부착 (primary=fast일 때만) |
| `data_pipeline_score` | >= 1 | secondary data_pipeline 부착 |

§12.5 Phase 1a fixture (15~20건)에서 expected_mode 정확도 ≥ 80% 미달 시 위 임계를 fixture 기반으로 재calibration. 코드 직접 튜닝 금지 — 항상 fixture 라벨 추가/수정 후 측정.

### 4.3 Phase별 Deep capability level (v1.1 추가)

`deep_source_research` 모드는 단계에 따라 capability level이 다르다. 같은 mode 이름이지만 의미가 다르므로 diagnostics에 명시한다.

| Phase | deep_capability_level | Tavily Extract | NotebookLM source injection |
|-------|----------------------|----------------|------------------------------|
| Phase 1a~2 | `lite` | ON | OFF (Phase 3까지) |
| Phase 3+ | `full` | ON | ON (임시 노트북 + cleanup) |

이 표기를 빼면 "deep으로 점프했는데 왜 NotebookLM 안 부르냐"는 혼동이 발생한다.

### 4.4 Escalation rule (v1.1 추가)

router 오판을 1회 retry 안에서 정정하기 위한 규칙.

#### 4.4.1 횟수와 폭

```
max retry = 1회
mode jump = gap에 따라 direct (인접 강제 없음)
```

`fast → deep` 직접 점프 가능. retry 횟수는 1회로 제한해 비용 상한 보장.

#### 4.4.2 Gap-to-mode 매핑

```
fresh-tier gap → fresh_lookup
  - NO_EXTERNAL_EVIDENCE
  - FRESHNESS_REQUIRED_MISSING
  - OFFICIAL_SOURCE_MISSING

deep-tier gap → deep_source_research (Phase 1a에서는 deep-lite)
  - ARCHITECTURE_COVERAGE_LOW
  - HIGH_RISK_CAPABILITY_MISSING
  - MULTI_CLIENT_MISSING

quality-tier gap → unclassified (mode jump 없음, Phase 1b verifier 내부 retry)
  - CITATION_VALIDITY_LOW
  - CLAIM_SOURCE_RATIO_LOW
  - SOURCE_PACK_TOO_SHALLOW
```

매핑은 `core/research_router.py`에 둔다 (verifier 아님). enum 추가 시 본 표도 함께 갱신 (§6.5 규칙).

#### 4.4.3 Precedence

```
deep > fresh > unclassified
```

다중 gap 동시 emit 시 deep-tier 하나라도 있으면 deep로 직진. fresh-tier만 있으면 fresh로. 매핑 안 되는 gap은 1-step 인접 fallback.

#### 4.4.4 Deep gap emission threshold

약한 신호로 deep direct-jump가 트리거되지 않도록 다음 조건 동시 만족 시에만 deep-tier gap을 emit한다.

```
1. signal score 임계 충족
   - operational_risk_score >= 3 또는
   - deep_decision_score >= 2 또는
   - external_stack_score >= 3

2. final_mode가 fast_synthesis 또는 fresh_lookup
   (이미 deep로 분류됐다면 escalation 자기 반복이므로 emit 안 함)

3. 수집된 evidence가 해당 obligation을 미충족
   (web_refs 없음, source_pack 없음 등)
```

요청 길이는 보조 신호일 뿐. capability token 수가 1차. (한국어 짧은 요청에 복잡도가 숨어 있을 수 있음)

#### 4.4.5 Detector 정책 분리

router의 `plan()`과 detector의 `detect_complexity_gaps()`는 동일 signal을 공유하되 정책은 다르다.

```python
# router.plan(): signal -> mode
def plan(request):
    scores = self._compute_signal_scores(request)
    return self._select_mode(scores)

# router.detect_complexity_gaps(): signal x final_mode x evidence -> gap
def detect_complexity_gaps(request, evidence, final_mode):
    scores = self._compute_signal_scores(request)
    gaps = []
    if (scores["operational_risk_score"] >= 3
        and final_mode in ("fast_synthesis", "fresh_lookup")  # §4.4.4 본문과 일치
        and not evidence.get("web_refs")):
        gaps.append(ResearchGap.MULTI_CLIENT_MISSING)
    return gaps
```

이렇게 해야 "router 자기 반복"이 아니라 "수집 결과와 complexity obligation의 불일치 감지"가 된다.

## 5. Mode별 흐름

### 5.1 fast_synthesis

대상:

```text
- 작은 기능 구현
- 단순 웹앱
- CRUD
- 명확한 기술스택
- 최신 외부 정보가 중요하지 않은 작업
```

흐름:

```text
1. local docs/code 검색
2. memory/feedback 조회
3. skill registry 검색
4. LLM structured evidence 생성
5. project_brief 생성
6. 기존 뒤 파이프라인 실행
```

도구:

```text
Tavily: OFF
NotebookLM: OFF
LLM: ON
Local RAG: ON
Skill Registry: ON
```

### 5.2 fresh_lookup

대상:

```text
- 최신 프레임워크/API/SDK
- 외부 라이브러리 선택
- 가격/라이선스
- 보안/릴리스
- 공식 데이터 출처 확인
```

흐름:

```text
1. local/docs/skill registry 검색
2. Tavily Search로 후보 URL 수집
3. 공식 문서/권위 소스 우선 선별
4. Tavily Extract로 원문 확보
5. source_pack 생성
6. LLM structured evidence 생성
7. project_brief 생성
```

도구:

```text
Tavily Search: ON
Tavily Extract: ON
Tavily Crawl/Map: 필요 시
NotebookLM: 기본 OFF
LLM: ON
```

### 5.3 archive_research

대상:

```text
- 사용자가 축적한 archive 자료 기반 판단
- "우리 기존 기준", "내 자료", "과거 설계"가 중요한 요청
```

흐름:

```text
1. local/docs/memory 검색
2. archive relevance 판정
3. NotebookLM archive 질의
4. LLM normalizer로 structured evidence 변환
5. project_brief 생성
```

도구:

```text
Tavily: 필요 시
NotebookLM archive: ON
NotebookLM source injection: OFF
LLM: ON
```

### 5.4 deep_source_research

대상:

```text
- 아키텍처 비교
- 기술스택 선택
- 고위험 설계
- 긴 문서 여러 개 비교
- 나중에 재사용할 리서치 보고서가 필요한 요청
```

흐름:

```text
1. local/docs/code/memory 검색
2. Tavily Search로 후보 소스 수집
3. Tavily Extract/Crawl로 원문 확보
4. source_pack 생성
5. 임시 NotebookLM 노트북 생성
6. URL/text 주입
7. NotebookLM deep synthesis
8. LLM normalizer로 JSON evidence 변환
9. project_brief 생성
10. 리서치 로그 저장
```

도구:

```text
Tavily Search: ON
Tavily Extract/Crawl: ON
NotebookLM source injection: ON
LLM normalizer: ON
```

주의:

```text
- 짧은 snippet만 NotebookLM에 보내는 경로는 제거한다.
- 임시 노트북은 질의 후 삭제하거나 TTL 캐시한다.
- 1차 구현에서는 deep_source_research를 opt-in 또는 high-risk에서만 켠다.
```

### 5.5 live_project_analysis

대상:

```text
- 운영 중인 대규모 프로젝트 분석
- 유지보수/업데이트
- 변경 영향 분석
- migration plan
- 회귀 테스트 설계
```

흐름:

```text
1. repo inventory 생성
2. architecture/docs/code index 구축
3. 관련 모듈/파일/테스트 탐색
4. memory/previous incidents/feedback 조회
5. 외부 의존성만 Tavily로 최신성 확인
6. 영향 범위 분석
7. migration/update plan 생성
8. regression matrix 생성
9. project_brief 생성
```

도구:

```text
Local RAG: 강하게 ON
Code search: ON
Memory: ON
Skill Registry: ON
Tavily: 외부 의존성/버전 확인용
NotebookLM: 큰 설계 문서 묶음 분석 시만
LLM: ON
```

## 6. 데이터 구조

### 6.1 research_plan

`collect_project_evidence()` 시작 시 생성한다.

```json
{
  "mode": "fast_synthesis",
  "secondary_modes": ["skill_evolution"],
  "reason": "No current external dependency or deep architecture decision required.",
  "requires_web": false,
  "requires_tavily_extract": false,
  "requires_notebooklm": false,
  "requires_deep_source_pack": false,
  "risk_level": "normal"
}
```

### 6.2 source_pack

Tavily, local RAG, memory, NotebookLM 결과를 공통 소스 형식으로 정규화한다.

```json
{
  "sources": [
    {
      "source_id": "web_001",
      "source_type": "web",
      "retrieval_method": "tavily_search|tavily_extract|tavily_crawl|local_rag|memory|notebooklm",
      "url": "https://example.com/docs",
      "title": "Official Docs",
      "excerpt": "display-safe short text",
      "content_full": "analysis text",
      "authority_level": "primary",
      "relevance_score": 0.82,
      "selected_reason": "official framework documentation"
    }
  ]
}
```

### 6.3 structured_evidence

LLM normalizer가 생성하는 핵심 산출물이다.

```json
{
  "research_mode": "fresh_lookup",
  "goal_interpretation": "Build a responsive lottery statistics web app with scheduled official draw ingestion.",
  "recommended_architecture": "scheduled_data_ingestion_plus_statistics_dashboard",
  "recommended_tech_stack": [],
  "required_capabilities": [],
  "agent_role_hints": [],
  "skill_gap_hypotheses": [
    {
      "need_skill_id": "lottery_statistics_engine",
      "required_capabilities": [
        "draw_frequency_analysis",
        "pair_frequency_analysis",
        "recommendation_generation"
      ],
      "reuse_expectation": "forge",
      "reason": "Domain-specific lottery statistics capability is not covered by generic data visualization."
    }
  ],
  "risks": [],
  "verification_focus": [],
  "maintenance_strategy": [],
  "source_backed_claims": [
    {
      "claim": "Official draw results must be fetched from a current source.",
      "source_ids": ["web_001"]
    }
  ]
}
```

### 6.4 project_brief 확장 필드

기존 필드는 유지하고, 새 필드를 optional로 추가한다.

```json
{
  "goal": "...",
  "background_context": "...",
  "problem_statement": "...",
  "constraints": [],
  "required_skills": [],
  "role_hints": [],
  "deliverables": [],
  "risks": [],
  "research_notes": [],
  "tech_stack": [],
  "architecture_style": "...",

  "research_mode": "fresh_lookup",
  "recommended_architecture": "...",
  "recommended_tech_stack": [],
  "required_capabilities": [],
  "skill_gap_hypotheses": [],
  "verification_focus": [],
  "maintenance_strategy": [],
  "source_backed_claims": []
}
```

하위 호환:

```text
- 기존 뒤 파이프라인은 기존 필드만 읽어도 동작한다.
- Phase 2에서 새 필드를 읽도록 점진 확장한다.
```

### 6.5 ResearchGap enum (v1.2 — 9개로 확장)

Phase 1a detector와 Phase 1b verifier가 같은 gap 이름을 써야 diagnostics가 단계 간 끊기지 않는다. v1.1에서는 6개로 잠갔으나, Phase 1b deterministic 4-metric (§9.2)이 emit할 gap이 매핑되지 않는 충돌이 있었다. v1.2에서는 9개로 확장하여 1a/1b 모두를 사전 등록한다 (Phase 1b 활성화 시 enum 추가 PR 불필요).

```python
# core/research_router.py
from enum import Enum

class ResearchGap(str, Enum):
    # fresh-tier (Phase 1a verifier emit)
    NO_EXTERNAL_EVIDENCE = "no_external_evidence"
    FRESHNESS_REQUIRED_MISSING = "freshness_required_missing"
    OFFICIAL_SOURCE_MISSING = "official_source_missing"
    # deep-tier (Phase 1a router detector emit)
    ARCHITECTURE_COVERAGE_LOW = "architecture_coverage_low"
    HIGH_RISK_CAPABILITY_MISSING = "high_risk_capability_missing"
    MULTI_CLIENT_MISSING = "multi_client_or_distributed_system_missing"
    # quality-tier (Phase 1b verifier emit — 사전 등록, 1a에서는 미사용)
    CITATION_VALIDITY_LOW = "citation_validity_low"
    CLAIM_SOURCE_RATIO_LOW = "claim_source_ratio_low"
    SOURCE_PACK_TOO_SHALLOW = "source_pack_too_shallow"
```

규칙:

```text
- "잠금"의 의미: 기존 gap 이름과 §4.4.2 gap-to-mode 매핑은 변경 금지
  (mode_distance 데이터 연속성, fixture 라벨 호환성 보장).
- enum에 새 gap 추가는 가능. 단, 추가 시:
  1. §4.4.2 gap-to-mode 매핑 표를 같은 PR에서 갱신해야 한다.
  2. 추가 gap의 tier(fresh/deep/quality/unclassified)를 §4.4.3 precedence에
     명시해야 한다 (precedence 미정의 gap은 1-step 인접 fallback 처리).
- Phase 1b verifier는 새 gap 이름을 만들지 말고 위 enum의 quality-tier 3종
  (CITATION_VALIDITY_LOW / CLAIM_SOURCE_RATIO_LOW / SOURCE_PACK_TOO_SHALLOW)을 사용한다.
```

**Quality-tier gap의 §4.4.2 매핑** (v1.2 등록):

```
quality-tier gap → unclassified (mode jump 없음, verifier가 자체 retry로 처리)
  - CITATION_VALIDITY_LOW
  - CLAIM_SOURCE_RATIO_LOW
  - SOURCE_PACK_TOO_SHALLOW
```

quality-tier는 mode 자체의 문제가 아니라 LLM normalizer 출력 품질 문제이므로 mode jump보다는 verifier 내부 retry (Phase 1b에서 정의)가 맞다. mode jump 트리거하지 않음.

### 6.6 Diagnostics 진단 필드 (v1.1 확장)

각 실행마다 다음 진단을 evidence에 저장한다.

```json
{
  "research_mode": "deep_source_research",
  "deep_capability_level": "lite",
  "initial_research_mode": "fast_synthesis",
  "final_research_mode": "deep_source_research",
  "mode_distance": 2,
  "mode_escalations": 1,
  "mode_escalation_gap": "architecture_coverage_low",
  "tavily_called": true,
  "tavily_extract_called": false,
  "notebook_called": false,
  "local_refs": 6,
  "web_refs": 4,
  "source_pack_chars": 0,
  "structured_evidence_chars": 0,
  "latency_sec": 8.4,
  "verification_score": 0.78
}
```

Phase 1a에서는 `source_pack_chars` / `structured_evidence_chars`는 0으로 기록 (Phase 1b부터 채워짐).

## 7. Tavily 적용 방식

### 7.1 현재 문제

현재 Tavily 결과는 `content[:500]`으로 잘린다. 이후 `researcher.py`에서 다시 260자 excerpt가 된다.

이 구조에서는 Tavily가 "최신 웹 소스 수집기"가 아니라 "짧은 snippet 공급기"가 된다.

### 7.2 변경 원칙

1. UI 표시용 `excerpt`와 분석용 `content_full`을 분리한다.
2. Search는 URL 발견과 랭킹에 사용한다.
3. Extract는 공식 문서/권위 소스 원문 확보에 사용한다.
4. Crawl/Map은 문서 사이트 전체 구조가 필요할 때만 사용한다.

예상 필드:

```json
{
  "url": "...",
  "title": "...",
  "excerpt": "260자 표시용",
  "content_full": "분석용 긴 본문",
  "score": 0.8,
  "source_type": "web",
  "authority_level": "primary",
  "retrieval_method": "tavily_extract"
}
```

### 7.3 Tavily ON 기준

Tavily는 다음 조건에서 켠다.

```text
- 최신 버전/API/SDK/가격/보안/라이선스가 중요하다.
- 외부 기술스택 선택이 필요하다.
- 공식 문서 기반 판단이 필요하다.
- 운영 리스크가 외부 기술 생태계에 의존한다.
- 공식 데이터 출처를 확인해야 한다.
```

예:

```text
8인 네트워크 포커 웹앱:
  WebSocket, room/session, reconnect, scaling, mobile browser constraints 확인 필요.

로또 통계 추천 웹앱:
  최신 공식 회차 데이터, 데이터 출처, 주기적 수집 방식 확인 필요.
```

## 8. NotebookLM 적용 방식

### 8.1 현재 문제

현재 evidence 경로의 NotebookLM 호출은 다음과 같다.

```text
짧은 local/web excerpt
-> query_notebooklm(prompt)
-> archive notebook 질의
-> notebook_summary plain text
```

이 구조는 NotebookLM의 장점인 "긴 소스 묶음 기반 cross-reference"를 사용하지 못한다.

### 8.2 변경 원칙

NotebookLM은 다음 두 경우에만 사용한다.

1. `archive_research`
   - 사용자의 archive 노트북이 실제 task와 관련 있을 때.

2. `deep_source_research`
   - Tavily Extract/Crawl 또는 local docs로 만든 source_pack을 임시 노트북에 주입한 뒤 질의할 때.

금지 경로:

```text
Tavily snippet 3개
-> NotebookLM에 짧은 prompt
-> 다시 LLM에 넣기
```

### 8.3 Deep research 흐름

```text
source_pack
-> create_notebook()
-> inject_sources(urls/texts)
-> query_notebooklm(notebook_id=...)
-> LLM normalizer
-> structured_evidence
```

임시 노트북 수명:

```text
Phase 1: 질의 후 삭제 또는 수동 TTL 정책 문서화
Phase 2: source_hash 기준 7일 TTL 캐시
```

## 9. Verifier 변경

### 9.1 현재 문제

현재 verifier는 `notebook_summary` 존재 여부에 점수를 준다. 이 방식은 "도구를 호출했는가"를 평가하고 "결과가 도움이 됐는가"를 평가하지 않는다.

### 9.2 변경 목표 (v1.1)

`notebook_present`를 제거하고 **deterministic ground signal 4종**으로 대체한다. LLM이 만든 entity를 LLM-extracted entity로 채점하는 자기참조 위험을 피하기 위해, 측정 가능한 외부 신호 위주로 구성한다.

| 신호 | 의미 | 계산 방식 |
|------|------|----------|
| `citation_validity` | claim의 `source_id`가 `source_pack.sources`에 실재하는 비율 | (실재 source_id 수) / (claim에서 인용한 source_id 수) |
| `claim_source_ratio` | 전체 claim 중 source_id가 1개 이상 연결된 비율 | (인용 claim 수) / (전체 claim 수) |
| `primary_source_ratio` | source_pack에서 primary authority 소스 비율 | (primary 소스 수) / (전체 소스 수) |
| `source_pack_chars` | 분석 가능 본문 총량 (snippet 깊이 측정) | sum(len(s.content_full) for s in sources) |

각 신호의 임계와 가중치는 Phase 1b 도입 시점에 fixture로 calibration한다.

### 9.3 Phase 1a verifier (v1.1 추가)

Phase 1b 도입 전까지는 기존 verifier를 유지하되, escalation 트리거가 가능하도록 다음 gap을 emit하도록 확장한다 (이름은 §6.5 enum 사용).

```text
- NO_EXTERNAL_EVIDENCE (기존 신호 재활용)
- FRESHNESS_REQUIRED_MISSING (요청 키워드 + web_refs 부재로 판정)
- OFFICIAL_SOURCE_MISSING (primary authority 소스 부재)
```

deep-tier gap 3종 (`ARCHITECTURE_COVERAGE_LOW`, `HIGH_RISK_CAPABILITY_MISSING`, `MULTI_CLIENT_MISSING`)은 verifier가 아닌 `research_router.detect_complexity_gaps()`가 emit한다 (request 기반 lightweight detector).

### 9.4 Phase 1b verifier 교체

§9.2의 deterministic 4종으로 가중치 테이블을 교체. 동시에 §6.5 enum을 그대로 사용해 1a detector와 schema 일관성 유지.

## 10. 예시 시나리오

### 10.1 8인 네트워크 포커 웹앱

요청:

```text
8인이 같이 플레이할 수 있는 풀네트워크 포커게임을 PC, 모바일 웹앱으로 만들어줘.
로직은 서버에서 돌리고 클라이언트는 뷰어 역할만 할거야.
```

모드:

```json
{
  "mode": "deep_source_research",
  "secondary_modes": ["fresh_lookup", "skill_evolution"],
  "risk_level": "high"
}
```

핵심 capability:

```text
- server_authoritative_game_loop
- realtime_websocket_room_management
- betting_round_state_machine
- poker_hand_evaluation
- reconnect_and_resume
- responsive_card_table_ui
- multi_client_simulation_test
- anti_cheat_input_validation
```

Tavily 사용:

```text
- WebSocket/Socket.IO/Redis adapter 공식 문서
- 모바일 웹 실시간 연결 제약
- hand evaluator 라이브러리 문서
```

NotebookLM 사용:

```text
- 여러 긴 공식 문서를 비교해 room/session/reconnect/scaling 설계 판단이 필요할 때만 deep_source_research로 사용
```

project_brief에는 "포커 게임"이 아니라 "server-authoritative realtime multiplayer poker platform"으로 반영되어야 한다.

### 10.2 로또 통계 추천 웹앱

요청:

```text
최신 로또 800회차 1등 당첨 번호들을 수집해서 패턴을 분석하고,
앞으로 매주마다 1등 번호를 누적해서 통계를 내고 패턴을 분석해서
1등 당첨 번호를 추천해주는 PC, 모바일 웹앱을 만들어줘.
```

모드:

```json
{
  "mode": "fresh_lookup",
  "secondary_modes": ["data_pipeline", "statistical_analysis", "scheduled_maintenance", "skill_evolution"],
  "risk_level": "high"
}
```

핵심 capability:

```text
- official_lottery_data_collector
- draw_result_normalizer
- lottery_statistics_engine
- number_recommendation_generator
- weekly_scheduler
- responsive_dashboard_ui
- data_integrity_verifier
- responsible_prediction_disclaimer
```

Tavily 사용:

```text
- 공식 회차 데이터 출처 확인
- 데이터 수집 방식 확인
- 최신 회차 검증
```

NotebookLM 사용:

```text
- 기본 OFF
- 긴 약관/정책/광고 표현 리스크 분석이 필요할 때만 archive/deep 모드
```

중요 제품 제약:

```text
- 당첨 보장 표현 금지
- 과거 통계 기반 추천이며 실제 당첨 가능성을 보장하지 않음
- 데이터 출처와 최신성 검증 필수
```

## 11. 구현 계획 (v1.1)

7라운드 deliberation 합의에 따라 Phase 1을 **1a / 1b**로 분할하고, NotebookLM source injection은 Phase 3로 미룬다. 회귀 원인 추적을 쉽게 하고 cleanup 누락 위험을 0으로 만들기 위함.

### Phase 1a — Router + Lightweight Detector + Eval

목표: router의 mode 분류 + escalation 정정 데이터를 1a 시점부터 누적. `project_brief` 형식은 기존과 동일 유지(새 필드 미도입).

변경:

1. **`core/research_router.py` 신규**
   - `_compute_signal_scores(request)` (private) — freshness/external_stack/operational_risk/data_pipeline/live_project/deep_decision/archive 점수
   - `_select_mode(scores) -> ResearchPlan` (private) — §4.2.1 알고리즘
   - `plan(request) -> ResearchPlan` (mode/secondary/scores)
   - `detect_complexity_gaps(request, evidence, final_mode) -> list[ResearchGap]` — §4.4.5 정책
   - **gap-to-mode 매핑**도 이 파일에 (§4.4.2)

2. **`ResearchGap` enum 잠금** (§6.5)
   - 9개 gap 이름을 v1.2 진입 시점에 고정 (fresh 3 + deep 3 + quality 3)

3. **`core/researcher.py` 수정**
   - `collect_project_evidence(task_input, *, workspace=None, risk_level="normal", comparison_mode=False, research_plan=None, hint_gaps=None, **_kwargs) -> dict` — **시그니처 확장 필수** (`research_plan`, `hint_gaps`, `**_kwargs` 추가)
   - 기본 호출 시 (`research_plan is None`) 내부에서 `ResearchRouter.plan()` 호출
   - escalation 호출 시 (verifier에서 `hint_gaps` 전달) gap-to-mode 매핑으로 mode 재선택
   - mode별 Tavily/NotebookLM gating
   - **NotebookLM source injection 미적용** (Phase 3까지)
   - escalation 루프: max retry=1, gap-driven direct-jump

4. **`core/research_verifier.py` 최소 확장**
   - 기존 가중치 유지
   - `NO_EXTERNAL_EVIDENCE`, `FRESHNESS_REQUIRED_MISSING`, `OFFICIAL_SOURCE_MISSING` gap을 §6.5 enum 이름으로 emit
   - deep-tier gap은 verifier가 아닌 router detector가 담당
   - **`max_retries=1`로 변경** (router escalation `max retry=1`과 일치, §4.4.1)
   - 기존 `try: evidence_fn(hint_gaps=...) except TypeError: evidence_fn()` fallback은 **deprecation 경고 로그**와 함께 유지. Phase 1a 머지 직후 fallback 제거 (researcher 시그니처가 확장되면 TypeError가 더 이상 발생하지 않음)

5. **`core/project_pipeline.py` 통합 (v1.2 필수 추가)** — escalation의 핵심 통로
   - 현재 `_evidence_fn`은 zero-arg closure(`def _evidence_fn():`)로 정의되어 있어 verifier가 `hint_gaps=...`를 전달하면 `TypeError`로 떨어지고 silent fallback으로 무력화된다 (검증: `core/project_pipeline.py:653`, `core/research_verifier.py:246-249`).
   - **변경**: `def _evidence_fn(**kwargs)`로 시그니처 확장 후 `collect_evidence(task_input, **(_collect_kwargs | kwargs))` 형태로 전파.
   - 이 통합 없이는 §4.4 escalation 메커니즘이 코드상 실행 불가 (router가 gap을 emit해도 evidence_fn 재호출에 도달 못 함).
   - 회귀 테스트: `_evidence_fn(hint_gaps=[...])`가 `TypeError` 없이 호출되는지 단위 테스트 추가.

6. **`af.spec` `hiddenimports` 등록 (v1.2 필수 추가)**
   - `'core.research_router'` 항목 추가 (`af.spec:32-150` 영역).
   - CLAUDE.md "새 `core/*.py` 파일은 `af.spec` `hiddenimports`에 반드시 추가" 규칙 준수.
   - (선택) 같은 PR에서 기존 누락된 `core.retrieval_router`, `core.researcher`, `core.research_verifier`도 함께 등록하면 frozen 빌드 회귀 방지.

7. **Eval fixture 신규**
   - `tests/test_research_router_modes.py` (또는 `tests/fixtures/research_router_cases.json`)
   - 한국어/영어/혼합 15~20건
   - 라벨: `expected_mode`, `expected_secondary_modes`, `expected_capabilities`, `expected_requires_web`, `expected_requires_notebooklm`
   - **§4.2.1 임계값 calibration은 fixture 라벨로만 수행** — 코드 임계 직접 튜닝 금지.

8. **Diagnostics 저장**
   - §6.6의 진단 필드 evidence에 저장
   - `projects/<workspace>/data/research_log.jsonl`에 append

### Phase 1b — Source pack + Structured evidence + Verifier 교체

목표: evidence 품질 측정을 deterministic으로 전환하고, project_brief에 structured evidence 필드 추가.

변경:

1. **`core/web_search.py`**
   - `content[:500]` 제거
   - `excerpt` (UI용 짧은 요약) / `content_full` (분석용 원문) 분리
   - `tavily_extract()` 확장 지점 추가

2. **`core/researcher.py`**
   - `_synthesize_structured_evidence()` 신규 (LLM normalizer)
   - **fast 모드는 별도 호출 금지** — 기존 `research_project_brief()` LLM 호출에 합침
   - fresh/deep/archive 모드만 normalizer 별도 호출
   - `project_brief`에 structured evidence 필드 추가 (§6.4)

3. **`core/research_verifier.py` 교체**
   - `notebook_present` 제거
   - deterministic 4-metric (§9.2) 도입
   - 기존 6-signal과의 가중치 calibration은 fixture 기반

4. **§6.5 enum 일관 사용**
   - 1b verifier도 같은 enum의 gap을 emit
   - 새 gap이 필요하면 enum에 추가만, 기존 이름 변경 금지

### Phase 2 — 뒤 파이프라인 보강

목표: 기존 산출물 생성기가 새 필드를 적극 사용.

1. `core/work_item_generator.py`: `required_capabilities`, `verification_focus`, `skill_gap_hypotheses`를 문서에 반영
2. `core/project_task_board.py`: acceptance criteria에 `required_capabilities`, `verification_focus` 반영
3. skill pipeline: `skill_gap_hypotheses`를 `SkillRetrievalEngine.decide_reuse()`의 `required_capabilities` 입력으로 연결, reuse/enhance/forge 결정 사유를 `skill_manifest.json`에 보존

### Phase 3 — NotebookLM source injection (cleanup 동봉)

목표: deep_source_research를 `lite`에서 `full`로 승격. 임시 노트북 cleanup을 같은 PR에 강제.

1. `core/research_engine.py`에 `delete_notebook(notebook_id)` 신규
2. 임시 노트북 prefix `af_tmp_*` 컨벤션
3. source_pack → NotebookLM 임시 노트북 주입 → 질의 → 삭제 wrapper
4. 실패 시 orphan log (`af_tmp_orphans.jsonl`)
5. TTL policy (예: 7일 후 자동 cleanup 스크립트)
6. diagnostics에 `deep_capability_level: "full"`로 전환
7. **Phase 1a~2에서 누적된 `mode_distance` 분포 기반으로 deep gap emission threshold 재조정**

## 12. 성공 기준

### 12.1 품질 기준

다음 요청에서 `project_brief`가 핵심 capability를 놓치지 않아야 한다.

| 요청 | 필수 포함 |
|------|-----------|
| 8인 네트워크 포커 | WebSocket/room/session, server-authoritative state, reconnect, multi-client test |
| 로또 통계 앱 | official data collector, scheduler, statistics engine, disclaimer, data integrity |
| 라이브 프로젝트 리팩터링 | impact scope, migration plan, regression matrix |

### 12.2 성능 기준

```text
fast_synthesis:
  Tavily/NotebookLM 호출 없음

fresh_lookup:
  Tavily 호출 있음, NotebookLM 기본 없음

deep_source_research:
  NotebookLM 호출은 source_pack 주입 이후에만 발생
```

### 12.3 관측 기준 (v1.1)

각 실행마다 §6.6의 diagnostics를 evidence에 저장하고 `projects/<workspace>/data/research_log.jsonl`에 append.

### 12.4 운영 KPI 임계 (v1.1 추가)

누적된 diagnostics를 주기적으로 집계해 router 튜닝 신호로 사용한다.

| 지표 | 임계 | 액션 |
|------|------|------|
| `mode_escalations > 0` 비율 | ≥ 30% | router 키워드 가중치 재튜닝 |
| `mode_distance ≥ 2` 비율 | ≥ 10% | router 카테고리 재설계 (signal score 임계 조정) |
| deep gap emission 빈도 | Phase 3 진입 전 재측정 | NotebookLM 비용 폭발 방지 위해 threshold 보수화 |

### 12.5 Phase 1a Eval fixture 통과 기준 (v1.1 추가)

`tests/test_research_router_modes.py` (또는 fixture json)의 15~20건 케이스에서:

```text
- expected_mode 정확도 >= 80%
- expected_secondary_modes 부분 일치 >= 60%
- requires_web / requires_notebooklm 정확도 >= 90%
```

미달 시 Phase 1a 머지 차단. router signal weight를 fixture 기반으로 calibration.

## 13. 최종 판단

이 설계는 기존 파이프라인을 전면 교체하지 않는다.

핵심은 다음 하나다.

```text
현재:
  모든 요청에 비슷한 evidence 수집 절차를 적용한다.

개선:
  요청을 먼저 리서치 모드로 분류하고,
  필요한 도구만 사용해 structured evidence를 만든 뒤,
  더 풍부한 project_brief를 기존 뒤 파이프라인에 넘긴다.
```

따라서 초기 적용 위험은 낮고, 효과는 뒤 단계 전체에 전파된다.

```text
better project_brief
-> better role_plan
-> better task_board
-> better work-item docs
-> better skill reuse/enhance/forge
-> better execution readiness
```

## 14. 변경 이력

### v1.2 (2026-05-02) — af-cross-review BLOCK 4건 반영

v1.1 → v1.2: codex_cli 단독 cross-review에서 발견한 BLOCK 4건 + WARN 1건(W3)을 반영. WARN 3건(키워드 중복 / verifier max_retries 공존 / fixture 임계 60%)은 advisory 정책에 따라 미반영.

| BLOCK ID | 항목 | 반영 위치 |
|----------|------|-----------|
| **B1** | `_evidence_fn` zero-arg → escalation 죽음 | §11 Phase 1a 항목 5 (`core/project_pipeline.py` 통합 추가) + 항목 3 (researcher 시그니처 확장) + 항목 4 (verifier `max_retries=1`, fallback deprecation) |
| **B2** | enum "잠금" vs Phase 1b 4-metric 매핑 부재 | §6.5 9개로 확장 (quality-tier 3종 사전 등록) + §4.4.2 매핑 표에 quality-tier unclassified 추가 + 잠금 정책 reword |
| **B3** | `_select_mode` 알고리즘 명세 부재 | §4.2.1 신규 — precedence/임계값 v1.2 초기치 명시 |
| **B4** | `af.spec` hiddenimports 누락 | §11 Phase 1a 항목 6 (`af.spec` 등록 필수, 기존 누락 파일도 동시 등록 권장) |
| W3 | §4.4.5 final_mode 조건 1줄 불일치 | §4.4.5 예시 코드 `final_mode in ("fast_synthesis", "fresh_lookup")`로 수정 |

핵심 변경 요약:

1. **Escalation 통합 통로 명문화**: router가 gap을 emit해도 verifier→pipeline→researcher 호출 체인에서 `hint_gaps`가 실제로 전달되도록 4개 파일 시그니처/closure를 일관 변경. v1.1에서는 router 단독 설계만 있었고 통합 지점이 빠져 있었음.
2. **Enum 사전 등록**: Phase 1b에서 enum 추가 PR 없이도 4-metric verifier가 emit할 수 있도록 quality-tier 3종을 v1.2 시점에 등록.
3. **알고리즘 명시**: `_select_mode`의 precedence와 임계값을 v1.2 초기치로 잠금. 이후 변경은 §12.5 fixture calibration으로만 가능.
4. **빌드 정합성**: `af.spec` 등록을 Phase 1a 체크리스트의 필수 항목으로 명시.

### v1.1 (2026-05-01) — 7라운드 deliberation 합의

R1 → R7 deliberation 결과를 한 곳에 정리한 표.

| 항목 | R1 | R2 | R3 | R4 | R5 | R6 | R7/최종 |
|------|----|----|----|----|----|----|---------|
| Phase 분할 1a/1b | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cleanup → P3 | P1 | P3 | P3 | P3 | P3 | P3 | P3 |
| Verifier deterministic 4종 | 추상 | 4 | 4 | 4 | 4 | 4 | 4 |
| Eval fixture 15~20 (한/영/혼합) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fast LLM normalizer 합침 | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Escalation max retry = 1 | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Direct-jump (vs 인접) | — | 인접 | 인접 | direct | direct | direct | direct |
| `mode_distance` metric | — | — | — | (암묵) | ✓ | ✓ | ✓ |
| Deep gap emission threshold | — | — | — | (암묵) | ✓ | ✓ | ✓ |
| 1a lightweight detector | — | — | — | — | — | ✓ | ✓ |
| Detector signal 재사용 | — | — | — | — | — | ✓ | ✓ |
| `ResearchGap` enum 잠금 | — | — | — | — | — | ✓ | ✓ |
| Detector 정책 분리 (final_mode 조건) | — | — | — | — | — | — | ✓ |
| Deep-lite 표기 | — | — | — | — | — | — | ✓ |
| `research_router.py` vs `retrieval_router.py` 분리 | — | — | — | — | — | — | ✓ |

핵심 합의:

1. **router 오판 안전망**: max retry=1 + gap-driven direct-jump (1단계 인접 강제 없음).
2. **자기참조 회피**: verifier signal은 LLM-extracted entity가 아닌 deterministic ground signal 4종 위주.
3. **schema 연속성**: `ResearchGap` enum을 Phase 1a 시점에 잠금 → Phase 1b verifier도 같은 이름 사용.
4. **단계 의미 명시**: Phase 1a~2의 deep은 `lite` (NotebookLM injection 미적용), Phase 3+는 `full`로 승격.
5. **파일 책임 분리**: `core/research_router.py` 신규는 기존 `core/retrieval_router.py`(local retrieval strategy)와 다른 책임. §0에 명시.
6. **cleanup 강제**: NotebookLM source injection 도입 PR(Phase 3)은 prefix + delete wrapper + orphan log + TTL을 같은 PR에 묶어야 머지.

### v1 (2026-04-29) — 최초 설계

초기 설계. mode 분류, source_pack/structured_evidence 도입, NotebookLM source injection 분리.

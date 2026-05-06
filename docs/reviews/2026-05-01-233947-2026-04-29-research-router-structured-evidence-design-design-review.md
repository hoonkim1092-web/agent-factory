# Design Review: 2026-04-29-research-router-structured-evidence-design

> Source: docs/2026-04-29-research-router-structured-evidence-design.md
> Date: 2026-05-01 23:39
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

이유: Critic 2건이 Critical, Cross 8건 ACCEPT. 두 리뷰가 다른 각도에서 같은 Phase 1 실행 가능성 문제를 가리킨다(verifier-vs-mode 충돌, af.spec 누락, Tavily Extract 미구현). 구현 진입 전 설계 보강 필수.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] Phase 1 verifier vs fast_synthesis/structured_evidence 충돌
- **Critic #1**: `external_present`(0.15) + `notebook_present`(0.15) 가중치가 fast_synthesis(둘 다 OFF)에서 0.30점 손실 → 정규화 후 임계 0.6 미달 → max_retries=2 무한 재시도 위험. `core/research_verifier.py:84-94, 142-145`.
- **Cross #2**: 새 verifier metric(`claim_grounding`, `tech_stack_quality` 등)이 `structured_evidence`를 요구하는데 §3.2 흐름은 verifier를 synthesis보다 먼저 호출. 점수 산정 불가능.
- **Judgment**: 두 리뷰가 같은 verifier 모듈에서 다른 결함을 지적. 둘 다 코드 라인 근거 명확.
- **Action Required**:
  1. verifier 시그니처에 `research_mode: str` 추가, mode별 weight matrix 표 §9에 명시 (fast=2개 신호, fresh=4개, deep=6개; 각각 합 1.0 정규화)
  2. 검증을 2-pass로 분리: `verify_source_pack()` (정규화 전) + `verify_structured_evidence()` (synthesis 후). §3.2 흐름도 갱신.

#### 2. [ACCEPT] [Critical] `af.spec` hiddenimports 누락 — frozen 빌드 즉시 크래시
- **Critic #2**: 신규 `core/research_router.py`가 §11 Phase 1 변경 목록에 `af.spec` 갱신 없음. CLAUDE.md 규칙 위반. dist 빌드 시 ImportError.
- **Cross #8**: `af.spec:32` 수동 hiddenimports에 `core.research_router` 미포함. 코드리뷰에서도 manual hiddenimports를 known risk로 명시.
- **Judgment**: 양쪽 리뷰 합치, CLAUDE.md 명시 규칙. 반박 여지 없음.
- **Action Required**: §11 Phase 1 체크리스트에 "`af.spec` `hiddenimports`에 `core.research_router` 추가 + frozen smoke test" 항목 추가.

#### 3. [ACCEPT] [High] Tavily Extract API 미구현 상태로 fresh_lookup/deep_source 흐름 의존
- **Critic #4**: §5.2 단계 4 "Tavily Extract로 원문 확보"가 핵심인데 §11은 Extract를 "추후"로 미룸. fresh_lookup 전체 미동작.
- **Cross #4**: `core/web_search.py:25`는 `tavily_search()`만 존재. Extract 함수 시그니처/return shape/timeout/max_chars/fallback 모두 미정의.
- **Judgment**: 동일 문제. 양쪽 모두 web_search.py를 직접 확인.
- **Action Required**: Phase 1 분할 또는 Extract API 계약을 §5에 추가 — `tavily_extract(urls, *, timeout_sec=30, max_chars_per_source=...) -> list[Source]` (`content_full`, `excerpt`, `content_hash`, `retrieval_method`, `error`, `fallback_used` 포함).

#### 4. [ACCEPT] [High] Escalation retry contract가 현재 인터페이스로 구현 불가
- **Critic #3** + **Cross #1**: `ProjectPipeline._evidence_fn`은 zero-arg 래퍼(`project_pipeline.py:653`), `verify_with_retry`의 `hint_gaps`는 `TypeError` fallback에서 swallow됨(`research_verifier.py:220`), `collect_project_evidence()`는 `mode`/`research_plan`/`hint_gaps` 인자 없음(`researcher.py:507`). 또한 기존 `risk_level` 분기(`researcher.py:562-565`)와 새 `research_plan` 결정의 우선순위 미정의.
- **Judgment**: Critic은 risk_level 잔존을, Cross는 wrapper/kwargs를 봤다. 같은 인터페이스 영역.
- **Action Required**: 명시적 계약 추가 — `ResearchRouter.plan(...) -> ResearchPlan`, `ResearchRouter.escalate(plan, gaps) -> ResearchPlan`, `collect_project_evidence(..., research_plan=None, hint_gaps=None)`. Pipeline wrapper `**kwargs` 수용. risk_level 기반 NotebookLM 분기를 deprecate 명시 + 전환 단계 기술.

#### 5. [ACCEPT] [High] Mode 분류 점수→결정 매핑 알고리즘 부재
- **Critic #5**: 7개 점수 함수만 정의, mode 결정 규칙(임계값/결합식) 없음. secondary_modes 4개 부착 알고리즘도 없음. 구현자 추측 필요 → 비결정적.
- **Cross**: not flagged.
- **Judgment**: 단일 출처지만 §4.2 점수 정의와 §10.2 예시 사이의 결정 로직 공백이 명확. 강한 증거.
- **Action Required**: §4.2에 의사결정 트리 + secondary 부착 규칙 + 5~10개 분류 unit test fixture 추가.

#### 6. [ACCEPT] [High] Phase 1 brief 신규 필드가 다운스트림에서 미소비 (Phase 2까지 dead weight)
- **Critic #8** + **Cross #3**: `required_capabilities`, `verification_focus`, `skill_gap_hypotheses` 등이 Phase 1에서 생산되지만 `work_item_generator.py:43`, `project_task_board.py:945`은 legacy 필드만 읽음. Critic은 추가로 `_merge_project_brief_evidence`(researcher.py:589)와 strict 변환 로직 충돌 검증 필요 지적.
- **Judgment**: 동일 영역 + Critic이 strict 변환 호환성을 추가 제기. 둘 다 ACCEPT.
- **Action Required**: Phase 1에서 신규 필드를 기존 필드(`deliverables`/`required_skills`/`risks`/`research_notes`/`evidence_summary`)에 projection 하거나, `_research_v2` internal 영역에 격리 후 Phase 2에서 promote. `_merge_project_brief_evidence` 충돌 회귀 테스트 명시.

#### 7. [ACCEPT] [Medium] NotebookLM 임시 노트북 lifecycle 미명시 → 고아 노트북 위험
- **Critic #7** + **Cross #6**: `create_notebook`은 ID만 반환, registry/manifest/delete primitive 없음. "삭제 또는 수동 TTL"은 구현자 결정 떠넘김. 프로세스 크래시 시 고아.
- **Judgment**: 합치.
- **Action Required**: lifecycle wrapper 정의 — `cleanup_status`, best-effort delete, `source_hash` 기반 fallback cache file, 실패 시 `research_diagnostics`에 영속화. Phase 1에서 deep_source_research를 opt-in/OFF로 두는 안 검토.

#### 8. [ACCEPT] [Medium] research_log 저장 경로 불명확 + atomic write 누락
- **Critic #10** + **Cross #7**: §11 "`projects/<workspace>/data/research_log.jsonl`"은 `workspace`가 이미 absolute path(`project_pipeline.py:614`)이므로 prefix 오류. 회전/lock 정책 없음. 코드리뷰는 `.af_runtime/control/run_ledger.jsonl`을 canonical로 명시.
- **Judgment**: 합치.
- **Action Required**: `{workspace}/data/research_log.jsonl` 또는 `{workspace}/.af_runtime/control/research_events.jsonl` 중 택1, JSONL schema + `core/file_lock.py` + atomic write 패턴 명시. per-run 진단은 `runs/{run_id}/research_diagnostics.json`.

#### 9. [ACCEPT] [Medium] Skill Registry "항상 ON"인데 evidence 경로에 미연결
- **Cross #5**: `researcher.py:507` `collect_project_evidence`는 workspace/local/web/NotebookLM만 수집, registry 조회 없음. `skill_gap_hypotheses` 생성 불가.
- **Critic**: not flagged directly.
- **Judgment**: Cross 단독이지만 코드 라인 직접 인용, §3.3 "Skill Registry 항상" 약속과 직접 모순. 강한 증거.
- **Action Required**: `_collect_skill_candidates(task_input, required_capabilities)` 추가, `source_pack`/`structured_evidence`에 포함.

#### 10. [ACCEPT] [Medium] `_compute_signal_scores` 공유 약속이 테스트 불가능
- **Critic #9**: 시그니처/순수성/캐싱 미정. plan()과 detect_complexity_gaps()가 매번 호출 시 같은 결과 보장 메커니즘 없음. drift는 코드리뷰만으로 잡힘.
- **Cross**: not flagged.
- **Judgment**: 단일 출처지만 §0의 "drift 방지" 약속을 코드 계약으로 만들지 않음. 합리적 증거.
- **Action Required**: `_compute_signal_scores(request) -> SignalScores`(frozen dataclass) + `RequestKey` LRU 캐시. 동일 입력→동일 출력 회귀 테스트.

#### 11. [HOLD] [Medium] live_project_analysis 진입 경계 불분명
- **Cross #10**: 운영 중 프로젝트 유지보수가 `ControlPlaneIntake`/`maintenance_pipeline`/`change_impact`/`regression_gate`와 겹치는지, `prepare_brief()`만 진입점인지 불명.
- **Critic**: not flagged.
- **Judgment**: 라우팅 소유권은 author 의도 확인 필요. 코드 사실만으로 단정 불가.
- **Question for Author**: live_project_analysis 모드의 CLI 진입 경로가 project creation, maintenance intake, 둘 다 중 어디인지? 기존 `change_impact`/`regression_gate` 재사용 vs 신규 구현 어느 쪽인지?

#### 12. [REJECT] [Low] research_router vs retrieval_router 이름 충돌 우려
- **Source**: Cross #9
- **Original Finding**: 이름이 비슷해 routing 책임 중복 우려.
- **Rejection Reason**: `RetrievalRouter`(local retrieval strategy: BM25/dense/hybrid/web)와 `ResearchRouter`(project research mode: fast/fresh/deep) 추상화 레벨이 명백히 다름. §0이 책임 분리 표로 이미 정당화. Critic도 §0의 분리를 "옳다"고 평가.

### 추가 미커버 항목 (Critic 단독 — 모두 [ACCEPT])

Critic의 "Missing from Design" 7개 중 본문 finding과 별도로 가치 있는 항목 (각 [Low~Medium]):

- **LLM normalizer provider 결정 정책** (Medium): `engine_auth.auto_configure_cli_provider()` vs `control_plane_llm` vs `llm_engine` 중 선택, 한도 초과 fallback chain.
- **Phase 1 회귀 테스트 매트릭스** (Medium): §12.1 품질 기준의 pytest fixture 명세.
- **롤백 경로** (Medium): `AF_RESEARCH_ROUTER=0` ENV feature flag 설계.
- **`prepare_brief()` 호환성** (Low): `_supports_risk` introspection 분기 패턴이 `research_plan`에도 필요한지.

(secondary_modes 실행 순서 [Critic #11, Low]는 Cross HOLD #10과 함께 author 의도 확인 후 결정.)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Verifier vs fast_synthesis / structured_evidence 충돌 | Critical | ACCEPT | Both |
| 2 | af.spec hiddenimports 누락 | Critical | ACCEPT | Both |
| 3 | Tavily Extract API 미구현 vs fresh_lookup 의존 | High | ACCEPT | Both |
| 4 | Escalation retry contract 구현 불가 (kwargs/risk_level) | High | ACCEPT | Both |
| 5 | Mode 분류 점수→결정 매핑 부재 | High | ACCEPT | Critic |
| 6 | 신규 brief 필드 다운스트림 미소비 | Medium | ACCEPT | Both |
| 7 | NotebookLM 임시 노트북 lifecycle 미명시 | Medium | ACCEPT | Both |
| 8 | research_log 경로/atomic write 미정 | Medium | ACCEPT | Both |
| 9 | Skill Registry evidence 경로 미연결 | Medium | ACCEPT | Cross |
| 10 | `_compute_signal_scores` 테스트 불가 | Medium | ACCEPT | Critic |
| 11 | live_project_analysis 진입 경계 | Medium | HOLD | Cross |
| 12 | research_router vs retrieval_router 충돌 | Low | REJECT | Cross |

### Recommendations (구현 진입 전 필수)

1. **§9 verifier 재설계**: mode별 weight matrix 표 + 2-pass 검증(`verify_source_pack` → synthesis → `verify_structured_evidence`). fast_synthesis 무한 retry 차단을 가장 먼저 해결.
2. **§11 Phase 1 체크리스트 보강**: `af.spec` hiddenimports 갱신, `tavily_extract` 계약, frozen smoke test, 회귀 fixture 5~10개 명시.
3. **§3.2 흐름도 + 인터페이스 계약**: `ResearchRouter.plan/escalate`, `collect_project_evidence(research_plan, hint_gaps)`, `_evidence_fn` `**kwargs` 전파. risk_level 분기 deprecation 단계 기술.
4. **§4.2 결정 알고리즘**: 점수→mode 매핑 의사결정 트리 + secondary_modes 부착 규칙.
5. **Phase 1 분할 검토**: (1a) Router + fast_synthesis + brief 필드 projection, (1b) Tavily Extract + fresh_lookup, (1c) deep_source_research(NotebookLM lifecycle 포함)로 분할하여 각 단계가 독립 동작하도록.
6. **`_compute_signal_scores` 계약화**: frozen dataclass + LRU 캐시 + 회귀 테스트.
7. **로깅/lifecycle 인프라**: file_lock + atomic write + ephemeral notebook registry.
8. **Author 결정 필요(HOLD #11)**: live_project_analysis 진입 경로 + 기존 maintenance/change_impact 재사용 정책.
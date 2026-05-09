# Design Review: 2026-04-29-research-router-structured-evidence-design

> Source: docs/2026-04-29-research-router-structured-evidence-design.md
> Date: 2026-05-02 00:17
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

3건의 Critical 결함(`_evidence_fn` 시그니처 충돌, `_select_mode` vs §10 예제 모순, af.spec 누락)이 모두 강한 코드/문서 근거를 동반한다. v1.2 동기화 갱신 전 Phase 1a 코드 진입 금지.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `_evidence_fn` 시그니처 충돌 — escalation이 silent dead code화
- **Critic**: `core/project_pipeline.py:653`의 zero-arg `_evidence_fn()`과 `core/research_verifier.py:246`의 `evidence_fn(hint_gaps=result.gaps)` 호출이 무조건 `TypeError` → silent fallback으로 `hint_gaps` 손실. router가 mode를 바꿔도 collector는 동일 mode로 재호출.
- **Cross**: not flagged (간접적으로 Cross #3이 evidence 키 드리프트로 같은 영역의 정합성 문제를 짚음)
- **Judgment**: Critic이 file:line 단위 근거 제시. 설계가 가정하는 escalation 데이터 경로가 현재 코드에 존재하지 않음 — Phase 1a 진입 즉시 런타임 dead code 발생.
- **Action Required**: §3.2 / §11 Phase 1a에 (a) `_evidence_fn(hint_gaps=None, upgraded_mode=None)` 시그니처 확장, (b) `research_verifier.py:246-248`의 silent `except TypeError` fallback 제거 또는 `inspect.signature` dispatch, (c) router escalation → evidence_fn 데이터 경로 명시.

#### 2. [ACCEPT] [Critical] ResearchPlan/Secondary Modes 계약 불안정 — 알고리즘이 §10 예제를 재현 불가
- **Critic** (#2): §4.2.1 algorithm은 `fresh_lookup`을 `primary == "fast_synthesis"`일 때만 secondary에 부착하는데 §10.1은 primary=`deep_source_research`인데 secondary에 `fresh_lookup` 포함. §10.2의 `statistical_analysis`/`scheduled_maintenance`는 §4.1 mode 목록에 없음. `skill_evolution`은 §4.2.1에서 후속 정책으로 빼고도 §10.1/§10.2 secondary에 박힘.
- **Cross** (#1): §4.2.1은 `mode/secondary_modes/scores`만 반환, §6.1은 `reason`, `requires_web`, `requires_tavily_extract`, `requires_notebooklm`, `requires_deep_source_pack` 추가, §10.2는 §4.1 외 secondary 추가.
- **Judgment**: 두 리뷰가 동일 영역의 다른 단면을 짚음. 합의 필요. Fixture 80% 임계(§12.5) calibration 자체가 불가능.
- **Action Required**: `ResearchMode`/`ResearchSecondaryMode`/`ResearchPlan` 데이터클래스+enum 정식화. §4.2.1 algorithm, §6.1 contract, §10 예제 schema 통일. §10 예제의 `statistical_analysis`/`scheduled_maintenance`는 별도 필드(`derived_capabilities`)로 분리하거나 §4.1 정식 mode로 승격.

#### 3. [ACCEPT] [Critical] `core/research_router.py`가 `af.spec hiddenimports` 누락 — frozen 빌드 ImportError
- **Critic** (#3): CLAUDE.md 명시("새 `core/*.py` 파일은 `af.spec hiddenimports`에 반드시 추가"), 현재 `af.spec`에 `core.research_router` 미등재. §11 Phase 1a 체크리스트에서 누락.
- **Cross** (#6): `af.spec`만이 아니라 `version.py`, `install-af.ps1`, frozen smoke validation, `docs/code_review/code-review.md` 갱신까지 누락.
- **Judgment**: Cross가 더 넓은 deployment 의무를 짚음. 둘 다 ACCEPT 후 통합 deploy checklist로 묶는다.
- **Action Required**: §11 Phase 1a에 deployment checklist subsection 추가 — (a) `af.spec hiddenimports`에 `core.research_router` 추가, (b) 동시 점검: `core.retrieval_router` 누락 여부, (c) `version.py`/installer 버전 정책, (d) frozen smoke validation, (e) `docs/code_review/code-review.md` 갱신.

#### 4. [ACCEPT] [High] Evidence dict shape contract 부재 + 키 드리프트
- **Critic** (#5): Phase 1a detector가 받는 `evidence` dict shape 명시 없음. `web_refs`만 참조. Phase 1b structured_evidence 전환 시 silently 깨질 위험.
- **Cross** (#3): 설계 pseudocode `evidence.get("web_refs")` vs 현재 `collect_project_evidence()` 반환 키 `web_references` — 그대로 구현 시 web evidence를 항상 missing으로 취급.
- **Judgment**: Cross가 즉시 발생하는 구체적 버그(키 이름 드리프트), Critic은 contract 부재의 근본 문제. 둘 다 같은 영역의 다른 층위.
- **Action Required**: §4.4.5에 Phase 1a detector input 최소 contract 표 추가 (`{web_refs, local_refs, notebook_summary, source_pack}`). 정식 키 이름 잠금 + `get_web_refs()` 헬퍼 도입. Phase 1b structured_evidence는 superset 보장 명시.

#### 5. [ACCEPT] [High] Signal scoring 규칙 미정의 — fixture calibration 불가
- **Critic** (#9): `freshness_score` 등 키워드 매칭이 카운트인지 binary인지 불명. 한/영 혼용, 부분 매칭, 형태소 분석 미정. §4.2.1의 임계값이 v1.2로 잠겼는데 점수 함수가 안 정해져 calibration 무의미.
- **Cross** (#2): substring vs token, Korean/English normalization, phrase weights, negation, year matching, tie handling 미정.
- **Judgment**: 두 리뷰 동일 지적. 즉시 ACCEPT.
- **Action Required**: §4.2에 scoring table 추가 — regex/token 패턴, 가중치, signal별 max cap, 한/영 normalization 규칙, negative 예시, tie-break fixture. `_compute_signal_scores` 계산 규칙 잠금.

#### 6. [ACCEPT] [High] ResearchGap enum ↔ Phase 1b 4-metric mapping 부재
- **Critic** (#4): §6.5 enum 6개와 §9.2 4-metric 사이의 1:N mapping 없음. 예: `citation_validity < 0.7`이면 어느 enum gap인지 미정. Phase 1a 누적 통계가 Phase 1b 진입 시 의미 단절.
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 §9.4 "1a detector와 schema 일관성 유지" 명시 vs mapping 미정의 모순이 명확. 강한 근거.
- **Action Required**: §9.2 또는 §9.4에 metric → enum gap mapping table 추가. §11 Phase 1b acceptance에 schema 일관성 검증 항목 추가.

#### 7. [ACCEPT] [High] Phase 1a eval에서 expected_capabilities 검증 불가
- **Critic**: not flagged
- **Cross** (#4): Phase 1a는 `project_brief` 형식 동일 유지(structured evidence 미도입)인데 fixture는 `expected_capabilities`를 라벨로 둠. Phase 1a는 mode/flag만 검증 가능, capability 추출은 못 함.
- **Judgment**: Cross 단독이지만 design lines [972-975, 1014-1018] 인용으로 근거 강함.
- **Action Required**: 테스트 분리 — `test_research_router_modes.py` (mode/flag), Phase 1b 통합 suite (`expected_capabilities`, `source_backed_claims`, `project_brief` 보강).

#### 8. [ACCEPT] [Medium] Archive/Live 모드 deep escalation 제외
- **Critic** (#6): §4.4.4 조건이 `final_mode in {fast_synthesis, fresh_lookup}`만 deep escalation 허용. archive 자료 기반 멀티플레이어 요청 같은 숨은 복잡도 미감지.
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 합리적 corner case 제기. 의도/비의도 명시 필요.
- **Action Required**: §4.4.4-2 조건을 `final_mode != deep_source_research`로 일반화하거나, archive/live가 deep secondary로 부착될 수 있도록 §4.2.1 algorithm 보강. 어느 쪽이든 명시.

#### 9. [ACCEPT] [Medium] Diagnostics/research_log.jsonl 스키마+동시성 미정의
- **Critic** (#7): dynamic_orchestrator 5-concurrent 환경에서 같은 워크스페이스 동시 append 시 JSON line 인터리브 위험. `core/file_lock.py` 사용 의무 미명시.
- **Cross** (#5): `run_id`, request hash, signal scores, secondary modes, emitted gaps, skip reasons, error codes 누락 — KPI tuning 불가.
- **Judgment**: 동일 파일에 대한 동시성(Critic) + 스키마 충실도(Cross) 두 측면. 통합 처리.
- **Action Required**: §11 Phase 1a-6 또는 §6.6에 (a) versioned JSONL schema (`schema_version, run_id, request_hash, initial_plan, final_plan, scores, gaps, retry_count, tool_calls, skip_reasons, latency_ms, verification`), (b) `FileLock` 보호 또는 per-run sub-file 후 merge 명시.

#### 10. [ACCEPT] [Medium] Tavily/NotebookLM 외부 도구 실패 시 fallback 미정의
- **Critic** (#8): Tavily Search/Extract 실패, NotebookLM 임시 노트북 생성 실패 등 happy-path 외 흐름 미정. 부분 실패 시 source_pack/verifier 4-metric 분모 0 처리 정책 부재.
- **Cross**: not flagged
- **Judgment**: 운영 신뢰성 측면에서 Critic 지적 타당.
- **Action Required**: 각 모드에 degradation subsection 추가 — (a) 부분 실패 시 degraded source_pack + `_degraded_sources` 태그, (b) 전체 실패 시 fast_synthesis 강등 + escalation 카운트 소비, (c) verifier 분모 0 처리 정책.

#### 11. [HOLD] [Medium] Archive relevance gating 미정의
- **Critic**: not flagged
- **Cross** (#7): NotebookLM archive 호출 조건이 "관련 있을 때"라고만 되어 있고, `archive_relevance_score`/threshold/notebook id 출처 미정.
- **Judgment**: Cross 단독, evidence는 확실하지만 Phase 1a 차단 사유까지는 아님 (archive_research mode 자체는 §4 정의됨). 저자 답변 필요.
- **Question for Author**: archive_relevance_score 계산 방식, 최소 임계, 노트북 메타데이터 출처(workspace config? 사용자 입력?), skip 시 diagnostics 표기 방식.

#### 12. [REJECT] [Low] `deep_capability_level` lite/full 미사용
- **Source**: Critic (#10)
- **Original Finding**: `lite/full` 두 값이 §6.6 diagnostics 외 코드 분기에 안 쓰임. Phase 3 전환 hook 위치 미정.
- **Rejection Reason**: 진단 표기/Phase 추적 용도로 의도적 명시 가능. Phase 3 진입 시 §11에서 결정해도 늦지 않음. 현 단계에서 BLOCK 사유 아님.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `_evidence_fn` 시그니처 충돌 → silent dead code | Critical | ACCEPT | Critic |
| 2 | ResearchPlan/Secondary Modes 계약 불안정 | Critical | ACCEPT | Both |
| 3 | af.spec/deployment checklist 누락 | Critical | ACCEPT | Both |
| 4 | Evidence dict contract 부재 + 키 드리프트 | High | ACCEPT | Both |
| 5 | Signal scoring 규칙 미정의 | High | ACCEPT | Both |
| 6 | enum ↔ 4-metric mapping 부재 | High | ACCEPT | Critic |
| 7 | Phase 1a eval expected_capabilities 검증 불가 | High | ACCEPT | Cross |
| 8 | Archive/Live deep escalation 제외 | Medium | ACCEPT | Critic |
| 9 | Diagnostics 스키마+동시성 | Medium | ACCEPT | Both |
| 10 | 외부 도구 실패 fallback 미정의 | Medium | ACCEPT | Critic |
| 11 | Archive relevance gating | Medium | HOLD | Cross |
| 12 | `deep_capability_level` 미사용 | Low | REJECT | Critic |

---

### Recommendations

Phase 1a 코드 진입 전 v1.2 동기화 갱신 필수:

1. **#1, #2, #3 (Critical 3건)을 v1.2로 즉시 잠금** — `_evidence_fn` 시그니처 + verifier fallback 제거, ResearchPlan dataclass 정식화 및 §4.2.1↔§6.1↔§10 schema 통일, deployment checklist 추가.
2. **#4, #5를 §4 영역에 묶어 갱신** — Evidence contract 표 + scoring table을 §4.2 / §4.4.5에 추가. Phase 1b 진입 시 superset 보장 조항 명시.
3. **#6은 §9.4에 mapping table로 명시** — Phase 1a/1b schema 일관성을 acceptance 기준에 포함.
4. **#7은 fixture 분리** — Phase 1a는 mode/flag만, Phase 1b 통합 suite로 capability/brief 검증 분리.
5. **#8, #10 정책 명시** — Archive/Live escalation 허용 여부 + 외부 도구 degradation 경로.
6. **#9는 versioned JSONL schema + FileLock** — observability 확보.
7. **#11은 저자 답변 후 결정** — archive_relevance_score 정의 합의 후 §5.3 보강.
8. **#12는 Phase 3 §11에서 결정 보류** — 현 단계 차단 사유 아님.
9. **문서 title을 v1.2로 bump** — 현재 v1.1 표기 vs §4.2.1 "v1.2 추가" 불일치 해소.
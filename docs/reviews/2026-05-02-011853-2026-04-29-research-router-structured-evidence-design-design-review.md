# Design Review: 2026-04-29-research-router-structured-evidence-design

> Source: docs/2026-04-29-research-router-structured-evidence-design.md
> Date: 2026-05-02 01:18
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

3 Critical findings from Critic + 2 High-severity integration findings from Cross. Algorithm self-reference failure (§10.1 poker) is a hard blocker.

### Aggregated Findings (15 total)

#### 1. [ACCEPT] [Critical] §4.2.1 알고리즘이 §10.1 poker 예제를 produce 못 함
- **Critic**: §10.1 "8인 풀네트워크 포커 웹앱" 텍스트를 §4.2 키워드 set으로 채점하면 deep_decision=0, operational_risk=1, primary는 `fast_synthesis`로 떨어짐. §4.4.5 escalation도 `MULTI_CLIENT_MISSING`이 `operational_risk>=3`을 요구하므로 미발화 → expected `deep_source_research`에 도달할 경로 없음.
- **Cross**: not flagged
- **Judgment**: 강력한 evidence (precedence trace + escalation 조건 trace). Critic이 §10.1 expected output과 §4.2.1 코드 trace를 직접 대조했고, 본문 §4.2.1 코드가 인용한 trace를 그대로 따름.
- **Action Required**: §4.2 `operational_risk_score`/`deep_decision_score`에 한국어 신호 (8인/n인/다인/뷰어/서버 권위) 보강 또는 `external_stack_score >= 3 AND primary==fast` → deep 승격 보조 룰 §4.2.1에 추가. Phase 1a fixture 진입 전에 §10.1·§10.2 두 케이스에 대한 worked example 표를 §4.2.1 직후 첨부해 dry-run 통과 증명.

#### 2. [ACCEPT] [Critical] §10.2 `secondary_modes`에 undefined 모드 (`statistical_analysis`/`scheduled_maintenance`)
- **Critic**: §4.1에는 6개 모드만 정의됨. §10.2 lottery 예제 secondary_modes의 두 항목은 §4.1·§4.2·§4.2.1 어디에도 없음. Phase 1a fixture가 부분 일치 60%를 요구하므로 calibration 무한루프 위험.
- **Cross**: not flagged
- **Judgment**: Critic의 §4.1 vs §10.2 직접 대조가 결정적. v1.2 변경 이력에 미반영된 NEXT_STEPS R2-3 확인 가능.
- **Action Required**: (a) §4.1에 두 모드 정식 등록 + 점수/임계 추가, 또는 (b) §10.2 예제에서 두 항목 제거 후 v1.2 produce 가능한 secondary 어휘 (`data_pipeline`, `fresh_lookup`, `skill_evolution` 셋)를 §4.2.1 직후 명시.

#### 3. [ACCEPT] [Critical] §4.4.5 detector emit logic이 deep-tier gap 3종 중 1종만 명세
- **Critic**: §6.5 enum에 잠긴 `ARCHITECTURE_COVERAGE_LOW`, `HIGH_RISK_CAPABILITY_MISSING`, `MULTI_CLIENT_MISSING` 중 마지막 1종만 §4.4.5 예시 코드에 emit 조건 명시. 구현자가 추측으로 코드 작성 위험.
- **Cross**: not flagged
- **Judgment**: §6.5 enum과 §4.4.5 예시 코드 간 mismatch는 확실. Phase 1a 머지 시점에 emit 매핑 부재가 finding #1 escalation 경로 고치는 작업과도 직결.
- **Action Required**: §4.4.5에 3종 gap 모두 emit 조건 명시. 예: `deep_decision_score >= 2` → `ARCHITECTURE_COVERAGE_LOW`, `external_stack_score >= 3 AND no web_refs` → `HIGH_RISK_CAPABILITY_MISSING`, `operational_risk_score >= 3 AND no web_refs` → `MULTI_CLIENT_MISSING`.

#### 4. [ACCEPT] [High] `fresh_lookup`이 기존 sufficiency gate에 의해 차단될 수 있음
- **Critic**: not flagged
- **Cross**: `core/researcher.py:519-529`에서 `_collect_web_references()`는 `if not sufficient` 가드 안에서만 호출됨. local-heavy repo는 `fresh_lookup`으로 분류되어도 Tavily 스킵 가능.
- **Judgment**: 라인 인용까지 명확. 설계의 mode-aware gating 약속과 기존 코드의 sufficiency 가드가 충돌.
- **Action Required**: §5에 `research_plan.requires_web` overrides `_is_sufficient()` 명시. 회귀 테스트 (local refs sufficient + freshness keywords → web 강제) Phase 1a 진입 항목에 추가.

#### 5. [ACCEPT] [High] `content_full`이 LLM prompt/JSON downstream에 누설
- **Critic**: not flagged
- **Cross**: `core/researcher.py:692-694`가 `web_refs[:4]`를 통째로 prompt에 주입. `core/researcher.py:595-610` `_merge_project_brief_evidence()`가 `web_references` 통째 복사. `core/bootstrap_roles.py:402` planner도 brief 통째 dump.
- **Judgment**: 코드 라인 3곳 인용으로 evidence 강함. 설계 §1.2 (3) "원문 보존"과 §6 evidence schema에서 `content_full`을 분석 전용으로 분리한 의도가 무력화됨.
- **Action Required**: `content_full`은 `research_evidence.source_pack`에만 두고, `project_brief.web_references`/planner prompt는 `source_id|title|url|excerpt|metadata`만 포함하도록 sanitizer 명시.

#### 6. [ACCEPT] [High] Runtime JSON persistence와 dataclass/enum 직렬화 경계 미명시
- **Critic**: not flagged
- **Cross**: `core/project_pipeline.py:129-137` `_write_json()`은 plain `json.dump`로 default=str 없음. `core/project_pipeline.py:680-681`에서 `research_evidence` 즉시 기록.
- **Judgment**: 코드 인용 정확. ResearchPlan dataclass와 ResearchGap enum이 evidence에 그대로 들어가면 즉시 ValueError.
- **Action Required**: §6에 `ResearchPlan.to_dict()` / `ResearchDiagnostics.to_dict()` 명시. evidence artifact는 enum `.value` string만 저장. `json.dumps(collect_project_evidence(...))` succeed 회귀 테스트 추가.

#### 7. [ACCEPT] [High] `risk_level` 산출 로직 누락
- **Critic**: §6.1·§10에 `risk_level` 필드는 있지만 §4.2.1은 계산/반환하지 않음. score → risk_level 매핑 정의 부재.
- **Cross**: not flagged
- **Judgment**: §6.1과 §4.2.1 사이 직접 대조로 evidence 충분.
- **Action Required**: §4.2.1 직후 `_compute_risk_level(scores, primary) -> Literal["low","normal","high"]` 의사코드 추가. ResearchPlan dataclass 필드 type 일람을 §11 항목 1에 명시.

#### 8. [ACCEPT] [High] §4.2 키워드와 §4.2.1 임계가 §10 예제와 quantitatively mismatch
- **Critic**: poker는 미달, lottery는 secondary 어휘 부재. v1.2 "fixture로만 calibration" 정책 하에서 v1.2 임계가 §10 두 예제를 둘 다 통과해야 함.
- **Cross**: not flagged (finding #1 보강)
- **Judgment**: Finding #1과 같은 뿌리. 별도로 잡되, 처치는 #1과 동시에.
- **Action Required**: §4.2.1 직후 worked example 표 (각 카테고리 점수 + _select_mode 출력) 첨부. Phase 1a 머지 차단 조건으로 §11에 명시.

#### 9. [ACCEPT] [High] §11 항목 6 — `core.retrieval_router/researcher/research_verifier` hiddenimports를 "(선택)"으로 표시
- **Critic**: 누락 시 frozen 빌드는 이미 깨진 상태. CLAUDE.md 정책 ("새 `core/*.py`는 af.spec hiddenimports에 반드시 추가")과 모순.
- **Cross**: not flagged (관련: Cross #6은 새 `core/research_types.py`도 af.spec 등록 요구)
- **Judgment**: af.spec 실제 상태 확인이 선결. 누락이면 "(필수)"로 변경.
- **Action Required**: af.spec 점검 → 누락이면 "(필수)" + Phase 1a 항목에 회귀픽스로 격상. Cross #6의 `core.research_types`도 같이 추가.

#### 10. [ACCEPT] [Medium] Legacy verifier gap string → enum 변환 adapter 부재
- **Critic**: not flagged
- **Cross**: `core/research_verifier.py:84-106`의 `"no_external_evidence (web or llm_prior)"` 등 free-form string. 직접 매핑하면 phased rollout/fallback에서 누락.
- **Judgment**: 코드 인용으로 evidence 충분. Phase 1a → 1b 전환기 호환성 위협.
- **Action Required**: `normalize_research_gap(raw: str) -> ResearchGap | None` 정의 후 escalation mapping 앞단에 삽입. 레거시 string fixture 포함.

#### 11. [ACCEPT] [Medium] `source_id` 안정성 (retry/escalation 후 citation validity) 미명시
- **Critic**: not flagged
- **Cross**: `core/research_verifier.py:174-175` 현재는 positional `src_{i}` fallback. 재정렬 시 citation 깨짐.
- **Judgment**: 코드 인용 정확. §6의 `source_backed_claims` 약속과 충돌.
- **Action Required**: §6에 deterministic ID (`{source_type}_{sha256(url_or_path_or_content)[:12]}`) 명시. retry merge behavior 정의 + 회귀 테스트.

#### 12. [ACCEPT] [Medium] 공유 타입을 `core/research_types.py`로 분리
- **Critic**: not flagged
- **Cross**: `ResearchGap`이 router·verifier 양쪽에서 쓰이는 cross-module 계약. router private 모듈 안에 두면 `research_verifier.py`가 router를 import해야 함.
- **Judgment**: 의존성 방향 논리 타당. Phase 1b verifier가 같은 enum을 emit하기로 한 §6.5와 일관.
- **Action Required**: §0과 §6.5에 `core/research_types.py` 신설 명시 (Mode/Gap/Plan/diagnostics dataclass). af.spec hiddenimports에 등록 (Finding #9와 묶음).

#### 13. [ACCEPT] [Medium] `mode_distance` canonical ordering 정의 부재
- **Critic**: §6.6/§12.4가 `mode_distance ≥ 2`를 KPI로 쓰지만 ordering 미정의. fast→fresh→archive→deep→live가 cost 단조 증가도 아님.
- **Cross**: not flagged
- **Judgment**: §4.1과 §6.6의 직접 대조로 evidence 명확.
- **Action Required**: §4.1 표 직후 `MODE_INDEX = {fast:0, fresh:1, archive:2, deep:3, live:4}` 정의 + `mode_distance = abs(idx[final]-idx[initial])` 명시.

#### 14. [ACCEPT] [Medium] `skill_evolution` 부착 시점/주체 미명시
- **Critic**: §4.1은 후속 분석으로 취급, §4.2.1은 별도 정책으로 명시했지만 entry point는 §11에 없음. §10 예제에는 secondary로 포함됨.
- **Cross**: not flagged
- **Judgment**: §4.2.1과 §10 사이 일관성 부재. ResearchRouter.plan()이 emit하는지 명확화 필요.
- **Action Required**: "skill_evolution은 collect_project_evidence 종료 후 capability_gap_detector가 ResearchPlan.secondary_modes에 in-place append" 명시 또는 Phase 2로 미루고 1a/1b plan() 출력에서 제외 명시.

#### 15. [ACCEPT] [Medium] evidence_fn 호출 횟수 상한 + verifier retry 의미 모호
- **Critic**: §11 Phase 1a 항목 4 `max_retries=1`이 router escalation `max retry=1`과 같은 1인지, 합쳐서 2인지 불명확. verifier 내부 retry가 LLM normalizer만인지 evidence_fn 전체인지 §9.4 미정의.
- **Cross**: not flagged
- **Judgment**: §4.4.1과 §9.4 사이 cost cap 정의 부재 — verifier·router 모두 1회씩이면 사실상 2회 상한.
- **Action Required**: §4.4.1에 "evidence_fn 총 호출 = 초기 1 + escalation ≤ 1 = 최대 2회" 명시. §9.4에 "quality-tier verifier retry는 LLM normalizer만 재호출, evidence_fn 재호출 없음" 1줄 추가.

### Summary Table

| #  | Title                                      | Severity | Verdict | Source |
|----|--------------------------------------------|----------|---------|--------|
| 1  | poker §10.1 self-reference 실패            | Critical | ACCEPT  | Critic |
| 2  | undefined secondary modes (§10.2)          | Critical | ACCEPT  | Critic |
| 3  | deep-tier gap 3종 중 1종만 emit 조건       | Critical | ACCEPT  | Critic |
| 4  | fresh_lookup sufficiency-gate 차단         | High     | ACCEPT  | Cross  |
| 5  | content_full prompt/JSON 누설              | High     | ACCEPT  | Cross  |
| 6  | dataclass/enum JSON 직렬화 경계            | High     | ACCEPT  | Cross  |
| 7  | risk_level 산출 로직 누락                  | High     | ACCEPT  | Critic |
| 8  | 키워드↔임계 §10 예제 mismatch              | High     | ACCEPT  | Critic |
| 9  | af.spec hiddenimports "(선택)" 표기        | High     | ACCEPT  | Critic |
| 10 | legacy gap string → enum adapter           | Medium   | ACCEPT  | Cross  |
| 11 | source_id 안정성 (retry/escalation)        | Medium   | ACCEPT  | Cross  |
| 12 | core/research_types.py 분리                | Medium   | ACCEPT  | Cross  |
| 13 | mode_distance ordering 정의                | Medium   | ACCEPT  | Critic |
| 14 | skill_evolution 부착 시점/주체             | Medium   | ACCEPT  | Critic |
| 15 | evidence_fn 호출 상한 + verifier retry     | Medium   | ACCEPT  | Critic |

### Recommendations

문서 v1.3 진입 전 다음 순서로 처리:

1. **알고리즘 self-reference 증명 (Findings #1, #2, #3, #8)** — §4.2.1 직후 §10.1·§10.2 worked example 표 첨부. v1.2 키워드/임계로 expected_mode produce 못 하면 키워드/임계 같이 조정 (Phase 1a 머지 차단 조건). §10.2 undefined secondary 어휘 정리. §4.4.5 emit 조건 3종 모두 명시.
2. **데이터 계약 명시 (Findings #6, #7, #11, #12)** — `core/research_types.py` 신설하고 `ResearchPlan.to_dict()`/`ResearchDiagnostics.to_dict()`/`ResearchGap` 모두 거기 둠. dataclass 필드 type 일람 + risk_level 산출 + source_id deterministic 생성 규칙 한 절에 묶음.
3. **기존 코드 통합 가드 (Findings #4, #5, #10)** — §5에 mode-aware gating override 명시 + sanitizer + legacy gap string normalizer. 회귀 테스트 3건 Phase 1a 항목에 추가.
4. **빌드/KPI/cost cap 보강 (Findings #9, #13, #14, #15)** — af.spec hiddenimports 점검 후 "(필수)" 격상 + `core.research_types` 추가. mode_distance ordering 정의. skill_evolution 부착 entry point 명시. evidence_fn 총 호출 상한 명문화.
5. **재리뷰** — v1.3 작성 후 af-cross-review 1회 추가 발화 (max_rounds=2 캡 내). poker/lottery worked example이 통과하면 PASS 가능.
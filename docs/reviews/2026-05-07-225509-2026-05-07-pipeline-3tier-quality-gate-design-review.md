# Design Review: 2026-05-07-pipeline-3tier-quality-gate

> Source: docs/2026-05-07-pipeline-3tier-quality-gate.md
> Date: 2026-05-07 22:55
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

다수의 Critical 발견사항이 코드 사실과 충돌합니다. 설계 문서를 수정하기 전까지 구현 금지.

### Aggregated Findings (16 total)

#### 1. [ACCEPT] [Critical] `_refine_document` 위치 오기 (review_report.py:1031 → work_item_generator.py:889)
- **Critic**: §3.6/§3.2가 가리키는 `review_report.py:1031`에는 함수가 없음. `_refine_document`는 `core/work_item_generator.py:889`에 정의되어 있고, project_pipeline.py:1031도 그쪽에서 import.
- **Cross**: 같은 파일/라인 확인 (Cross #3 evidence).
- **Judgment**: 코드 grep으로 양쪽 일치. §3.6 옵션 A의 "WorkItemGenerator만 재실행"이라는 설명도 실제 함수 동작(LLM에 한 문서 넘겨 부분 수정)과 다름.
- **Action Required**: §3.6/§3.2의 인용 위치를 `core/work_item_generator.py:889`로 정정. "WorkItemGenerator 재실행" 표현을 "_refine_document로 문서 단위 부분 수정"으로 정확히 다시 기술.

#### 2. [ACCEPT] [Critical] `fix_instructions` 데드 필드 + T1 retry 계약 부재
- **Critic**: `JudgeResult.fix_instructions`는 `core/review_report.py:50`에 선언만, 채우는 곳 0건. `project_pipeline.py:1031`에서만 소비. raw_output→dict 파서 부재.
- **Cross**: `run_structural_gate` 반환 계약에 `fix_instructions` 없음 (project_pipeline.py:283). `_refine_document`는 문자열 feedback만 받음.
- **Judgment**: 두 리뷰어가 같은 결함을 다른 각도에서 확인. retry 매개체가 코드 어디에도 없음.
- **Action Required**: ① judge raw_output → fix_instructions dict 파싱 경로를 §3에 명시 설계 항목으로 추가, 또는 ② T1 결과 스키마를 새로 정의(`{"pass": bool, "fix_instructions": {filename: feedback}}`), 또는 ③ T1은 retry 없이 BLOCK/WARN만 하도록 범위 축소.

#### 3. [ACCEPT] [Critical] `provider_detect.fan_out(exclude_self=...)` 가공 API
- **Critic**: `core/provider_detect.py`의 public API는 `detect_provider_states()`/`invalidate_cache()` 뿐. `--exclude-self`는 argparse CLI alias.
- **Cross**: 명시적으로 다루지 않음.
- **Judgment**: Critic 단독이지만 grep으로 검증되는 사실. 데이터 흐름 다이어그램이 가상 함수에 기반.
- **Action Required**: §3.2 의사코드를 `detect_provider_states()` → AVAILABLE 추출 → critic_provider 키 제외(claude↔claude_cli alias 매핑 포함)로 다시 작성.

#### 4. [ACCEPT] [Critical] T1 rubric "4종 문서" 매핑이 실제 산출물과 불일치
- **Critic**: generator는 5종 산출(`feature-plan/spec`, **`implementation-design`**, `implementation-tasks`, `approval-gate`). approval-gate는 `ApprovalGate.initialize`가 만드는 상태 파일이지 LLM 산출물 아님 — "본문 비어있지 않음" 검사 시 false-fail.
- **Cross**: 같은 5개 라인 인용, T1 대상이 어느 4개인지 결정 필요 (HOLD).
- **Judgment**: Critic이 더 강한 정정 방향을 제시. Cross의 HOLD는 "design/tasks 중 무엇을 포함할지"의 결정 부재 때문이며, 정답은 design 포함·approval-gate 제외.
- **Action Required**: §3.4 표 대상을 `feature-plan / feature-spec / implementation-design / implementation-tasks` 4개로 정정. approval-gate 제외 명시.

#### 5. [ACCEPT] [High] RubricCompiler 신규 rule 누락 — §3.4 차원 표현 불가
- **Critic**: `_run_check`가 지원하는 rule 5종(`not_empty/min_count/all_have_owner/all_have_mitigation/grounding_ratio_min`)으로 "deliverables 커버", "엣지 키워드 ≥3", "phase/task 수 일치", "task가 spec 참조" 어느 것도 표현 못 함. NG4("새 컴포넌트 추가 금지")와 충돌.
- **Cross**: 동일. 알 수 없는 rule은 pass 처리되므로 YAML만 추가하면 false PASS (rubric_compiler.py:233).
- **Judgment**: 두 리뷰 모두 동일 file/line 인용. Both ACCEPT.
- **Action Required**: §3.3.3에 신규 rule명 명시(`required_documents_present`, `deliverables_covered_by_acceptance`, `keyword_count_min`, `phase_task_count_consistent`, `tasks_reference_spec_sections`)+ 입력 shape 문서화. NG4 문구도 "새 rule 추가 허용"으로 수정.

#### 6. [ACCEPT] [High] NG1 위반 — `detect_providers` 의미 변경이 watcher에 즉시 영향
- **Critic**: `scripts/design_review_watcher.py:214`도 같은 함수 호출 → auth-ping/cache 동작이 watcher에 누설.
- **Cross**: 동일 라인 인용. `DocumentReviewSession`만 새 함수 쓰도록 분리 권고.
- **Judgment**: Both ACCEPT, 해법까지 일치.
- **Action Required**: 새 함수(`detect_authenticated_providers()` 또는 `detect_review_providers(auth_check=True)`) 추가. `DocumentReviewSession`만 새 함수 사용. NG1 유지.

#### 7. [ACCEPT] [High] SKIP/BLOCK verdict가 project_pipeline에서 잘못 집계됨
- **Critic**: 명시적으로 다루지 않음.
- **Cross**: project_pipeline.py:1013은 PASS만 성공 처리, :1022는 마지막 라운드를 전부 WARN으로 만듦. SKIP/BLOCK 처리 누락.
- **Judgment**: Cross 단독이지만 라인 수준 evidence로 검증된 결함. 새 verdict 도입은 호출자 변경이 필수.
- **Action Required**: §3.3 변경 항목에 `project_pipeline.py:1013/1022` 분기 수정 추가 — `SKIP→{verdict:"SKIP", confidence:0.0, provider_count:0}`로 통과 저장, `BLOCK→report.save() 후 준비 단계 중단`.

#### 8. [ACCEPT] [High] T1 FAIL→BLOCK이 rubric 부재 시 default-pass로 떨어짐
- **Critic**: `RubricCompiler._load_rubric_for_type`가 매칭 못 찾으면 `total_score=0.65, status=pass_with_warnings` (rubric_compiler.py:64-71). `rubrics/work_item_doc_set.yaml` 부재 시 T1은 절대 FAIL 안 남.
- **Cross**: 명시 안 함 (Cross #4의 일부와 인접).
- **Judgment**: Critic 단독이지만 코드 사실. 이 결함이 빠지면 새 T1이 무력화됨.
- **Action Required**: §3 변경 항목에 `rubrics/work_item_doc_set.yaml` 신규 추가 명시 + "rubric 미발견 시 fail-closed/fail-open" 결정 박기.

#### 9. [ACCEPT] [High] Rubric 임계값 스케일 불일치 (normalized 0.7 vs raw 1-5 평균)
- **Critic**: 명시 안 함.
- **Cross**: `total_score`는 0~1 normalized이지만 status 판정은 `weighted_avg >= pass_threshold` (raw 1-5). YAML에 `pass: 0.7` 넣으면 거의 항상 pass (rubric_compiler.py:95,99).
- **Judgment**: Cross 단독이지만 라인 수준 evidence로 검증. 설계가 문서대로 구현되면 false PASS.
- **Action Required**: §3.4를 raw threshold(`pass: 3.8`, `warn: 3.0` 등)로 다시 쓰거나, RubricCompiler를 normalized 모드로 전환(+회귀 테스트).

#### 10. [ACCEPT] [High] AF_LLM_JUDGE / AF_LLM_JUDGE_LEVEL 환경변수 부재 — 롤백 경로 가짜
- **Critic**: grep 결과 0건. 실제 분기는 `pipeline_level` (project_pipeline.py:987).
- **Cross**: 명시 안 함.
- **Judgment**: Critic 단독, grep으로 검증.
- **Action Required**: §6을 실제 신호(`pipeline_level`/`AF_SKIP_PROVIDER`/`AF_PROVIDER_CACHE_TTL`)로 다시 쓰거나, 새 env var 도입 시 §3 변경 항목에 추가.

#### 11. [ACCEPT] [High] AUTH_EXPIRED 부분 만료 시 BLOCK 미발생
- **Critic**: 제안 분기는 AVAILABLE=0일 때만 BLOCK 검사. `AVAILABLE=1 + AUTH_EXPIRED=1` 케이스에서 SKIP으로 통과 — 개발 환경 정책("1개 이상 만료 시 BLOCK")과 모순.
- **Cross**: 명시 안 함.
- **Judgment**: Critic 단독이지만 §3.3.2.B 분기 순서를 직접 인용해 검증.
- **Action Required**: §3.3.2.B 분기를 `len(blocked) >= 1` 우선 BLOCK으로 변경 — providers 비었는지 여부와 독립.

#### 12. [ACCEPT] [Medium] §3.3.2.C ↔ §3.6 ↔ project_pipeline.py:1003 retry 횟수 충돌
- **Critic**: §3.6은 max 1회, §3.3.2.C는 enterprise=2 유지, 코드는 enterprise=2 사용. 세 곳 정합 안 됨.
- **Cross**: 명시 안 함.
- **Judgment**: Critic 단독, 세 위치 모두 인용으로 검증.
- **Action Required**: 한 곳으로 통일 — 권장: "T1/T2/T3 각자 1회 retry, level과 무관" + §3.3.2.C / §3.6 / `max_rounds` 기본값 모두 일관되게 정정.

#### 13. [ACCEPT] [Medium] artifact 형식 변환 — work_item 경로 dict→RubricCompiler 입력 헬퍼 미설계
- **Critic**: 한 줄 주석으로 미룸. 본문을 읽어와도 평가 가능한 스키마 비어 있음.
- **Cross**: Finding #4와 인접하지만 별도로 명시 안 함.
- **Judgment**: 설계가 한 줄 주석으로 핵심 변환을 미룸 — Finding #5와 결합 시 구현 가능성 차단.
- **Action Required**: §3.3.3에 artifact dict 스키마 명시(`{"feature_plan": str, "feature_spec": str, "impl_design": str, "impl_tasks": str, "project_brief": dict}`) + §3.4에 각 dimension의 evidence_check가 어떤 키 위에서 작동하는지 의사코드 추가.

#### 14. [ACCEPT] [Medium] cold-cache ping 비용(최대 30s × 3) UX 노출 미명시
- **Critic**: `_PING_TIMEOUT_SEC = 30`, 캐시 미스 시 work-item 생성 직후 T3에서 사용자 무진행 표시 30초 대기.
- **Cross**: 명시 안 함.
- **Judgment**: Critic 단독이나 코드 상수와 호출 시점으로 검증.
- **Action Required**: §1.1/§3.2에 "cold-cache 시 최대 30s 추가 latency" 명시 + 워밍업 위치(work-item 생성 직전 vs T3 진입) 결정.

#### 15. [ACCEPT] [Medium] `DocumentReviewSession`이 workspace를 wrapper에 미전달
- **Critic**: 명시 안 함.
- **Cross**: review_report.py:284,295가 workspace 인자 미전달, wrapper는 `workspace or "."` (review_runner.py:191). cwd ≠ workspace이면 prompt 로드 실패.
- **Judgment**: Cross 단독이지만 라인 수준 검증. 프로덕션 통합의 선행 수정.
- **Action Required**: §3 변경 항목에 `run_critic_review`/`run_cross_review` 호출에 `workspace=self.workspace` 전달 추가.

#### 16. [REJECT] [Low] af.spec hidden import 누락 우려
- **Source**: Cross (자체 reject)
- **Original Finding**: provider_detect.py가 frozen build에서 누락될 가능성.
- **Rejection Reason**: 이미 `af.spec:71`에 `core.provider_detect`, `af.spec:166`에 `core.review_report`/`core.review_runner` 등록됨. 이번 설계 범위에서 차단 이슈 아님.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_refine_document` 위치 오기 | Critical | ACCEPT | Both |
| 2 | fix_instructions 데드 + T1 retry 계약 부재 | Critical | ACCEPT | Both |
| 3 | provider_detect.fan_out 가공 API | Critical | ACCEPT | Critic |
| 4 | T1 rubric 4종 문서 매핑 불일치 | Critical | ACCEPT | Both |
| 5 | RubricCompiler 신규 rule 누락 (NG4 충돌) | High | ACCEPT | Both |
| 6 | NG1 위반 — watcher 영향 | High | ACCEPT | Both |
| 7 | SKIP/BLOCK verdict 호출자 미반영 | High | ACCEPT | Cross |
| 8 | T1 FAIL이 rubric 부재로 default-pass | High | ACCEPT | Critic |
| 9 | Rubric 임계값 스케일 불일치 | High | ACCEPT | Cross |
| 10 | AF_LLM_JUDGE env var 부재 | High | ACCEPT | Critic |
| 11 | AUTH_EXPIRED 부분만료 BLOCK 미발동 | High | ACCEPT | Critic |
| 12 | §3.3.2.C ↔ §3.6 ↔ 코드 retry 횟수 충돌 | Medium | ACCEPT | Critic |
| 13 | artifact dict→RubricCompiler 헬퍼 미설계 | Medium | ACCEPT | Critic |
| 14 | cold-cache 30s latency 미명시 | Medium | ACCEPT | Critic |
| 15 | DocumentReviewSession workspace 미전달 | Medium | ACCEPT | Cross |
| 16 | af.spec hidden import 우려 | Low | REJECT | Cross |

### Recommendations

구현 진입 전 다음 8가지를 설계 문서에 반영:

1. **§3.6/§3.2 인용 위치 정정** — `core/work_item_generator.py:889` + 함수 동작 정확화 (Finding 1)
2. **T1 retry 계약 명시** — fix_instructions 생산 경로 설계 OR T1 retry 범위 축소 (Finding 2)
3. **§3.2 데이터 흐름 의사코드 재작성** — `detect_provider_states()` 기반, alias 매핑 포함 (Finding 3)
4. **§3.4 대상 문서 4종 정정** — `feature-plan/spec/design/tasks`. approval-gate 제외 (Finding 4)
5. **§3.3.3 RubricCompiler 신규 rule 명시 + NG4 수정 + artifact dict 스키마 정의 + 의사코드** (Finding 5, 13)
6. **`detect_authenticated_providers()` 신규 함수 분리** — watcher와 격리, NG1 유지 (Finding 6)
7. **`project_pipeline.py:1013/1022` SKIP/BLOCK 처리 명시 + AUTH_EXPIRED 우선 BLOCK + AF_LLM_JUDGE 대체 신호** (Finding 7, 10, 11)
8. **rubric YAML 추가 + raw 1-5 임계값 사용 + workspace 전달 + cold-cache UX + retry 횟수 단일화** (Finding 8, 9, 12, 14, 15)

총 16건 중 14건 ACCEPT (Critical 4 + High 7 + Medium 3), 1건 자체 REJECT, HOLD 0건. **다음 라운드는 위 8개 항목이 모두 반영된 v2 설계 문서로 재검증 권장.**
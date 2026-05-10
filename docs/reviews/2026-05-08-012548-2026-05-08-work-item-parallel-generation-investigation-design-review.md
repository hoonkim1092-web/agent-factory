# Design Review: 2026-05-08-work-item-parallel-generation-investigation

> Source: docs/2026-05-08-work-item-parallel-generation-investigation.md
> Date: 2026-05-08 01:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Critical race-condition finding (`run_id` 공유로 인한 세션 상태/`.claude/settings.local.json` last-write-wins) is independently confirmed by both reviewers and must be resolved before any Option B 시범 구현. 추가로 5건의 High 이슈가 §4 검증 절차의 유효성을 무력화하므로, 검증 자체가 거짓 결론을 만들 위험이 있다.

### Aggregated Findings (15 total)

#### 1. [ACCEPT] [Critical] `run_id` 공유로 인한 세션 상태 race condition
- **Critic**: `_generate_doc_with_llm` (`core/work_item_generator.py:526-527`)이 `run_id` 없이 호출 → 4개 호출 모두 default `"claude_cli_run"`로 정규화 → `_runtime_paths` 동일 `state_path`/`events_path` 반환, `_save_json`/`_write_claude_settings`가 lock 없이 last-write-wins.
- **Cross**: 동일 — `execute_document_prompt()` `requirement_llm.py:173`에서 `run_id` 그대로 전달, `prepare_cli_session()`이 빈 값에서 `"{provider_id}_run"`로 폴백, file lock 없음.
- **Judgment**: 양 리뷰어가 같은 코드 경로를 다른 각도에서 짚음. 실코드 file:line 인용도 일치. 가장 위험한 fail mode (hook 손상)는 critic이 추가로 짚었음.
- **Action Required**: §4 Step 2를 다음 순서로 재구성 — (a) `execute_document_prompt`/`_generate_doc_with_llm` 시그니처에 `run_id={base_run_id}:work_item:{doc_type}` 강제 주입, (b) `.claude/settings.local.json` 사전-1회 등록 또는 `core/file_lock.py`로 cross-process lock, (c) 테스트는 `runtime/cli_sessions/claude_cli_*.json` 4개가 doc_type별로 분리 생성됨을 assert.

#### 2. [ACCEPT] [High] §4 Step 2 스모크 테스트가 실 실패 모드 미측정
- **Critic**: `'1+1=?'` 류 짧은 프롬프트는 race window 거의 안 열림. `result['ok']`만 보면 state_path 손상/hook 누락 보이지 않음.
- **Cross**: not flagged.
- **Judgment**: 단독 지적이지만 finding #1 채택 시 testing methodology에 직결. 수치적 근거(120s timeout vs 수 ms 응답) 강함.
- **Action Required**: 실제 work-item 프롬프트(또는 ~2KB 동급)로 교체, 검증 항목 3종 강제 — (a) ok=True ×4, (b) `cli_sessions/*.json` task_preview 4개 모두 다름, (c) hook entry 개수가 단일 호출 후와 동일.

#### 3. [ACCEPT] [High] 4-병렬은 worst-case 실제로 12-병렬
- **Critic**: `_generate_and_refine` (`work_item_generator.py:834-870`)의 `_PLACEHOLDER_REFINE_MAX = 2`로 문서당 1~3 LLM 호출. Option B는 동시 4~12 호출.
- **Cross**: not flagged.
- **Judgment**: 코드 상수 직접 인용, 정량적. 단독이지만 reject 이유 없음.
- **Action Required**: §3 Option B 설명에 동시 호출 수 범위 명시. §5 임계에 rate-limit fallback 발생 시 토큰 예산 영향 측정 추가.

#### 4. [ACCEPT] [High] Option B/C의 입력 의존을 과소집계 — task_board + 정합성 cyclic
- **Critic** (#4): `_generate_feature_spec` (`:576-611`), `_generate_implementation_tasks` (`:654-694`)는 `task_board`도 입력. "project_brief만"은 부정확.
- **Cross** (#3): `implementation-tasks`는 spec과 병렬 시 §N 참조 불가능 — rubric traceability 직격타.
- **Judgment**: 동일 영역(Option B/C 공통 입력)을 다른 각도에서 짚음. 둘 다 ACCEPT.
- **Action Required**: Option B 정의를 "공통 입력 = `project_brief + role_plan + task_board`, prev_doc만 제거"로 수정. Option C는 Stage 2를 spec→tasks 순차로 두는 변형 추가, 또는 사전 outline 생성 단계 추가. §5의 "rubric 점수 하락 < 0.5" 임계 재교정.

#### 5. [ACCEPT] [High] Timeout 수치가 실코드와 불일치
- **Critic**: `execute_document_prompt` default `timeout_sec=120` (`requirement_llm.py:178`), 그러나 `CliChatRequest.effective_timeout_sec` (`cli.py:42`)가 0이면 `_default_cli_timeout_sec()=900`로 폴백. `doc_gen_deadline=300`은 5b~5d **합산** deadline.
- **Cross**: not flagged.
- **Judgment**: 단독이지만 file:line + 의미 분석 강함. §3 시간 추정의 기반이라 신뢰도 직결.
- **Action Required**: §2 Q3을 "단일 호출 timeout=120s, 5b~5d 합산 deadline=300s, fallback 시 900s"로 재기술. §4 Step 4 비교표에 "timeout-fallback 발생 횟수" 컬럼 추가.

#### 6. [ACCEPT] [High] Deadline/fallback 의미론 미명세
- **Critic**: not flagged (관련 정보는 #5에 흡수).
- **Cross**: `doc_gen_deadline = time.time() + 300` (`work_item_generator.py:764`) 검사가 779/791/803에 있어 plan 외엔 deadline 초과 시 fallback. 병렬화 시 per-doc timeout/global deadline/이미 실행 중인 future 처리/fallback 순서 미정.
- **Judgment**: #5와 다른 축(시간 절대값 vs 동작 의미). 별도 ACCEPT.
- **Action Required**: §3에 per-doc timeout vs global deadline 의미 명시. `as_completed` + `execute_document_prompt(timeout_sec=remaining)` + 실패 시 per-doc fallback 절차 기술.

#### 7. [ACCEPT] [High] T1 재시도(refine) 부작용을 품질 비교에서 누락
- **Critic**: not flagged.
- **Cross**: `prepare_documents()` 가 T1 실패 시 `_refine_document()`로 work-item md 재작성 (`project_pipeline.py:999`).
- **Judgment**: 단독이지만 코드 직접 인용, 비교 메트릭의 정의 자체에 영향.
- **Action Required**: §4 Step 4 비교표를 "raw 출력 점수 / T1-후 점수 / total 시간(retry 포함)" 3종으로 분리. 의사결정 기준 어디에 적용할지 §5에 명시.

#### 8. [ACCEPT] [Medium] 병렬 생성 관측성 미명세
- **Critic** (#9): provider failover 시 4종 문서가 서로 다른 모델 산출물이 될 수 있음 — 비교표에 provider 분포 컬럼 필요.
- **Cross** (#5): `_generate_doc_with_llm`이 `used_fallback`을 폐기, `execute_document_prompt`에 elapsed/token 정보 없음. `DocGenerationResult` 구조체 도입 권고.
- **Judgment**: 같은 영역(병렬 호출 가시성). Cross가 더 구체적 솔루션 제시.
- **Action Required**: `DocGenerationResult { doc_type, provider_id, model, elapsed_sec, used_fallback, refine_attempts, errors }` 정의. §4 Step 4 비교표에 provider 분포 컬럼 추가.

#### 9. [ACCEPT] [Medium] Frozen build (`af.exe`) 호환성 미점검
- **Critic**: `prepare_cli_session`이 frozen 환경에서 `_write_claude_settings` 우회 (`session_adapter.py:474, 476`). hook 미등록 상태 4-병렬 시 EventBus 미수신 발생 가능.
- **Cross**: not flagged.
- **Judgment**: 단독이지만 CLAUDE.md 빌드 경로 고려 시 타당.
- **Action Required**: §4 Step 3에 source 경로와 `dist/af/af.exe` 양쪽 smoke 수행 추가.

#### 10. [ACCEPT] [Medium] §4 Step 1 명령이 prev_doc 의존도를 정량화 못 함
- **Critic**: `_generate_feature_spec`이 `prev_plan`을 plain text로만 삽입 (line 591). prompt에 phase 구조 일치 강제 룰 없음 — 정량 측정 없이 분석만으론 의사결정 불가.
- **Cross**: not flagged.
- **Judgment**: 단독이지만 검증 방법론에 직결.
- **Action Required**: Step 1을 "동일 brief × 5쌍 생성 후 `phase_count_match` 분포 측정"으로 교체.

#### 11. [HOLD] [Medium] 토큰 사용량 메트릭 가용성 불명
- **Critic**: not flagged.
- **Cross**: CLI/API doc 생성 모두 token usage 미반환. 다른 telemetry 레이어 존재 여부 미확인.
- **Judgment**: Cross도 HOLD로 처리. 정보 부족.
- **Question for Author**: `execute_document_prompt()` 응답 어딘가에 provider별 token usage가 기록되는가? 없으면 prompt/response 문자수로 대체 가능한가?

#### 12. [REJECT] [Low] approval-gate 초기화의 snapshot race
- **Source**: Cross (자체 reject)
- **Original Finding**: 다른 문서 생성 중 approval-gate 초기화 시 부분 파일 snapshot 위험.
- **Rejection Reason**: `ApprovalGate.initialize()`는 빈 review-pending gate만 작성, hash snapshot은 `approve()`에서 계산 (`approval_gate.py:91, 193`).

#### 13. [REJECT] [Low] researcher.py:958 인용 부적절
- **Source**: Critic
- **Original Finding**: `researcher.py:958`의 ThreadPoolExecutor는 동일 provider 동시호출 사례가 아니라 서로 다른 함수의 2-way 병렬화 — 안전성 선례로 부적절.
- **Rejection Reason**: 사실 자체는 맞지만 finding #1이 동일 영역(CLI 동시성 안전성)에서 더 강한 증거로 ACCEPT됨. 중복 가치 낮음.
- **Note**: 문서 정확성 차원에서 §2 Q2의 인용은 제거하거나 단서를 다는 것이 좋음 — 별도 액션은 아님.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | run_id 공유 race condition | Critical | ACCEPT | Both |
| 2 | Step 2 스모크가 실 실패 모드 미측정 | High | ACCEPT | Critic |
| 3 | worst-case 12-병렬 (refine loop) | High | ACCEPT | Critic |
| 4 | task_board 입력 + traceability cyclic | High | ACCEPT | Both |
| 5 | timeout 수치 실코드 불일치 | High | ACCEPT | Critic |
| 6 | deadline/fallback 의미론 미명세 | High | ACCEPT | Cross |
| 7 | T1 retry 부작용 비교 누락 | High | ACCEPT | Cross |
| 8 | 관측성/메트릭 미명세 | Medium | ACCEPT | Both |
| 9 | frozen build 호환성 | Medium | ACCEPT | Critic |
| 10 | Step 1 정량화 부족 | Medium | ACCEPT | Critic |
| 11 | 토큰 사용량 메트릭 가용성 | Medium | HOLD | Cross |
| 12 | approval-gate snapshot race | Low | REJECT | Cross |
| 13 | researcher.py:958 인용 | Low | REJECT | Critic |

### Recommendations

구현 진입 전 §4를 다음 순서로 재작성:

1. **Step 0 (신규)**: `execute_document_prompt`/`_generate_doc_with_llm`/4개 generator에 `run_id={base}:work_item:{doc_type}` 전파 경로 보강. `.claude/settings.local.json` cross-process lock 또는 사전-1회 등록.
2. **Step 1 재정의**: prev_doc 의존도 정량 측정 — 동일 brief × 5쌍, `phase_count_match` 분포.
3. **Step 2 재정의**: 실제 work-item 길이 프롬프트로 4-병렬 smoke, 검증 3종 assert(ok×4 / state file 4종 분리 / hook 개수 보존).
4. **Step 3 보강**: source + `dist/af/af.exe` 양쪽 실행. Option B의 동시 호출 수 4~12 명시. Option C는 Stage 1=plan, Stage 2=spec & design 병렬, Stage 3=tasks 변형도 비교군에 포함.
5. **Step 4 비교표 확장**: 컬럼 추가 — `timeout-fallback 횟수`, `provider 분포`, `raw vs T1-후 점수`, `total 시간(retry 포함)`. 토큰 사용량은 가용성 확인 후 결정(finding #11).
6. **§3 입력 정의 수정**: Option B 공통 입력 = `project_brief + role_plan + task_board`. §5의 "rubric 하락 < 0.5" 임계 재교정.
7. **`DocGenerationResult` 구조체 정의**: `doc_type/provider_id/model/elapsed_sec/used_fallback/refine_attempts/errors`. `_generate_*`가 이를 반환하고 pipeline이 로깅.
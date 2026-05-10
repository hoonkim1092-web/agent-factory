# Design Review: 2026-05-08-work-item-parallel-option-c-design-v2

> Source: docs/2026-05-08-work-item-parallel-option-c-design-v2.md
> Date: 2026-05-08 14:24
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

Multiple High findings accepted across both reviewers. No Critical (BLOCK-level) findings confirmed. Implement with caution after addressing High items.

---

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [High] Refine loop exceeds Stage 2 budget AND breaks "max 2 concurrent LLM" invariant
- **Critic**: design 267s + refine 2×120s = 507s > 400s budget. `cancel_futures=True`는 실행 중 스레드 미중단. refine attempt 2가 t≈782s까지 살아있다.
- **Cross**: timeout fallback 후 not_done future 지속 실행 중 Stage 3 시작 → 동시 호출 3+개 가능. 설계가 "최대 2개" 불변식을 선언하지만 enforced 경로가 없다.
- **Judgment**: 두 리뷰어가 동일 코드 경로(not_done future + Stage 3 즉시 진입)를 다른 각도에서 독립 발견. 실측 수치(267s + 2×120s)가 산술적으로 명확.
- **Action Required**: `_generate_and_refine`의 refine 루프 각 iteration 전 `iter_deadline = deadline - time.monotonic()` 계산 후 해당 값을 `timeout_sec`으로 전달. Stage 3 진입 전 not_done grace wait(예: 5s) 또는 "일시적 동시 호출 >2 가능" 명시 + 모니터링 지표 추가.

#### 2. [ACCEPT] [High] `timeout_sec` end-to-end 계약이 API transport에서 단절
- **Critic**: Finding 2 맥락에서 timeout 전파 체인 단절 암시.
- **Cross**: `_call_google_api`, `_call_openai_api`, `_call_anthropic_api` 시그니처에 `timeout_sec` 파라미터 없음(`requirement_llm.py:73, 84, 95`). `execute_document_prompt` API 분기도 미전달(`requirement_llm.py:203`).
- **Judgment**: Cross가 구체적 라인 넘버로 증거 확보. 설계 §29가 "전 체인" 연결을 명시했으나 실제 코드가 불완전하다 — 설계가 구현 상태를 과도하게 가정.
- **Action Required**: `_call_*_api(..., timeout_sec: int)` 시그니처 통일을 §7 또는 §9 구현 명세에 추가. `execute_document_prompt`에서 stage 잔여시간 기반 timeout 전달 계약 명문화.

#### 3. [ACCEPT] [High] Episode Hints 주입이 Stage 재구성 설계에서 누락 — 회귀 위험
- **Critic**: not flagged.
- **Cross**: 현재 구현이 plan 생성 직후 `_build_episode_hints_section`을 append(`work_item_generator.py:764, 772`). C-3stages 설계에서 이 단계가 완전히 빠져 있어 구현 시 누락 가능성이 크다.
- **Judgment**: 라인 번호 기반 강한 증거. 현행 동작이 존재하는 주입 단계가 설계에서 누락된 것은 명백한 회귀 위험.
- **Action Required**: §2 또는 §6에 "Stage 1 완료 후 plan 결과에 Episode Hints 주입 → Stage 2 `prev_plan`으로 전달" 명시. 검증 Step에 `feature-plan.md`의 `## Episode Hints` 섹션 존재 확인 추가.

#### 4. [ACCEPT] [High] `_exec_stage1` / `_exec_stage3` 구현 명세 부재
- **Critic**: `_exec_stage2`는 §7에 전체 구현이 있으나 `_exec_stage1`, `_exec_stage3`는 pseudocode 변수명으로만 등장. Stage 3는 `spec_outline`과 `prev_design`을 동시에 전달해야 하지만 시그니처와 `spec_outline` 생성 경로가 없다.
- **Cross**: not flagged.
- **Judgment**: 설계 §6의 코드 블록에서 `_exec_stage1(deadline=deadline_1, ...)` / `_exec_stage3(deadline=deadline_3, ...)` 호출이 명시되어 있으나 정의 없음. 단일 리뷰어지만 설계 문서 내 증거가 명확.
- **Action Required**: §7a (Stage 1), §7b (Stage 3)를 §7 수준으로 추가. `_exec_stage3(deadline, design_result, spec_result, ...)` 시그니처와 `spec_outline = _extract_section_outline(spec_result.content)` 호출 위치 명시.

#### 5. [ACCEPT] [High] asyncio 이벤트 루프 차단 위험 — §14 검증 미포함
- **Critic**: `project_pipeline.execute()`가 `async def`이면 `cf.wait(timeout=400)` 호출이 이벤트 루프 스레드를 최대 400s 블록. `control/supervisor.py` heartbeat(30s)가 굶어 stall detector 120s 후 파이프라인 종료 가능.
- **Cross**: not flagged.
- **Judgment**: 단일 리뷰어지만 asyncio 기반 `dynamic_orchestrator.py`(5-concurrent) 아키텍처 근거가 구체적. `project_pipeline.py:948` 호출 컨텍스트 확인 없이 넘어갈 경우 silent failure 위험.
- **Action Required**: §3 또는 §11에 sync/async 불변식 명시. §14 Step 0에 "project_pipeline.execute() 호출 컨텍스트 확인(sync 필수 또는 run_in_executor 래핑)" 검증 단계 추가.

#### 6. [ACCEPT] [Medium] `_fallback_feature_spec` / `_fallback_impl_design` 존재 미검증
- **Critic**: 코드 리뷰 전체에서 해당 함수 미언급. `_fallback_feature_plan()`만 §12 확인. timeout 시 `NameError`로 예외 전파 위험.
- **Cross**: not flagged.
- **Judgment**: fallback 체인이 핵심 오류 경로임에도 구현 존재 확인 없이 설계에 사용된 것은 중간 위험.
- **Action Required**: 구현 전 `core/work_item_generator.py`에서 두 함수 grep 확인. 없으면 §9(M2) 수준으로 최소 구조 설계 명시.

#### 7. [ACCEPT] [Medium] 텔레메트리 저장 경로가 런타임 경로 컨벤션과 분리
- **Cross**: 세션/상태 파일은 `workspace_runtime_dir(workspace)`를 사용하지만 텔레메트리는 `Path(workspace)/runtime/work_item_telemetry`(`work_item_telemetry.py:12`). 런타임 산출물 경로 규칙이 분산.
- **Critic**: Finding 6에서 `core/continuity/runtime_paths.py` import 경로 불확실성 지적 (Cross가 `runtime_paths.py:9`로 파일 확인).
- **Judgment**: Cross가 양측 경로를 라인 번호로 확인. 컨벤션 불일치는 cleanup/검증 절차 오류로 이어질 수 있음.
- **Action Required**: `core/work_item_telemetry.py:12`를 `workspace_runtime_dir(workspace) / "work_item_telemetry"`로 통일. §9(M2) cleanup 경로도 동일 기준으로 수정.

#### 8. [HOLD] [Medium] `_PLACEHOLDER_REFINE_MAX` 현재 값 미인용 — 예산 산정 근거 불확실
- **Critic**: §6 예산 계산이 "refine 2회" 가정. 값이 3이면 worst-case 627s로 Finding 1의 누수 규모가 더 커진다.
- **Cross**: not flagged.
- **Judgment**: 값이 설계 문서에 없고 코드 확인 없이 판단 불가. Finding 1의 budget 재산정과 연동.
- **Question for Author**: `core/work_item_generator.py`의 `_PLACEHOLDER_REFINE_MAX` 현재 값은? 값이 2 초과면 Finding 1 fix와 연계해 `STAGE_BUDGET[2]` 재산정 필요.

#### 9. [ACCEPT] [Low] `_extract_section_outline` 카운트 불일치 시 복구 경로 미정의
- **Critic**: 불일치 시 경고만 로그하고 불완전 outline 반환. `expected_count=11` 하드코딩 — 템플릿 변경 시 항상 경고.
- **Cross**: not flagged.
- **Judgment**: traceability rubric(weight 0.10) 조용한 저하 위험. Low이지만 명확한 설계 결정 누락.
- **Action Required**: 불일치 시 빈 문자열 반환(outline 없음) vs 불완전 outline 반환 중 하나를 명시. `expected_count`를 spec 템플릿에서 파생하도록 변경 방향 기술.

#### 10. [ACCEPT] [Low] T1 retry `_dname` 변수 형식 미확인
- **Critic**: `_dname`이 `plan`/`spec`/`design`/`tasks` 문자열인지 파일 경로인지 불명. 경로이면 telemetry JSON의 `docs` 키와 불일치.
- **Cross**: not flagged.
- **Judgment**: Low severity지만 §11 Step 4 검증표 정합성에 영향.
- **Action Required**: 설계서에 `project_pipeline.py:1003-1020` 현재 코드 인용, `_dname` 값 형식 확정.

#### 11. [REJECT] [High] `core.work_item_telemetry` af.spec hiddenimports 누락
- **Source**: Critic
- **Original Finding**: `core/work_item_telemetry.py`가 M4 hiddenimports에서 누락.
- **Rejection Reason**: Cross가 `af.spec:76`에 `core.file_lock`, `core.cli_session_cleanup`, `core.work_item_telemetry` 세 모듈 모두 존재를 직접 확인. Critic의 전제가 현재 코드 상태와 불일치.
- **Note**: `DocGenerationResult`를 신규 파일(`core/doc_generation_result.py`)에 배치하는 경우 해당 모듈 추가 필요 — Finding 7 참조.

#### 12. [HOLD] [Medium] Stage 3 budget(110s) 적정성 판단 불가
- **Source**: Cross
- **Original Finding**: tasks 실측 없이 110s 고정. N≥3~5 brief에서 P50/P95 분포, refine 발생률, fallback 원인 분해 미측정.
- **Judgment**: 설계 §2 자체가 "측정 보류"로 명시. 측정 데이터 없이 수용/거부 불가.
- **Question for Author**: §14 Step 2의 N≥3 측정 결과가 나오기 전까지 110s는 provisional. 구현 중 fallback 비율이 >20% 이면 budget 재산정 트리거 조건 명시 요청.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Refine loop budget 초과 + 동시 호출 불변식 파괴 | High | ACCEPT | Both |
| 2 | `timeout_sec` API transport 단절 | High | ACCEPT | Cross |
| 3 | Episode Hints 주입 누락 — 회귀 위험 | High | ACCEPT | Cross |
| 4 | `_exec_stage1`/`_exec_stage3` 구현 명세 부재 | High | ACCEPT | Critic |
| 5 | asyncio 이벤트 루프 차단 위험 | High | ACCEPT | Critic |
| 6 | fallback 함수 존재 미검증 | Medium | ACCEPT | Critic |
| 7 | 텔레메트리 경로 컨벤션 분리 | Medium | ACCEPT | Both |
| 8 | `_PLACEHOLDER_REFINE_MAX` 값 미인용 | Medium | HOLD | Critic |
| 9 | outline 카운트 불일치 복구 미정의 | Low | ACCEPT | Critic |
| 10 | T1 retry `_dname` 형식 미확인 | Low | ACCEPT | Critic |
| 11 | `core.work_item_telemetry` af.spec 누락 | High | REJECT | Critic |
| 12 | Stage 3 budget 110s 적정성 | Medium | HOLD | Cross |

---

### Recommendations

구현 시작 전 필수:
- **F4 (Stage 1/3 명세)**: §7a/§7b 추가 작성 후 재검토. `spec_outline` 전달 경로 확정이 F3 (Episode Hints)와 연계.
- **F8 (`_PLACEHOLDER_REFINE_MAX`)**: `core/work_item_generator.py` grep 1회로 즉시 해소. 값이 3이면 F1 budget 재산정 필수.
- **F6 (fallback 함수)**: `_fallback_feature_spec`, `_fallback_impl_design` grep 확인. 없으면 최소 stub 설계 추가.

구현 중 병행:
- **F1 + F2 (timeout 체인)**: `_generate_and_refine`에 `deadline` 파라미터 추가 → per-iteration `iter_timeout` 계산 → `_call_*_api` 시그니처 통일 순서로 적용.
- **F3 (Episode Hints)**: Stage 1 완료 후 `plan_result.content`에 hints 주입 코드를 `_exec_stage1` 반환 직후에 위치 명시.
- **F5 (asyncio)**: `project_pipeline.py:948` 컨텍스트 확인 1회. sync이면 §3에 불변식 한 줄 추가로 완료.
- **F7 (텔레메트리 경로)**: `work_item_telemetry.py:12` 1줄 수정으로 완료.

구현 후 검증:
- F12 (Stage 3 budget): N≥3 실측 후 fallback 비율 >20% 기준으로 재산정 여부 결정.
- F8 HOLD: `_PLACEHOLDER_REFINE_MAX` 값 확인 결과에 따라 즉시 해소 가능.
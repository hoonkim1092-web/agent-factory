# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-23 KST** — R3 scope guard enforce + skills/ 격리 fix 완료 (3-Tier PASS). 다음 세션 진입점: R1 복합 증명 (worktree에서 AF multi-file 자기실행 실험) → deep-interview-pipeline §17 Step 3~4.

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # 본 repo (main 브랜치)
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb
```

그 다음 아래 "🚧 진행 중 work-item" 섹션부터 읽으면 됨.

---

## ✅ optional-id-normalization (2026-05-19) — DONE (`fb085fdb`)

`safe_id("")="skill"` 계약 버그 전체 교정. safe_optional_id() 헬퍼 신설, 22파일 116 B-site 교체.
3-Tier: af-critic PASS → af-cross-review WARN(2건 수정) → af-test-runner PASS. 브랜치: `2026-05-19-optional-id-normalization`.

---

## ✅ research coverage-gate deep-mode fix (2026-05-20) — DONE (`9e610a5d`)

`collect_project_evidence()` coverage gate가 archive_research 에서만 적용되던 구조 결함 수정.
Step A-1(checklist hoist) + A-2(llm_prior_refs) + B(escalation scores) — 신규 8테스트. 1772 PASS.
3-Tier: af-critic PASS / af-cross-review WARN(G2/G3 mock 수정 반영) / af-test-runner PASS.

---

## ✅ 완료된 주요 작업 (2026-05-17 기준)

### Research Router (설계 v1.4.1 → 코드 완성)
| 항목 | 완료 | 내용 |
|------|------|------|
| Phase 1a | ✅ (`8654ce2a`) | `core/research_router.py` 신규 + mode-aware gating + escalation |
| Phase 1b | ✅ | source_pack + 4-metric verifier + structured evidence 필드 |
| A5 Quality Gate | ✅ (`deb9195d`) | ResearchPlan 3종 필드 + `_detect_domain_hints()` |
| P3 D3c | ✅ (`19c95f6f`) | substring 매칭 + 홀덤 토큰 보강 |
| P4 QualityContract | ✅ (`10c5879b`) | WorkSpec + pack layers + ChecklistMerger |

### 인프라 Fix (F-series)
| 항목 | 완료일 | 내용 |
|------|--------|------|
| F1~F17 전체 | 2026-05-15 | CLI 디스패치, schema, 격리, workspace 분리 등 |
| F15 workspace/runtime_workspace | 2026-05-17 | project pipeline/orchestrator/FSA 전체 분리 |
| F16 test isolation | 2026-05-15 | conftest AF_DISABLE 가드 |

### Registry Write Guard (F9 시리즈)
| 항목 | 완료일 | 내용 |
|------|--------|------|
| `_write_registry()` | 2026-05-15 | F12 hardening — 최초 가드 |
| `workflow_apply()` | 2026-05-17 | WARN #2/#3 해소 |
| `_install_skill_file()` | 2026-05-17 | os.makedirs/shutil/meta.yaml/lock 전체 차단 |
| `register_built()` | 2026-05-17 | lock_skill_state 미보호 BONUS High 해소 |

### 테스트 안정화
| 항목 | 완료일 | 내용 |
|------|--------|------|
| flaky test fix | 2026-05-17 (`1f26336d`) | runtime_workspace 라우팅 테스트 PlanVerifier stub 추가 |

### 기타
| 항목 | 완료 |
|------|------|
| P4.5a Agent Model Routing defaults | ✅ |
| P4.5b runtime escalation | ✅ |
| Cross-review 비용 감축 Phase 1 | ✅ (2026-05-01) |
| Blueprint §0~§12 동기화 | ✅ 최신 |
| Work-Item 병렬화 v3.1 | ✅ (`06661764`, `19f72479`) |
| Nightly Pipeline B2-4 (owner_role YAML) | ✅ (`5cd96564`) |
| Nightly Pipeline B2-6 (global status) | ✅ (`63990a71`) |
| Cross-review 비용 감축 Phase 2-prep | ✅ (`23f3e7bc`) |
| Cross-review 비용 감축 Phase 2 full bundle | ✅ (`23f3e7bc`) — 8섹션, 100KB cap, source_hash |
| post-commit amend 루프 근본 fix | ✅ (`f5d5461d`) — pre-commit 단일화, post_edit_blueprint/code_review hook 제거 |

---

## 🔥 미구현 항목 — 실행 순서

> 순서: **A Phase 2 → A Phase 3 → A Phase 3.5(측정) → B → A Phase 4**
> 근거: 검토 루프 인프라 먼저, 기능 확장은 루프 안정 후

### A Phase 2: review_bundle 생성기 ✅ DONE (`23f3e7bc`)

**선행 필수 (Phase 2-prep)**:
| 게이트 | 내용 |
|--------|------|
| 2-prep A | `requirements.txt` + `pyproject.toml`에 `ast-grep-py>=0.30` 추가, dev 설치 확인 |
| 2-prep B | `pyinstaller_hooks/hook-ast_grep_py.py` + `af.spec` hookspath — frozen 빌드에 native lib 포함 |
| 2-prep C | `python build_exe.py` → frozen `af`에서 ASTEngine smoke test 통과 |
| 2-prep D | `core/review_bundle.py` thin wrapper API (dev + frozen 공통 진입점) |

**본체 산출물**:
- `scripts/build_review_bundle.py` — dev hook entry
- `core/review_bundle.py` — 공통 wrapper (§§ 1~8 포함: Pending Files, Git Diff, Test Gap, Related Tests, Direct Callers, Risk Flags, Prior Findings, Bundle Stats)
- `tests/test_build_review_bundle.py`
- `.af_review_queue/review_bundle.md` (자동 생성 산출물)

**핵심 제약**: 100KB cap, source_hash 무효화, caller 심볼당 max 3개
- 설계 문서: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` §Phase 2

### A Phase 3: bundle-first + extension log 강제 ✅ DONE (agent 파일에 기존 구현)

- `af-critic.md`, `af-cross-review.md`: 진입 시 bundle 먼저 읽기 + extension log 형식 강제
- Phase 2.5 tool call cap 병행 (af-critic: 20, af-cross-review: 30)
- 설계 문서: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` §Phase 3, §Phase 2.5

### A Phase 3.5: 측정 인프라 수술적 수정 ✅ DONE (`f75e01b4`)

- `compute_report()`: "T3 finding share (단순 비율, T3 고유값 ≠)" 정정 + [Phase 4 primary] 승격 + commits_with_t3<10 샘플 게이트 + 미지원 필드 명시
- `hook_runner.py`: `payload.duration_ms` → `append_metric(duration_ms=...)` 전달
- 테스트: 39 PASS (신규 3개 포함). 3-Tier: af-critic/cross-review PASS, pytest 1704 PASS

**1주 데이터 수집 후에만 Phase 4 진입** (감 기반 skip routing 금지)

### B. Research Router Phase 2 — structured evidence promotion ✅ B-1(fallback trace) · B-2 완료 · B-3 step 1-3b 완료 (step 4 후행)

> 설계: `docs/2026-04-29-research-router-structured-evidence-design.md` §11 Phase 2 (L1139-1145)
> 본질: **데이터는 이미 생성됨** — 뒤 파이프라인 소비처가 안 쓰는 게 문제. "Research Router 필드 연결"이 아니라 "structured evidence promotion".

**용어 정정 (2026-05-18 세션 분석):**
- 대상 3필드(`required_capabilities`/`verification_focus`/`skill_gap_hypotheses`)는 `ResearchPlan`(research_router.py)에 **없음**.
- 생산자는 `core/researcher.py`의 structured evidence — `_synthesize_structured_evidence()`(researcher.py:455, fresh/deep/archive 모드) + `research_project_brief()`(fast_synthesis 모드). 생산자 2개.
- `_merge_project_brief_evidence()`(researcher.py:1148-1156)가 `project_brief`에 복사하나 **`setdefault`** — brief에 값 있으면 evidence 값 미반영. 모드별 우선순위 상이.

**B-1. `work_item_generator.py`** — ✅ **fallback trace 완료** (2026-05-21)
- LLM 경로(`work_item_generator.py:631/673/727`)는 `json.dumps(project_brief)` 전체를 프롬프트에 박음 → 3필드 값은 암묵 도달 (변경 없음).
- **완료**: `_inline()` sanitizer + `_skill_gap_bullets()` dict formatter + `_structured_evidence_block()` 추가. plan/spec/design fallback `## Evidence`/`## Design Evidence` 내부 sub-bullet으로 3필드 trace 보존. 새 `##` 헤더 없음 — `_extract_section_outline(expected_count=12)` 회귀 없음.
- 회귀 테스트 12개 추가 (`tests/test_work_item_generator_structured_evidence.py`).
- **후행**: ✅ **완료 (2026-05-21)** — `_generate_feature_plan`/`_generate_feature_spec`/`_generate_implementation_design` LLM 프롬프트 Rules에 structured evidence 3필드 명시. 21 tests PASS.

**B-2. `project_task_board.py`** — ✅ **완료·push** (`dd439f73`, 2026-05-18)
- `build_project_board()`가 `project_brief`의 `verification_focus`를 verify 태스크 `acceptance`에 주입 (dedup 가드, LLM·fallback 공통 funnel).
- **Finding 1 (버그)** — `_clean_list()` 문자열 char-split 버그 수정(`isinstance` 가드) + 회귀 테스트 3건(string/list/None).
- **Finding 2 (설계 결정 = ①)** — `required_capabilities`의 build `acceptance` 주입 제거. 근거: `acceptance`는 "완료 기준"으로 소비되는데(`agent_specializer.py:93`·`work_item_generator.py:333`) `required_capabilities`는 실행 전제·스킬 조달 신호 → 의미 불일치. 정규 소비처는 B-3 `decide_reuse()` capability-gap 경로 → B-3에 위임.
- 3-Tier: af-critic / af-cross-review / af-test-runner **전부 PASS**. Blueprint §3.1+§12 갱신. tests 6건 신규.

**B-3. skill pipeline — capability-gap 死코드 복구** ← ✅ **전체 완료·push** (`9eb14577` step1-3b + 2026-05-19 step4)

> 아래 라인 좌표는 2026-05-18 재캡처 기준. **구현 진입 시 grep으로 재확인** (라인은 stale 가능 — NEXT_STEPS의 이전 좌표 `:102`/`:197-206`이 실제 `:64`/`:172`로 어긋나 있었음).

**배선은 2군데 — 둘 다 고쳐야 함. #1만 하면 死코드가 "항상 forge" 오작동으로 바뀜:**

- **#1 요구 capability 배선** — `decide_reuse()`(skill_retrieval_engine.py:64)는 `payload["required_capabilities"]`(:102)로 gap 분석(:108). 그러나 `project_pipeline.py:641` `reqs`={goal,constraints,missing_skills}만 → `_rank_candidates_for_need()`(researcher.py:172) target dict(:197)에 `required_capabilities` 없음 → 항상 `gap=None`.
- **#2 후보 capability 배선 (5라운드 분석서 발견)** — `_analyze_capability_gap(skill_meta, required_capabilities)`(:308)는 입력이 2개. `skill_meta`는 `decide_reuse:105` `candidate_meta = best.get("meta", {})`에서 옴 — 그러나 researcher candidate row(researcher.py:187-194)에 `meta` 키 없음 → `candidate_meta` 항상 `{}` → `existing=set()` → `gap_ratio=1.0` → enhance-range 후보가 전부 forge로 밀림 (단 high-confidence+verified는 `:110`에서 gap 보기 전 ranked_reuse). **데이터는 `best["capabilities"]`에 살아있음** (researcher.py:192 → `_rank_candidates:191` `row=dict(item)`로 전파, `_iter_candidates:271` dict 무변형 통과 확인) — 순수 키 불일치 버그.

**B-3 분할 (Tier3 메가 PR 금지):**
1. contract helper — `skill_gap_hypotheses`를 `safe_id(need_skill_id)` 키 dict로 정규화. **miss 시 `[]` 반환이 계약** (project-union 주입 금지 — gap_ratio 과대산정).
2. `project_pipeline.py:641` `reqs`에 `skill_gap_hypotheses` 추가. (`required_capabilities`는 `_skill_gap_capabilities_map` 계약상 소비처 없음 → `reqs` 미포함, 2026-05-18 정정)
3. `_rank_candidates_for_need()` target에 need의 `required_capabilities` 주입 — 후보의 `capabilities` 키와 충돌하지 않게 별도 키명(예: `required_capabilities` top-level) + 설명 키 동반.
3b. **(#2)** `decide_reuse:105` candidate_meta 정규화 — `best["meta"]` 없으면 `best["capabilities"]`(list)를 `{"capabilities": ...}`로 흡수. WHY 주석 명시 (researcher candidate는 capabilities를 top-level에 둠).
4. `decide_reuse` 결정 사유(`ReuseDecision.to_dict()` — `capability_gap` 이미 직렬화됨 `:39,:43`)를 `skill_manifest.json` entry에 보존. 후행 분리 가능.

**테스트 계약 (positive 필수 — forge 케이스만 짜면 #2 버그를 통과시킴):**
- 후보 capabilities ⊇ required → `missing=[]`, `gap_ratio=0.0`
- 일부 빠지면 missing 정확 계산
- `gap_ratio=0.5` 경계 — enhance(`:115` `<=0.5`) vs forge(`:121` `>0.5`) 분기 assert
- researcher candidate shape fixture로 통합 검증 — fixture는 `researcher.py:187-194` 출처 주석 명시 (stale 방지)
- `required_capabilities` 비면 점수기반 enhance 유지 (regression)

**진입 순서:** step 1~3+3b 한 묶음 (step 2 단독은 무음 no-op). step 4 후행 분리. 설계 Opus, 구현 Sonnet. **첫 작업은 코딩이 아니라 grep 좌표·payload 계약 재캡처.**

### ✅ P2-F 루프 정합 (2026-05-22) — DONE (`99498b1b`)

- `scripts/review_gate.py`: `_MAX_ROUNDS = 5` 상수 추가, 하드코딩 `< 5` → `< _MAX_ROUNDS`
- `.codex/hooks.json`: PreCompact/SessionStart/UserPromptSubmit/Stop 각 이벤트의 `hook_runner.py` 직접 호출 제거 (run.py가 위임하므로 2중 실행 방지)
- 3-Tier: af-critic WARN(advisory) / af-cross-review PASS / af-test-runner PASS (68 tests)

### ✅ G2/G4/G5 — 이미 구현 완료 확인 (2026-05-22)

코드 탐색 결과 `core/review_report.py` + `core/review_runner.py`에 **이미 모두 구현됨**:
- G2 (`review_report.py:308`): `len(providers) >= 2` → cross/judge 실행
- G4 (`review_report.py:283`): provider 0개 → `SKIP` 반환 (PASS와 메트릭 분리)
- G5 (`review_report.py:273`): `AUTH_EXPIRED` → 즉시 `BLOCK` + 재인증 안내
- 구현 커밋: `86e3ed83` (2026-05-07)

### ✅ P2-E manifest projection — 이미 구현 완료 확인 (2026-05-22)

`skill_procurer.py` 루프 내 모든 decision mode (ranked_reuse/enhance/shadow_reuse/external_install/forge)에
`reuse_decision: decision.to_dict()` 이미 포함됨 → `skill_manifest.json`에 capability_gap/confidence/rationale 기록 중.
`exact_match`는 `decide_reuse()` 미호출이므로 없는 게 정상.

### 🔜 다음 세션 진입 순서 (2026-05-22 갱신)

> **구조 결정 (2026-05-22 세션)**:
> - `deep-interview-pipeline.md` → 북극성 epic (AF가 AF를 개발하는 완성 루프 정의)
> - `af-dogfooding-infrastructure-gap-analysis.md` → epic 구현 제약/검수 체크리스트로 흡수 (grep 증거·라인 좌표 보존)
> - Phase 3.5 runbook → sidecar 운영 문서 (epic과 별도)
>
> **팩트 확인 결과 (코드 직접 grep)**:
> - G7/G8/G1 → 2026-05-21 `fix(G8/G7/G1)` 커밋에서 이미 해소됨. blocker 아님.
> - `blast_radius.required_agents()` → CLI 출력 전용, 실행 경로 미사용. minor.
> - R1 → `docs/dogfooding/2026-05-21-r1-selfrun-result.md` PASS. 최소 증명 완료.
>   단, docstring 1줄 수준 — skills/ 격리 미완(BASE_DIR 기반 57개 스킬 로드) 잔존.
>
> **실행 게이트**: R1 복합 증명 → 신규 모듈 최소 단위 착공 (6개 동시 착공 금지)

1. ✅ **Phase 3.5 runbook 문서화** (sidecar) — `docs/2026-05-22-review-metrics-phase35-runbook.md` 작성. 실행 절차·Phase 4 진입 기준 수록.
2. ✅ **`core/interview.py` artifact shape 확장** — `research_questions/`risk_hints`/`assumptions` 필드 추가. `_build_assumptions()` + `_ensure_artifact_shape()` 신설. 테스트 5개 신규. 3-Tier PASS.
3. **R1 복합 증명** — multi-file 또는 실제 기능 변경 시나리오 1회. ✅ skills/ 격리 미완 해소 완료 (AF_SELF_RUN + SKILLS_DIR 제외). 실제 실험: worktree 생성 후 `python agent_launcher.py --fsa` 실행.
4. ✅ **R3 scope guard enforce** — `_scope_guard_report()` + baseline 기반 false-positive 제거. `AF_SCOPE_GUARD_PATHS` env var로 allowlist 지정 가능. DONE (`2026-05-23`).
5. 위 완료 후 `deep-interview-pipeline.md §17 Step 3~4` (Research Brief 연결) 진입.

**보류**: `cli_hook_bridge` 미커밋 — 현재 dirty 없음, 우선순위 낮음.

---

### A Phase 4: 스마트 라우팅 (데이터 수집 후)

- Tier 3 skip 조건 결정 (T3-only accepted finding rate < 10% 기준)
- **1주 실측 데이터 없이 구현 금지**

### ✅ C. AF Dogfooding Review Safety — Follow-ups (2026-05-20) — DONE

> 설계: [docs/2026-05-20-af-dogfooding-review-safety.md](docs/2026-05-20-af-dogfooding-review-safety.md)
> 후속: [docs/2026-05-20-af-dogfooding-review-safety-followups.md](docs/2026-05-20-af-dogfooding-review-safety-followups.md) (status: DONE)

후속 4건 전부 흡수:
- ✅ **#1 P1** (`89559a8d`) `scripts/t3_classifier.py:7-9` 모듈 docstring 정정 — annotations preserved as semantic.
- ✅ **#2 P2** (`89559a8d`) `scripts/prompts/code_critic.txt:48` 프롬프트 `no` 허용 범위 좁힘 + annotation=semantic 명시.
- ✅ **#3 P3** (`d3734717`) `scripts/review_gate.py` CLI에 `--t3-required` 옵션 추가 (choices=yes/no/unknown).
- ✅ **#4 P3** (`d3734717`) `_T3_SKIP_CLASSIFIER_VERSION`을 `scripts.t3_classifier.CLASSIFIER_VERSION`에서 import하는 dual-import 패턴으로 단일소스화 — 회귀 테스트로 invariant 봉인.

### ✅ R4 Provider Priority Fix (2026-05-21) — DONE (`cf4754b9`)

`GOOGLE_API_KEY` 없을 때 gemini_cli가 claude_cli보다 먼저 시도되어 3초 낭비하는 문제 수정.
`_PROVIDER_KEY_ENVS` + `_has_required_credentials()` 추가, 정렬 키 2-tuple화.
테스트 10건. 3-Tier PASS.

### ✅ R1 Self-Run 실험 (2026-05-21) — DONE

- **결과**: AF가 자기 `.py`를 수정하는 핵심 명제 **최초 증명**
- scope: `core/utils.py` 단 1파일 수정 — scope leak 없음
- claude_cli 17초 완료 (gemini_cli 폴백 포함 ~25초)
- 마찰점: gemini 1순위 낭비(R4), 단순 작업에 57 skill 로드(노이즈), `"skill"` 오인식(무해)
- 결과 문서: `docs/dogfooding/2026-05-21-r1-selfrun-result.md`
- 실험 worktree: `r1-selfrun-exp` (수동 삭제 필요: `git worktree remove --force ...`)

### ✅ G8/G7/G1 정합화 (`529fa1a9`, 2026-05-21) — DONE

- G8: `check_design_pending.py` → "af-cross-review 1개만" (2026-05-01 정책)
- G7: `check_pending_review._agents_for_tier()` review-first 순서 + 전파 4곳
- G1: `MAX_ROUNDS 2→5` (CLAUDE.md 기준) + `review_gate.py:282` 동반
- G6: 기완료 (`82e256a7`)
- 3-Tier: af-critic PASS / af-cross-review PASS / af-test-runner PASS

---

### 🔍 C follow-up 후속 리뷰 (2026-05-20) — 4건 적용 완료, 교차검증 대기

> 코덱스 + 추가 검토. 4건 findings 중 **3건 수용 / 1건 거절**. 적용 결과: 111 tests passed.

- ✅ **#3 P0** `docs/2026-05-20-af-dogfooding-review-safety-followups.md:5` `(이 커밋)` → `d3734717` 치환.
- ✅ **#4 P1** `tests/test_review_gate.py` non-critic invariant 회귀 테스트 추가 — CLI `--record af-test-runner --t3-required yes` → `reviews[af-test-runner]`에 `t3_required` 키 없음 + `fired_at` 보존. 가드(`scripts/review_gate.py:345`) mutation 시 정상 fail 확인.
- ✅ **#1-a P2** `scripts/enqueue_agent_review.py` t3_decision=None 분기 `classifier_version` → `CLASSIFIER_VERSION` 변수 (except 분기에선 `"classifier-unavailable"` sentinel). sentinel은 `pending_agent_review.json.t3_decision.classifier_version` 필드에 forensic 마커로 남고 `reason: "classifier-unavailable"` 라벨과 일관 유지. *(주의: `t3_skip_telemetry.jsonl`은 `if decision.t3_required: return`으로 skip-only 기록이고 sentinel 분기는 t3_required=True이므로 telemetry/report 카운터에는 노출되지 않음 — af-cross-review WARN으로 사후 정정.)*
- ✅ **#1-b P2** `scripts/enqueue_agent_review.py:174` try 블록에 `CLASSIFIER_VERSION` 동시 import → stale-file-set 분기 `getattr` fallback도 동일 변수로 단일소스화. T3Decision dataclass `classifier_version: str` 필수 필드 확인.
- **#2 P? 거절** `scripts/review_gate.py:94` `ImportError` catch 확대 안 함. SyntaxError까지 sentinel로 숨기면 분류기 코드 깨짐을 hide → 진단성 저하. enqueue 측 fail-closed가 이미 SyntaxError까지 커버(`enqueue:187` `except Exception: t3_decision=None`). 상한은 `(ImportError, AttributeError)`.

**부수 변경**: `tests/test_pending_review.py` 두 fake fixture에 `CLASSIFIER_VERSION="test"` 추가 — fake 모듈이 `t3_classifier`를 위장할 때 import 호환성. (NEXT_STEPS 사전 분석에서 놓친 영향.)

**커밋 분리 권고**: #3+#4 한 커밋 / #1+fixture 별도 커밋 (enqueue 변경은 Tier 2 가능성).

---

## 📜 과거 이력 참조

- 세션별 누적 이력: [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md)
- dogfooding 마찰 F0~F17: [docs/dogfooding/round4-af-cli-friction.md](docs/dogfooding/round4-af-cli-friction.md)
- Research Router 설계: [docs/2026-04-29-research-router-structured-evidence-design.md](docs/2026-04-29-research-router-structured-evidence-design.md)

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`

# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-18 KST** — Phase 3.5 완료(`f75e01b4`) + B 설계 분석 완료. 다음 진입점: **B (structured evidence promotion)** — §B 섹션 정독 후 B-2/B-3 순서 결정부터.

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # 본 repo (main 브랜치)
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb
```

그 다음 이 파일 "🔥 다음 진입점" 섹션부터 읽으면 됨.

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

### B. Research Router Phase 2 — structured evidence promotion ← **현재 진입점**

> 설계: `docs/2026-04-29-research-router-structured-evidence-design.md` §11 Phase 2 (L1139-1145)
> 본질: **데이터는 이미 생성됨** — 뒤 파이프라인 소비처가 안 쓰는 게 문제. "Research Router 필드 연결"이 아니라 "structured evidence promotion".

**용어 정정 (2026-05-18 세션 분석):**
- 대상 3필드(`required_capabilities`/`verification_focus`/`skill_gap_hypotheses`)는 `ResearchPlan`(research_router.py)에 **없음**.
- 생산자는 `core/researcher.py`의 structured evidence — `_synthesize_structured_evidence()`(researcher.py:455, fresh/deep/archive 모드) + `research_project_brief()`(fast_synthesis 모드). 생산자 2개.
- `_merge_project_brief_evidence()`(researcher.py:1148-1156)가 `project_brief`에 복사하나 **`setdefault`** — brief에 값 있으면 evidence 값 미반영. 모드별 우선순위 상이.

**B-1. `work_item_generator.py`** — 소비 *보장* 없음 (완전 폐기 아님)
- LLM 경로(`work_item_generator.py:631/673/727`)는 `json.dumps(project_brief)` 전체를 프롬프트에 박음 → 3필드 값은 암묵 도달.
- 빠진 것: 구조적 렌더링 + fallback 문서 명시 섹션. → fallback에 명시 섹션 추가.

**B-2. `project_task_board.py`** — acceptance가 보일러플레이트
- `_task_template()`(project_task_board.py:337) verify acceptance = 일반 문구. `build_project_board()`(L590)가 `verification_focus` 미연결.
- → `verification_focus`/`required_capabilities`를 verify/build task `acceptance`에 주입. **deterministic·소규모·테스트 명확 — 저위험.**

**B-3. skill pipeline** — capability-gap 경로가 死코드 (end-to-end 계약 문제, 단일 함수 아님)
- `decide_reuse()`(skill_retrieval_engine.py:102)는 payload의 `required_capabilities`로 gap 분석 — 그러나 `_rank_candidates_for_need()`(researcher.py:197-206) target에 미포함 → 항상 `gap=None`.
- 근본: `project_pipeline.py:641-645` `reqs` = `{goal, constraints, missing_skills}`만 — `required_capabilities`/`skill_gap_hypotheses` 미전달. `_rank_candidates_for_need`만 고치면 무음 no-op.
- 네임스페이스 리스크: `skill_gap_hypotheses.need_skill_id`(research LLM) ≠ `roles[].required_skills`(`bootstrap_roles.plan()` 별도 LLM). 매칭 키 불일치 가능.
- **B-3 분할 (4단계, Tier3 파일이므로 메가 PR 금지):**
  1. contract helper — `skill_gap_hypotheses`를 `safe_id(need_skill_id)` 키 dict로 정규화. **miss 시 `[]` 반환이 계약** (project-union 주입 금지 — gap_ratio 과대산정).
  2. `project_pipeline.py:641` `reqs`에 `required_capabilities`/`skill_gap_hypotheses` 추가.
  3. `_rank_candidates_for_need()`에 hypothesis map 전달 → 매칭 need의 `required_capabilities`를 target에 주입.
  4. `decide_reuse` 결정 사유(`decision.to_dict()`/rationale/capability_gap/confidence)를 `skill_manifest.json` entry에 보존 (현재 `decision_mode/reused_from/forge_run_id/fallback_chain`만).

**진입 순서 미결 (사용자 결정 대기):** B-2 먼저(저위험 워밍업) vs B-3 contract helper 먼저(가치 최대). 설계는 Opus, 구현은 Sonnet.

### A Phase 4: 스마트 라우팅 (데이터 수집 후)

- Tier 3 skip 조건 결정 (T3-only accepted finding rate < 10% 기준)
- **1주 실측 데이터 없이 구현 금지**

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

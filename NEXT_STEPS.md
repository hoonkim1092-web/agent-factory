# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-17 KST** — Phase 2+3 완료, Phase 3.5 수술적 수정 합의. 다음 진입점: **Phase 3.5 수정 3개 → B**.

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

### A Phase 3.5: 측정 인프라 수술적 수정 ← **현재 진입점**

**수술적 수정 3개 (30~45분):**
1. `compute_report()` metric 이름 정정: "T3-only finding rate" → "T3 finding share (단순 비율, T3 고유값 ≠)"
   + `t3_block_only_commits / commits_with_t3`를 Phase 4 primary 신호로 승격
   + 샘플 부족(< 10 커밋) 시 "Phase 4 판단 불가" 명시
2. `hook_runner.py` duration_ms wall time 측정 추가
3. (tokens/tool_calls는 API 통합 없이 불가 → "미지원" 명시하고 건드리지 않음)

**True T3-unique finding rate** (structured output + dedup)는 Phase 4 이후 별도 작업으로 분류.

**1주 데이터 수집 후에만 Phase 4 진입** (감 기반 skip routing 금지)

### B. Research Router Phase 2 — 뒤 파이프라인 보강

(A Phase 3 완료 후 진입)
- `core/work_item_generator.py`: `required_capabilities`, `verification_focus`, `skill_gap_hypotheses` 반영
- `core/project_task_board.py`: acceptance criteria에 새 필드 연결
- skill pipeline: `skill_gap_hypotheses` → `SkillRetrievalEngine.decide_reuse()` 연결

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

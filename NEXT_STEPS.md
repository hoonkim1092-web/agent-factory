# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-17 KST** — 다음 진입점: F8 ContextSchema 진단 (F3 완료 확인됨) 또는 `_install_skill_file` AF_DISABLE 가드 불완전 (cross-review BONUS High) 처리.

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

## 🔥 다음 진입점 — 순서대로 진행

### ✅ Step 1: registry_manager WARN fix (완료 2026-05-17)
- `core/registry_manager.py::workflow_apply()` 에 `AF_DISABLE_REGISTRY_WRITE` 가드 추가
- `logger.debug` 일관성 보완 + 회귀 테스트 1건 추가
- 3-tier 검증 40 PASS. Blueprint §6 갱신됨.

### ✅ Step 2: F3 CLI argparse fix (이전 세션에서 완료)
- `_detect_mode` + `_build_arg_parser` 구현됨. 31 테스트 PASS.

### Step 3: `_install_skill_file` AF_DISABLE 가드 불완전 (cross-review BONUS High, ~30분)
- **파일**: `core/registry_manager.py` L205-244 `_install_skill_file()`
- **결함**: `AF_DISABLE_REGISTRY_WRITE=1` 설정에도 `shutil.copytree` (L211) + `write_yaml(target_meta, ...)` (L236) 가 글로벌 `skills/` 에 파일을 씀 → `_write_registry()` 가드만 있고 앞단이 무방비
- **호출경로**: `agent_launcher.py:55` (self-run 격리) → `skill_procurer.py:567` → `registry_manager.py:315` → L236 `write_yaml` 글로벌 오염
- **수정**: `_install_skill_file()` 진입부에 `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return False, "disabled"` 추가
- **주의**: core/ 파일 → Tier 2-3 풀 리뷰 사이클

### Step 4: F8 ContextSchema (F3 완료 확인 후 진단 필요)
- dogfooding Round 4b에서 F8 fix 확인됨. 추가 재현이 필요하면 진입.

F15 (workspace/runtime_workspace 분리)는 완전 완료.

### F15 마무리 내역 (2026-05-17 세션)

- `core/ise_loop.py` — `ISELoop.run_mission`에 `runtime_workspace` 파라미터 추가 → `FSALoop.run_mission`에 위임
- `agent_launcher.py` — single-run `fsa`/`ise` 디스패치가 `runtime_workspace=state_workspace` 전달 (`_invoke_runner` else 분기와 정합)
- `core/dynamic_orchestrator.py:875` — lineage maxed 사전검사를 `state_workspace`에서 읽도록 수정. auto-review(Codex) BLOCK Finding 1: FSA는 lineage 원장을 `state_workspace`에 기록(`fsa_loop.py:145`)하는데 사전검사가 `target_workspace`를 읽어 캡이 우회되던 버그.

### 검증 상태

- 변경 파일 직접 관련 스위트 **49 passed** (`test_fsa_runtime_workspace` 2 + `test_dynamic_orchestrator_workspace_scope` 9 + `test_ise_integration` 7 + `test_agent_launcher_cli_dispatch` 31), `py_compile` OK
- lineage 버그 재현 검증: 수정 되돌리면 `test_lineage_maxed_check_reads_runtime_workspace` FAIL 확인
- `test_project_pipeline` 6건 중 `test_project_pipeline_writes_planning_artifacts_and_roles`가 full-run에서 1회 FAIL → 단독 재실행 PASS (flaky, 실 LLM 호출 의존). 이 테스트는 `DynamicOrchestrator`를 스텁하므로 F15 변경과 무관.
- Blueprint §0/§3.1/§3.2/§12 동기화됨

---

## ✅ F15 구현 내용 — workspace/runtime_workspace 분리 (참조)

**브랜치**: `main`

### F15 핵심 결과

- `core/agent_runner.py:840-859` — `target_workspace` (사용자) / `state_workspace` (AF 내부) 분리 로직
- `agent_launcher.py:554-587` — `runtime_workspace` 파라미터 + `state_workspace` 계산
- `core/project_pipeline.py` — `prepare_brief()`, `prepare()`, `execute()`, `run()`에 `runtime_workspace` 추가. `.checkpoint/`, warning registry, strategy ledger, orchestrator runtime을 `state_ws`로 라우팅.
- `core/dynamic_orchestrator.py` — `run_project(..., runtime_workspace=...)` 추가. in-thread runner, terminal payload, manifest/runtime file을 `state_ws`로 라우팅.
- `core/fsa_loop.py` / `core/agent_worker.py` — FSA runner 호출과 터미널 worker payload에 `runtime_workspace` 전달.
- 테스트: `tests/test_project_pipeline.py`, `tests/test_dynamic_orchestrator_workspace_scope.py`, `tests/test_fsa_runtime_workspace.py`, 기존 self-run split 테스트.

### AF 내부 상태 vs 사용자 산출물 분류표

| 경로 | 분류 | 라우팅 |
|------|------|--------|
| `planning/` | 사용자 산출물 | `workspace` |
| `agents/*.yaml` | 사용자 산출물 | `workspace` |
| `.todo.md` | 사용자 산출물 | `workspace` |
| `docs/` | 사용자 산출물 | `workspace` |
| `.checkpoint/` | AF 내부 | `state_ws` |
| `.af/` | AF 내부 | `state_ws` |
| `runtime/warnings/` | AF 내부 | `state_ws` |
| `runs/`, `data/`, `artifacts/` | AF 내부 | `state_ws` |

## ✅ 완료된 것들 (이전 세션)

- **Backlog #1**: `pytest.ini pythonpath` + `ci.yml` 실제 게이트 (`a0961ebc`)
- **Backlog #2**: runtime 산출물 gitignore (`a0a44928`) — 매 세션 dirty 해소
- **test_orchestrator_manifest**: `.todo.md` 제거 → LLM 경로 강제 → dynamic_log.txt 생성 (`19f261c6`)
- **test_project_pipeline**: `PlanVerifier` stub + `AF_SKIP_ESCALATION=1` → PASSED (`e4f1e0d0`)
- **F15 설계 준비**: 코드베이스 전체 `workspace` 사용 패턴 스캔 완료
- **F15 구현**: project pipeline/orchestrator/FSA/worker까지 runtime state 분리 완료

### 잔존 backlog
- ~~**전역 싱글톤 storage가 `runtime_workspace`를 무시**~~ — **완료 (2026-05-17)**: `get_storage_for(workspace)` + `get_store_for(workspace)` workspace-keyed factory 추가. `project_pipeline.py` 3곳 + `dynamic_orchestrator.py` 2곳 모두 `state_workspace`를 인자로 전달하도록 변경. 싱글톤(`get_default_storage`/`get_default_store`) 계약은 유지 — `approval_gate`, `run_budget`, `skill_self_evolution` 미변경.
- ~~**터미널 worker I/O hygiene 기존 결함**~~ — **완료 (2026-05-17)**: result.json/crash.log 원자적 write, corrupt-result fail-fast, proc.wait() 추가. `tests/test_agent_worker.py` 3건 신규.
- **cross-review WARN #2/#3** — registry_manager pre-existing 결함
- ~~**Master_Blueprint.md hook 잡음**~~ — 별도 처리 보류 (settings.json PostToolUse 정리로 중복 발화 해소)
- ~~**훅 중복 발화**~~ — **완료 (2026-05-17)**: settings.json을 단일 진실원천으로 통합. post_edit_enqueue + post_edit_blueprint 누락 추가. settings.local.json hooks 섹션 제거.
- ~~**`test_project_pipeline_writes_planning_artifacts_and_roles` flaky**~~ — **완료 (2026-05-17)**: `monkeypatch.setattr(pp, "generate_work_items", lambda **_kwargs: {})` 1줄 추가. 19분 LLM 호출 → 4.5초 결정론적 실행.
- ~~**설계 리뷰 미해결**~~ — **완료 (2026-05-17)**: `test_sync_wrappers.py` 전면 재작성. 삭제된 `.cmd` 래퍼 Windows-only 테스트 2건 → `start_db.py`/`start_sync.py` 크로스플랫폼 테스트 14건. design review [Critical] BLOCK 해소.

---

## 📜 과거 이력

세션별 누적 이력은 [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md), dogfooding 마찰 F0~F17은 [docs/dogfooding/round4-af-cli-friction.md](docs/dogfooding/round4-af-cli-friction.md) 참고.

- Round 1~4e dogfooding (2026-05-14~05-15)
- P5 DomainVerdict / P4.5a model routing / P4.5x F3·F8 / F12 isolation+hardening / F16 test isolation / F17 workspace split — 모두 완료
- Phase A/B/C, ADR M1~M5, P1~P4, Question Router Stage 0 등 — session-log 파일 참조

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`

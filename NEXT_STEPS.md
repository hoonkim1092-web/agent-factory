# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-17 KST** — F15 완료 (project pipeline + single-run dispatch + ISE wrapper + lineage 캡 정합). 다음 진입점 = 잔존 backlog 정리.

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

## 🔥 다음 진입점 — 잔존 backlog 정리

F15 (workspace/runtime_workspace 분리)는 project pipeline + single-run dispatch + ISE wrapper + lineage 캡 정합까지 완료. 아래 "잔존 backlog"에서 우선순위를 골라 진행.

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
- **전역 싱글톤 storage가 `runtime_workspace`를 무시** — 같은 설계 결함 2곳: ① `prepare_documents()`의 `get_default_storage().save()`(checkpoint), ② `dynamic_orchestrator.py:754` `get_default_store().append(RunEvent(...))`(run event). 둘 다 `runs/`를 CWD 상대 경로로 쓰며 `AF_CHECKPOINT_DIR`를 싱글톤 초기화 전에 set해야만 override됨 → `state_ws` 라우팅 안 됨. 제대로 고치려면 storage injection 또는 run-scoped resolver 설계 필요. (auto-review Finding 2)
- **터미널 worker I/O hygiene 기존 결함** — `docs/reviews/2026-05-17-014614-dynamic_orchestrator-code-review.md` BLOCK 4건: `agent_worker.py` result.json 비원자 write, corrupt result polling 1h timeout, `dynamic_orchestrator.py` crash.log 비원자 write, timeout worker kill 후 wait 누락. 모두 F15 추가 라인이 아니라 기존 터미널 모드 안정성 결함(C2/M10/M6 계열)이며, 별도 hardening 커밋에서 원자 write + corrupt-result fail-fast + process reap으로 처리.
- **cross-review WARN #2/#3** — registry_manager pre-existing 결함
- **Master_Blueprint.md hook 잡음** — 비-코드 편집에도 §12 자동 entry 생성
- **`test_project_pipeline_writes_planning_artifacts_and_roles` flaky** — 실 LLM 호출 의존(19분 소요), full-run에서 간헐 FAIL. `work_item_generator` 경로 stub 보강 필요.
- **설계 리뷰 미해결** — `docs/reviews/2026-05-17-012959-...-test-suite-triage-handoff-design-review.md`: `docs/2026-05-16-test-suite-triage-handoff.md`에 대한 BLOCK. [Critical] `test_sync_wrappers`가 삭제된 `.cmd` 래퍼를 대상으로 함. F15와 무관 — 별도 처리.

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

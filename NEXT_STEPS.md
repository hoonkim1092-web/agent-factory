# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-16 KST** — F15 설계 준비 완료. 다음 진입점 = **F15 구현** (Sonnet으로 바로 진입 가능, Opus 불필요).

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

## 🔥 다음 진입점 — F15 구현 (바로 시작 가능)

**브랜치**: `main`

> 설계 준비 완료. 기존 패턴(`agent_runner.py` + `agent_launcher.py`)이 이미 정립되어 있어 Sonnet으로 바로 구현 진입 가능.

### F15 핵심 사실 (사전 스캔 완료)

**이미 있는 것** — `runtime_workspace` 개념은 이미 구현됨:
- `core/agent_runner.py:840-859` — `target_workspace` (사용자) / `state_workspace` (AF 내부) 분리 로직
- `agent_launcher.py:554-587` — `runtime_workspace` 파라미터 + `state_workspace` 계산
- `tests/test_agent_launcher_cli_dispatch.py:201-279` — `TestSelfRunWorkspaceSplit` 클래스 (F15/F17 계약 테스트)

**없는 것** — `core/project_pipeline.py`만 `runtime_workspace`가 없음:
```python
# 현재 (문제)
def run(self, task_input: str, workspace: str, ...) -> dict:
    # workspace 하나로 AF 내부 상태 + 사용자 산출물 모두 씀

# 목표
def run(self, task_input: str, workspace: str, runtime_workspace: str | None = None, ...) -> dict:
    state_ws = runtime_workspace or workspace
    # AF 내부 → state_ws (.checkpoint, .af, runtime/warnings)
    # 사용자 산출물 → workspace (.todo.md, docs/, planning/, agents/*.yaml)
```

### F15 구현 범위 (확정)

**변경 파일 1: `core/project_pipeline.py`**
- `run()`, `prepare()`, `execute()` 시그니처에 `runtime_workspace: str | None = None` 추가
- 내부 상태 경로는 `state_ws = runtime_workspace or workspace`로 라우팅:
  - AF 내부 → `state_ws`: `.checkpoint/`, `.af/`, `runtime/warnings/`, `runs/`, `data/`, `artifacts/`
  - 사용자 산출물 → `workspace`: `.todo.md`, `docs/`, `planning/`, `agents/*.yaml`
- 기존 helper들: `_planning_dir()`, `_checkpoint_dir()`, `_save_checkpoint()` 등도 `state_ws` 사용

**변경 파일 2: `agent_launcher.py:569-576`** — project_pipeline 호출부에 `runtime_workspace` 전달
```python
# 현재
return self.project_pipeline.run(
    task_input=task_input,
    workspace=target_workspace,
    ...
)
# 수정 후
return self.project_pipeline.run(
    task_input=task_input,
    workspace=target_workspace,
    runtime_workspace=state_workspace,  # 추가
    ...
)
```

**변경 파일 3: `tests/test_project_pipeline.py`** — 기존 테스트는 `runtime_workspace` 없이 호출하므로 호환성 확인 필요 (기본값=None이면 `workspace`로 fallback → 변경 불필요)

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

### 구현 시작 방법

1. `core/project_pipeline.py` `run()` 시그니처 수정 → `state_ws` 변수 도입
2. 내부 helper 함수들 `state_ws` 사용으로 교체
3. `agent_launcher.py:569` 호출부 `runtime_workspace=state_workspace` 추가
4. `pytest tests/test_project_pipeline.py -v` 확인

---

## ✅ 완료된 것들 (이전 세션)

- **Backlog #1**: `pytest.ini pythonpath` + `ci.yml` 실제 게이트 (`a0961ebc`)
- **Backlog #2**: runtime 산출물 gitignore (`a0a44928`) — 매 세션 dirty 해소
- **test_orchestrator_manifest**: `.todo.md` 제거 → LLM 경로 강제 → dynamic_log.txt 생성 (`19f261c6`)
- **test_project_pipeline**: `PlanVerifier` stub + `AF_SKIP_ESCALATION=1` → PASSED (`e4f1e0d0`)
- **F15 설계 준비**: 코드베이스 전체 `workspace` 사용 패턴 스캔 완료

### 잔존 backlog (낮은 우선순위)
- **cross-review WARN #2/#3** — registry_manager pre-existing 결함
- **Master_Blueprint.md hook 잡음** — 비-코드 편집에도 §12 자동 entry 생성

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

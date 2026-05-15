# Round 4: AF CLI Dogfooding — NEXT_STEPS 분리

**목표**: AF의 진짜 파이프라인(`agent_launcher.py`)으로 NEXT_STEPS 분리 작업을 위임.

**Round 1~3 와의 차이**: 이전은 Claude(주체)가 손으로 한 작업의 마찰 측정. **Round 4는 AF tool 자체를 호출한 첫 dogfooding** — Codex가 만든 AF를 Claude가 사용자로서 사용.

## 사전 조건 (2026-05-15 KST)

- Branch: `af-on-af/round1-hook-fix` (P5 + P4.5a commit 완료, `06a58d5c`)
- 환경:
  - API key: 없음 (`OPENAI_API_KEY`/`ANTHROPIC_API_KEY` 미설정)
  - CLI providers 감지: `claude_cli`, `gemini_cli`, `codex_cli`
  - Active provider setting: `claude_cli,gemini_cli,codex_cli`
- 사용자 제약:
  - 문서 변경만 허용
  - `core/*.py`, `.claude/agents/`, P4.5b, Phase C 미접촉
  - push/merge 금지

## 사용 명령

```bash
python agent_launcher.py "NEXT_STEPS.md를 현재상태(≤50줄, P5 진입점만)와 과거 라운드 이력 아카이브(docs/session-log/2026-05-15-rounds-1-2-3.md)로 분리. Round 1/2/3 종료 섹션 + P5 완료 섹션 등 과거 이력은 모두 아카이브로 이동." --mode approval --role General </dev/null
```

- `--mode approval`: 정상 파이프라인. clarification 단계 있음.
- `< /dev/null`: stdin EOF → `input()` 자동 `/skip` (agent_launcher.py:313)
- 타임아웃: 600s (Bash tool max)

## 마찰 로그 (실시간 append)

| # | 단계 | 도메인 | 내용 |
|---|------|--------|------|
| F0 | pre-flight | env | `OPENAI_API_KEY` 없음 → CLI provider 경로로 우회 시도. AF가 실제로 어떤 경로로 LLM 호출하는지는 실행해야 확인 가능 |
| F1 | pre-flight | interactive | approval mode clarification에 `input()` 다수 호출. `< /dev/null`로 EOF→`/skip` 우회. 즉 AF가 모호성을 묻더라도 자동으로 기본값 적용됨 — 의도와 다른 해석 가능성 ↑ |
| F2 | pre-flight | scope-guard | "문서만 변경" 제약을 AF가 모름. 자체 가드 없으니 후처리(`git diff`)에서 확인 + 비-문서 변경 시 abort 절차 필요 |
| F3 | launch | **차단성 — CLI 설계 결함** | `python agent_launcher.py "<task>" --mode approval` 시 argparse가 `<task>`를 subcommand로 잡아 `invalid choice: ... (choose from project)` 오류. `--` separator도 무효. 정상 사용 경로는 `inquirer.prompt` interactive TUI뿐 (`core/template_input.py`), stdin redirect 시 `sys.exit(1)`. 즉 **AF는 cmdline task 입력을 지원하지 않음**. 우회: `AgentFactory().run()` programmatic 호출 |

## 실행 로그

### Attempt 1: `python agent_launcher.py "<task>" --mode approval --role General </dev/null`
- 결과: F3 (argparse error, subcommand invalid choice)
- 소요 시간: ~즉시

### Attempt 2: `python agent_launcher.py --mode approval --role General -- "TEST" </dev/null`
- 결과: F3 동일 (-- separator 무효)
- 소요 시간: ~즉시

### Attempt 3: Programmatic wrapper (`tests/_tmp/round4_af_runner.py`)
- 방식: `AgentFactory().run(task_input=..., execution_mode='approval', role_spec='General')` 직접 호출
- 결과: AF가 부팅 + task 라우팅까지는 성공, 그러나 **실제 NEXT_STEPS 분리 작업은 실행되지 않음** (ContextSchema validation failure)
- 부작용 발생: `projects/default/` scaffolding + `skills/registry.yaml` 갱신 (의도하지 않은 변경)
- 실행 시간: ~11초 (gemini_cli 3초 실패 → claude_cli 8초 → context schema fail)

## 마찰 로그 (실행 중 발견)

| # | 단계 | 도메인 | 내용 |
|---|------|--------|------|
| F4 | LLM 호출 | provider-config | `[WARNING] No GOOGLE_API_KEY found` 9회 반복. AF가 CLI provider 감지 후에도 SDK key를 다시 묻는 코드 경로 존재 — 무해하지만 noise |
| F5 | IntentGate | fallback | Gemini SDK가 GOOGLE_API_KEY 없어 `empty_llm_response` 반환 → `IntentGate LLM Classification failed`. 다음 provider(claude_cli)로 fallback은 동작 |
| F6 | provider race | first-success | `gemini_cli` 3초 실패 → `claude_cli` 8초 성공. 의도된 다중-provider fallback이지만 매번 첫 시도 cost 발생 (총 11초) |
| F7 | skill build | gated | AF가 "markdown_split" skill 후보를 식별 → `[RunOnly] build disabled, skipping`. `--build` 플래그 없으면 신규 skill 생성 차단 (의도된 동작) |
| F8 | **차단성 — ContextSchema** | runtime | `[ContextSchema] validation failed: missing context key: missing_key` → `Agent execution stopped.` 작업 시작 못함. AF가 first-time 임의 작업에 필요한 context를 자체 채우지 못함 |
| F9 | 부작용 | scope-leak | AF가 task 실행 실패에도 불구하고 `projects/default/.claude/`, `projects/default/agents/`, `projects/default/.todo.md`, `skills/registry.yaml`, `projects/default/dashboard.json` 변경/생성. "문서만 변경" 사용자 제약 위반 |

## 결과

**AF는 NEXT_STEPS 분리 작업을 수행하지 못했다.**

차단 원인: F8 (ContextSchema validation `missing_key`). AF의 일반 agent runner가 자기 자신의 repo에서 첫 ad-hoc task를 받았을 때 필요한 context를 자체적으로 채우지 못한다.

부수 손상: F9 — 작업 실패에도 부작용 변경 5개. dogfooding에서 "AF는 작업 실패 시 partial-state를 남긴다"는 신호.

## 결론

| 항목 | 평가 |
|------|------|
| Round 4 본래 목표 (NEXT_STEPS 분리) | ❌ 미달성 |
| Dogfooding 가치 (마찰 발견) | ✅ 9건 신규 friction (F3~F9) |
| 가장 큰 문제 | **F3 (CLI 설계 결함)** + **F8 (Context Schema)** |
| AF의 self-application 가능성 | **현재 확인된 비대화 CLI/프로그램 호출 경로로는 ad-hoc self-task 수행이 실패한다.** 원인은 CLI task 입력 경로 부재(F3) + ContextSchema 사전 구성 실패(F8). "AF 전체가 불가능"이 아니라, **현재 dogfooding에 필요한 non-interactive task runner 경로가 아직 성숙하지 않다**가 정확. interactive TUI 경로(`inquirer.prompt`)는 본 dogfooding 환경(stdin-redirected)에서 검증 불가 |

## 재현 정보 (wrapper 폐기 대체)

본 round에서 사용했던 `tests/_tmp/round4_af_runner.py`는 일회성으로 삭제됨. 재현 시 다음 패턴 사용:

```python
import sys, os
from pathlib import Path
REPO_ROOT = Path("D:/hoonProJect/worktrees/agent-factory")  # or wherever
sys.path.insert(0, str(REPO_ROOT))
os.chdir(str(REPO_ROOT))

from agent_launcher import AgentFactory
AgentFactory().run(
    task_input="<자연어 task — F3 우회용 programmatic 진입>",
    role_spec="General",
    enable_build=False,
    execution_mode="approval",   # or "fsa"
    pipeline_mode="auto",
)
```

실행 시 stdin은 `</dev/null`로 닫아 `input()` 호출들이 EOF로 처리되도록 한다 (`agent_launcher.py:313` 의 `/skip` 분기).

## 정리 결과 (2026-05-15 KST)

1. AF 부작용 5건(`projects/default/.claude/`, `projects/default/agents/`, `projects/default/.todo.md`, `projects/default/dashboard.json`, `skills/registry.yaml`) — revert/제거 완료. baseline 완전 복원 (38 lines == 38 lines, diff 0)
2. `tests/_tmp/round4_af_runner.py` — 삭제. 재현 정보는 위에 보존
3. `NEXT_STEPS.md` — AF가 실제로 분리하지 못했으므로 손대지 않음
4. 본 friction log만 commit. push/main merge 금지 (사용자 지시)

---

# Round 4b — F3/F8 fix 후 NEXT_STEPS 분리 재시도 (2026-05-15 KST)

**전제**: P4.5x (commit `f62c52e2`)로 F3 (argparse dispatch) + F8 (schema sentinel cleanup) 수정 완료.
**목표**: 동일 task를 fixed AF CLI로 재실행하여 self-run 경로 검증.

## 사용 명령 (직접 cmdline — wrapper 불필요)

```bash
python agent_launcher.py "NEXT_STEPS.md 파일을 두 부분으로 분리한다. ..." \
  --mode approval --role General </dev/null
```

F3 fix 덕에 `agent_launcher.py "task..."` 형태가 정상 작동 (P4.5x 이전엔 argparse invalid choice).

## 실행 결과

| 지표 | 값 |
|------|-----|
| AF 진입 | ✅ argparse 통과 → RUN 시작 |
| LLM 호출 1차 (intent gate) | gemini_cli 2초 실패 → claude_cli 9초 성공 |
| LLM 호출 2차 (실제 작업) | gemini_cli 2초 실패 → claude_cli **3분 15초** 성공 |
| NEXT_STEPS.md 크기 | **45줄** (목표 ≤50 ✅) |
| docs/session-log/2026-05-15-rounds-1-2-3.md | **1791줄** 생성 ✅ |
| 의도 외 .py / .claude/agents/ / scripts/ 변경 | **없음** ✅ |
| ContextSchema validation | **통과** ✅ (F8 fix 효과 확인) |
| 작업 성공 | ✅ AF가 자기 self-task를 실제 완수 |

## 신규 마찰 (Round 4 대비 추가)

| # | 단계 | 도메인 | 내용 |
|---|------|--------|------|
| F10 | NEXT_STEPS 내용 | context-staleness | AF가 출력한 NEXT_STEPS.md가 "P5 commit 대기" / "워킹트리 일괄 커밋"이라고 적었으나 실제로는 이미 `d39b1327`(P5) / `06a58d5c`(P4.5a) / `f62c52e2`(P4.5x)로 commit 완료된 상태. AF는 git log를 읽지 않고 분리 대상 본문만 보고 요약함 → 시간성 정확도 낮음. handoff doc 용도에선 사용자 후수정 필요 |
| F11 | provider race 재발 | first-success | 이번에도 gemini_cli가 매번 2초 실패하고 claude_cli로 fallback. 총 4초 낭비 × 2회 LLM 호출 = 8초. F6의 재현 |
| F12 | scope-leak 재발 (확장) | F9 재현 + 추가 | `projects/default/` 부작용 5건 (`.claude`, `.system_generated` ←신규!, `agents`, `.todo.md`, `dashboard.json`) + `skills/registry.yaml` 1건. F9 fix가 안 됐으므로 예상된 동작. 작업 성공 여부와 무관하게 매번 발생 |

## 정리 결과 (Round 4b)

1. **NEXT_STEPS.md** — AF 출력 그대로 보존 (45줄). F10(staleness)는 dogfooding 측정 가치 위해 의도적으로 손대지 않음. 사용자가 후수정 가능.
2. **docs/session-log/2026-05-15-rounds-1-2-3.md** — AF 출력 그대로 보존 (1791줄, 헤더에 "분리 시점 기록" 명시).
3. **AF 부작용 6건** (F12) — baseline 기준으로 격리 / cleanup 완료:
   - `git restore` × 2: `projects/default/dashboard.json`, `skills/registry.yaml`
   - `os.remove` × 1: `projects/default/.todo.md`
   - `shutil.rmtree` × 3: `projects/default/.claude/`, `projects/default/.system_generated/`, `projects/default/agents/`
4. **최종 diff**: `M NEXT_STEPS.md` + `?? docs/session-log/2026-05-15-rounds-1-2-3.md` (의도된 2건만)

## 결론

| 항목 | Round 4 | Round 4b |
|------|:------:|:------:|
| AF 부팅 + 라우팅 | ✅ | ✅ |
| ad-hoc cmdline 진입 | ❌ F3 | ✅ |
| ContextSchema 통과 | ❌ F8 | ✅ |
| 작업 실제 완수 | ❌ | ✅ |
| 부작용 발생 | 5건 | 6건 (F9/F12 동일 패턴, `.system_generated` 1건 추가) |

**P4.5x로 self-run 경로 차단성 마찰(F3+F8) 해소 확인**. AF는 이제 자기 자신을 cmdline에서 호출해 doc-level 작업을 완수할 수 있다.

**남은 비-차단성 마찰**: F9/F12 (validation/실행 무관 매번 발생하는 default-project scope leak) + F11 (gemini_cli race overhead) + F10 (context staleness — git 미참조). 모두 본 작업 외.

> **표현 정정 (사후)**: "Round 4b 성공"이라는 단일 라벨은 도식적이다. 정확히는 **"execution-path success, output requires human correction"** — AF 실행 경로는 검증됐지만 산출물(NEXT_STEPS)은 stale해서 사람이 정정해야 함. 이후 Round 4c+에서는 이 표현을 사용한다.

---

# F12 Scope Investigation (Round 4 + 4b 통합 분석, 2026-05-15)

**조사 정책**: timebox 30분, 80줄 cap, per-path S/M/L 표 (S ≤ 3 파일/50줄, M ≤ 10 파일/200줄, L 초과/인터페이스 변경).

## 각 write path의 entry point

| Path | Entry point | Trigger 조건 | Size (write-level) |
|------|-------------|-------------|:--:|
| `projects/default/.todo.md` | `core/documentation_policy.py:325` (`write_text`) | `project_pipeline._write_todo()` — 모든 프로젝트 run마다 | **S** |
| `projects/default/.claude/settings.local.json` | `core/providers/session_adapter.py:287` (`_write_claude_settings`) | provider/session bootstrap 시 hook 등록 | **S** |
| `projects/default/agents/<role>.yaml` | `core/manager.py:84,103` (`write_yaml`) — `_agent_path:36`이 `os.makedirs` | `manager.get_or_create()` — 신규 role 처음 요청 시 | **S** |
| `projects/default/.system_generated/` | **다중 writer**: `agent_runner.py:1043`, `hooks/langsmith_tracing.py:134`, `hooks/memory_consolidation.py:79`, `memory_system/adapters/ast_hub.py:25`, `memory_system/adapters/knowledge_graph.py:29`, `memory_system/adapters/trace_log.py:29` | 트레이스 로그·캐시·메모리 스냅샷 | **M** (5+ 파일 분산) |
| `projects/default/dashboard.json` | `core/dashboard.py:57` (`append_dashboard_run`) | 매 run 완료/오류 시 dashboard 기록 | **S** |
| `skills/registry.yaml` | `core/skill_preflight.py:261`, `external_skill_candidate_importer.py:355` | skill preflight 평가 후 metadata 갱신 | **S** |

**최종 라벨 = M** (`.system_generated/` 다중 writer 때문).

## 핵심 인사이트 — write-level fix vs architectural fix

위 표는 **write-level** 분류. 그러나 **architectural fix**가 더 효율적일 수 있음:

- **현 원인**: `AGENT_PROJECT_ROOT` env 없을 때 `config_paths.py:53`이 `PROJECT_ID="default"` → `PROJECT_ROOT=projects/default`로 fallback. 모든 위 writer가 이 fallback path에 씀.
- **단일점 fix (가능)**: ad-hoc CLI 호출 시 `PROJECT_ROOT`를 isolated dir(`projects/_self_run_<runid>/`)로 자동 set, 또는 명시적 `--project-root` 강제. 한 곳(`agent_launcher.py` ad-hoc 분기 또는 `config_paths`)만 손대면 6개 write path 전부 격리됨.
- **이 architectural fix는 S** (1~2 파일, ≤30줄): `agent_launcher.py`에서 `os.environ.setdefault("AGENT_PROJECT_ROOT", ...)` + cleanup hook.

## 분류 결과 + 권장

| 차원 | 라벨 |
|------|------|
| write-level (각 writer를 가드한다면) | **M** |
| architectural (단일 fallback 차단) | **S** |

**권장 fix 경로**: architectural (S). write-level은 매 writer마다 분기 추가 → 회귀 위험 + 다른 사용 경로(production user)에 영향 가능. architectural fix는 ad-hoc CLI invocation 한정 환경 격리 → side-effect zero.

**user 정책 (all-or-nothing)에 따른 결정**: architectural 단일점 fix는 모든 path 일관 해결 → all-or-nothing 만족. **S 분류**.

→ **이번 turn에서 fix는 하지 않음** (조사만이 사용자 지시). 다음 turn에서 architectural S fix 진행 가능.

---

# 추가 친화 기록 (F13~)

| # | 분류 | 내용 |
|---|------|-----|
| **F13** | cost / wasted-discovery | AF가 매 ad-hoc run에서 task에 맞는 skill 후보 (예: `markdown_split`, `session_log_archival`)를 LLM intent gate에서 식별. `--build` 미사용 시 즉시 폐기되지만, **식별 자체의 토큰 비용은 매 run 발생** (관찰이 아니라 비용 누수) |
| **F14** | nondeterministic leak surface | F12 leak 항목 집합이 deterministic하지 않음. Round 4(F9)는 5건 (`.claude`, `agents`, `.todo.md`, `dashboard.json`, `registry.yaml`), Round 4b는 6건 (`.system_generated/` 추가). 입력 task의 skill 매칭 결과에 따라 leak 표면 변동 → 단순 cleanup list 자동화 어려움. F12 architectural fix가 이 nondeterminism도 해결 |
| **F10 root** | system-level (메모) | F10(NEXT_STEPS staleness)의 진짜 원인은 **AF가 self-run 시 `git log`/`git status` 미인지**. 이번 turn에서 NEXT_STEPS 수동 정정으로 1회성 해결했으나, **다음 self-run에서 동일 stale 출력 재발 예상**. 시스템 fix 후보: (a) AF agent prompt에 git context preamble 자동 주입, (b) ad-hoc CLI에 `--with-git-context` 플래그. 본 turn 외 backlog |
| **잠재 NameError** | 별도 (구현 X, 기록만) | `agent_launcher.py:775` `prompt_mission_template("Agent Factory")` 호출 — `agent_launcher.py` 상단에 import 없음. `from core.utils import *`에도 없음 (`grep -n "prompt_mission_template" core/utils.py` 결과 없음). 발화 조건: `python agent_launcher.py` (empty argv) → `_detect_mode()` ad_hoc → `args.task=[]` → `task_input=""` → 이 호출. **NameError 발생**. P4.5x가 잡지 못함. 별도 tiny fix (1줄 `from core.template_input import prompt_mission_template`) 필요 |

---

# Round 4c — F12 architectural fix 후 재검증 (2026-05-15)

**전제**: P4.5x F3/F8 fix + commit `78e6a4be` (F12 architectural isolation) + commit `253224e3`/`18d3d546` (F12 hardening: env_flag canonical + dual-source + diagnostic + Blueprint 반영) 적용.

**Task**: friction log에 1-줄 추가 (작은 doc-only 작업, leak 재발 여부 검증 목적).

## 실측 결과

| 차원 | 결과 |
|------|------|
| `projects/default/*` leak | **0건** ✅ |
| `skills/registry.yaml` leak | **0건** ✅ |
| 실행 path | ✅ AF 정상 부팅 + 작업 종료 (~15초 claude_cli) |
| baseline 대비 git diff | **0** (`docs/dogfooding/round4-af-cli-friction.md` 본 추가까지의 baseline) |
| **사용자 명시 목표** (leak 재발 여부 확인) | **PASS** ✅ |

## F15 신규 발견 — Workspace 격리 부작용

F12 fix가 PROJECT_ROOT 격리만 의도했으나, AF 내부에서 PROJECT_ROOT를 workspace로도 fallback 사용 → ad-hoc CLI에서 AF가 `<tempdir>/af_self_run_*/docs/dogfooding/round4-af-cli-friction.md`에 쓰고, **real repo 파일은 미수정**.

실측 증거:
```
$ find $TEMP -name "round4-af-cli-friction.md"
.../af_self_run_1778820746_72056/docs/dogfooding/round4-af-cli-friction.md
.../af_self_run_1778823153_123556/docs/dogfooding/round4-af-cli-friction.md  ← Round 4c
```

**비교**:
| Round | PROJECT_ROOT | workspace | real repo 편집 |
|-------|--------------|-----------|:--:|
| 4b (F12 fix 이전) | `projects/default/` | (default → PROJECT_ROOT) | ✅ NEXT_STEPS.md 분리 성공 |
| 4c (F12 fix 이후) | isolated tempdir | (default → isolated) | ❌ 작성은 tempdir에만 |

**해석**:
- **Leak 차단 성공** (사용자 목표 달성).
- **부작용**: dogfooding 사용 케이스의 "AF가 real repo 작업"이 불가능해짐. self-run의 활용 범위 축소.

**가능한 후속 조치 (별도 sprint)**:
- (A) `agent_launcher.py:if __name__` ad_hoc 분기에서 `AgentFactory().run(..., workspace=os.getcwd())` 명시 전달. PROJECT_ROOT는 isolated tempdir 유지, workspace는 real cwd → 이중 격리 분리.
- (B) PROJECT_ROOT 격리 정책 자체 재검토. ad-hoc CLI 진입은 격리 X, write-path별 가드로 회귀 (write-level M fix).
- (C) `--workspace <path>` 명시 플래그 도입 (F12 격리 + 사용자 선택 workspace).

이 결정은 사용자 의사에 달림. 본 friction log엔 새 finding으로 기록만.

## 결론

Round 4c는 **leak verification 차원에서 PASS**. F12 architectural fix가 의도된 동작 (default-project + global registry leak 차단)을 수행함.

**부작용 F15**는 별도 design 결정 필요. 본 sprint scope 외.

(F6 tempdir accumulation 잔재 확인됨 — 3+ self-run 디렉터리 누적. 후속 hygiene 작업 backlog.)

## Round 4c 사후 정정 — Reviewer challenge 응답

cross-review가 `skills/registry.yaml`을 보고 "Round 4c PASS 주장이 잘못, F12 fix가 unfixed"라고 challenge함 (2 High + Medium + Low). 사실 검증 후 다음과 같이 정정:

| Reviewer claim | 사실 | 평가 |
|----------------|------|------|
| HEAD의 `skills/registry.yaml`에 `tests/_tmp/af-test-9648c834/...` 경로 committed | **정확함** — `git show HEAD:skills/registry.yaml` 확인 | ✅ pre-existing 결함 (F12 외 backlog) |
| "F12 fix가 unfixed, test run이 여전히 mutating" | F12 fix는 작동 (재-smoke diff 0 검증). dirty state(`14:17:47`)는 **F12 fix Part B 적용 전** 의 잔재 | ⚠️ reviewer 인과 attribution 오류 |
| 제 "Round 4c PASS" 주장 | "F12 fix가 NEW write를 막는다"는 맞음. "skills/registry.yaml is clean"으로 해석되면 틀림 | ⚠️ 좁은 의미만 정확 |

## F16 신규 — Test isolation gap (별도 backlog)

`tests/test_project_scope.py:32-47`이 `RegistryManager`를 통해 real `skills/registry.yaml`에 write (test fixture `abc` skill 등록). F12 fix(`AF_DISABLE_REGISTRY_WRITE` env flag)는 agent_launcher CLI 진입에서만 set되므로 **pytest run은 차단 못 함**.

**증거**:
- `grep -rn "abc" tests/test_project_scope.py` 결과: 라인 32-47에서 test fixture `abc` skill 정의 → `skills/registry.yaml`에 영구 commit됨
- HEAD의 registry.yaml에 test paths 잔존 (older runs로부터)
- 이번 세션 중에도 어느 시점에 누군가가 14:17:47에 mutate (정확한 호출자 미식별, 가장 가능성 큰 후보: 제 pytest 실행)

**해결 옵션** (F16):
- (A) `tests/test_project_scope.py`에 pytest fixture로 `monkeypatch.setenv("AF_DISABLE_REGISTRY_WRITE", "1")` 추가
- (B) `RegistryManager`가 호출자 stack에서 `pytest` 모듈 감지 시 auto-skip
- (C) `pytest.ini` 또는 `conftest.py`에 글로벌 env set
- (D) HEAD에서 `abc` test fixture entry 정리 commit (one-shot cleanup)

**우선순위**: 별도 sprint. 이번 F12 closure scope 외. 다음 cross-review 가 동일 challenge하지 않게 friction log에 명문화.

---

# F15 Scope Investigation (2026-05-15)

**조사 정책**: timebox 30분, 80줄 cap, S/M/L per fix option. 사용자 명시 5개 질문 답변.

## Q1: `AgentFactory.run(workspace=...)` 전달 경로

`agent_launcher.py:553` `target_workspace = workspace or PROJECT_ROOT` — workspace 미전달 시 PROJECT_ROOT fallback. Round 4c에서 workspace=None → target_workspace = isolated tempdir → AF가 tempdir에 작업한 원인.

## Q2: 실제 파일 write path 결정

`core/providers/cli.py:282,312,442,487,739,766` — provider subprocess (claude_cli/codex_cli/gemini_cli) `subprocess.Popen(..., cwd=str(request.workspace))`. **provider cwd = workspace**. provider 내부에서 Edit/Write tool은 cwd-relative path resolution. 즉 workspace가 user file 편집 경로를 결정.

내부 상수와는 분리됨:
- `core/config_paths.py:67-78`: `AGENTS_DIR`, `DASHBOARD_PATH`, `.todo.md` 등 일부는 PROJECT_ROOT 기반
- `core/documentation_policy.py:324`: `.todo.md`는 workspace 기반 (`os.path.join(workspace, ".todo.md")`)
- 일관성은 부분적 — `.todo.md`는 workspace, agents/dashboard.json은 PROJECT_ROOT.

## Q3: Round 4b 메커니즘 — NEXT_STEPS.md 실제 수정

Round 4b 시: workspace=None → target_workspace = PROJECT_ROOT = projects/default/. provider cwd = projects/default/. 그러나 NEXT_STEPS.md는 repo root에 존재.

**가설**: claude_cli provider가 "git toplevel auto-resolve" 또는 LLM 자체가 path를 .. 로 올라가 해결. 정확한 메커니즘은 provider 내부 (out of AF scope). **확정 사실**: F12 fix 이전엔 provider cwd = projects/default/ 였고, real repo 수정이 일어남. F12 fix 후엔 provider cwd = isolated tempdir → real repo 수정 안 됨.

→ F15 fix 핵심: provider cwd를 real repo로 설정. workspace를 cwd로 전달하면 provider cwd도 cwd 됨.

## Q4: user-work vs internal-state 경계

존재함 (부분적):
- **user-work** (workspace 기반): provider cwd, `.todo.md`, ensure_documentation_files
- **internal-state** (PROJECT_ROOT 기반): agents/, dashboard.json, .system_generated/, runs/, skills/registry.yaml (글로벌은 SKILLS_DIR)

F12 fix가 두 가지 모두 isolation tempdir로 보낸 게 문제. workspace만 cwd로 분리하면 됨.

## Q5: Fix 옵션 S/M/L 분류

| 옵션 | 구현 | Size |
|------|------|:--:|
| **(A) `workspace=os.getcwd()` 명시 전달** — `agent_launcher.py:__main__` ad_hoc 분기에서 `AgentFactory().run(..., workspace=os.getcwd())` 추가 (~1줄) | 1 파일, 1 줄 | **S** |
| (B) `--workspace <path>` CLI 플래그 도입 + default=os.getcwd() | 1 파일, ~5 줄 + argparse | S+ |
| (C) env `AF_WORKSPACE` override + 자동 격리 정책 | 1~2 파일, ~10 줄 | S++ |

**최종 라벨**: **S** (옵션 A 채택 시)

## Fix 시 회귀 위험 + 추가 success criteria

**위험**: provider가 cwd=real repo로 실행되면, LLM이 의도 외 파일 수정 가능. F12 시절 발견된 scope-leak과 유사 패턴. 따라서 Round 4d 성공 기준에 사용자 명시 #4 (사용자 명시 외 파일 변경 0) 필수.

**Round 4d 성공 기준 (사용자 확정 5건)**:
1. real repo의 의도된 문서 파일 실제 수정 ✅
2. `projects/default/*` 변경 0
3. `skills/registry.yaml` 변경 0
4. **사용자 명시 외 파일 변경 0** (회귀 가드)
5. tempdir에는 runtime/session/state만 존재

## 결론

F15 fix는 **S** (옵션 A, 1줄). Round 4d 검증 후 S 확정. 사용자 plan대로 진행 가능 — F15 fix → Round 4d → tiny → push.


## 결과

(완료 후 append)

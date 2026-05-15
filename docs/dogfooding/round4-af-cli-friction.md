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


## 결과

(완료 후 append)

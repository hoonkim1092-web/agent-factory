# Code Review: cli_hook_bridge

> Source: scripts/cli_hook_bridge.py
> Date: 2026-04-29 22:54
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

WARN — 1 High (ACCEPT), 1 Medium (ACCEPT), 1 Low (HOLD). No Critical issues. Can merge with documented risks, but the High finding should be fixed before shipping to any multi-project deployment.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `_PROJECT_ROOT` fallback이 non-self-hosted 배포에서 잘못된 workspace를 제공

- **Critic**: "`_PROJECT_ROOT`는 `cli_hook_bridge.py` 위치 기반으로 고정 → AF가 글로벌 도구로 설치된 경우 실제 사용자 프로젝트가 아닌 AF 코드베이스 루트로 continuity 상태 파일이 기록됨"
- **Cross**: "`hook_runner.py:424-427`은 `cwd=workspace`로 자식 프로세스를 실행하지만, `cli_hook_bridge.py:30`의 fallback은 그 workspace를 무시하고 `_PROJECT_ROOT`를 사용 → `handle_hook_event`가 `.af_runtime`, `.todo.md`, `.af_manifest.json`, resume brief 경로를 잘못 계산"
- **Judgment**: 두 리뷰어가 동일 코드 라인(`cli_hook_bridge.py:30`)과 동일 실패 경로(non-self-hosted 배포)를 독립적으로 발견. `handle_hook_event`가 workspace를 경로 기반으로 사용하는 것은 `core/providers/session_adapter.py:622-668`에서 확인됨. 현재 단일 PC self-development 시나리오에서만 우연히 정확.
- **Action Required**:
  ```python
  if not args.workspace:
      args.workspace = os.environ.get("AGENT_CLI_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
  ```
  `_PROJECT_ROOT`는 `sys.path` 조작 용도로만 유지.

---

#### 2. [ACCEPT] [Medium] `__file__` 기반 `_PROJECT_ROOT`가 frozen 빌드에서 무음 오작동

- **Critic**: "변경 전에는 `_PROJECT_ROOT`가 sys.path 조작에만 쓰였으나, 변경 후 workspace fallback의 최종 소스가 됨 → frozen 빌드에서 `__file__`이 `/tmp/_MEIxxxx/`를 가리켜 잘못된 경로 생성. code-review.md 'Frozen build compatibility' 체크리스트와 정확히 일치."
- **Cross**: 별도 미언급 (Finding 1에 흡수된 형태로 일부 중복됨)
- **Judgment**: Critic의 증거가 충분하고 code-review.md 체크리스트와 일치. `scripts/`가 현재 frozen 빌드에 포함되지 않더라도, 이번 변경이 `_PROJECT_ROOT`의 **위험 노출 범위를 확대**했으므로 관리해야 함.
- **Action Required**: Finding 1 수정 시 함께 해결됨 — `_PROJECT_ROOT`를 workspace fallback에서 제거하면 frozen 빌드 위험도 동시에 제거됨. 필요 시 frozen 가드 추가:
  ```python
  if getattr(sys, 'frozen', False):
      _PROJECT_ROOT = os.path.dirname(sys.executable)
  ```

---

#### 3. [HOLD] [Low] `run.py` dispatch 경로에서 `--provider`, `--run-id` 중계 미검증

- **Critic**: "`run.py:38`이 `hook_runner.py`를 통해 `cli_hook_bridge.py`에 args를 중계하는 경로가 검증되지 않음. `--run-id`가 `required=True`이므로 dispatch가 깨지면 argparse 오류 발생."
- **Cross**: 미언급
- **Judgment**: 단일 리뷰어 Low 소견. Cross 리뷰어는 `_hook_command()`가 여전히 `--workspace`, `--run-id`, `--repo-root`를 명시적으로 emit하는 것을 확인했으나 (`session_adapter.py:231`), 이는 생성된 Claude/Gemini 훅 명령어 경로이지 `run.py` 경유 경로가 아님. `hook_runner.py`의 dispatch 로직을 보지 않으면 확정 불가.
- **Question for Author**: `hook_runner.py`가 `extra` args를 자식 스크립트로 그대로 중계합니까? 아니면 별도 파싱/필터링합니까?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_PROJECT_ROOT` fallback → 잘못된 workspace | High | ACCEPT | Both |
| 2 | `__file__` frozen 빌드 비호환 위험 확대 | Medium | ACCEPT | Critic |
| 3 | `run.py` dispatch args 중계 미검증 | Low | HOLD | Critic |

---

### Recommendations

- **[즉시]** `args.workspace` fallback을 `os.getcwd()` 또는 환경변수 기반으로 교체. `_PROJECT_ROOT`를 workspace 결정 로직에서 완전히 제거.
- **[함께]** Finding 1 수정으로 frozen 빌드 위험(Finding 2)도 자동 해소되는지 확인. `_PROJECT_ROOT`가 sys.path 전용으로만 남으면 OK.
- **[확인]** `hook_runner.py`의 `extra args` 중계 방식 확인 후 Finding 3 해소 또는 ACCEPT 격상.
- **[유지]** Cross 리뷰어가 확인한 긍정 사항: 생성된 훅 명령어(`_hook_command()`)는 여전히 `--workspace`를 명시적으로 전달 → 기존 Claude/Gemini 세션 호환성 유지됨. 이번 fix는 이 경로를 변경할 필요 없음.
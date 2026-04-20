# 교차검증 자동 트리거 — 개발환경 · 배포환경 통합 설계

- 작성일: 2026-04-17
- 작성자: Claude Code (Opus 4.7)
- 상태: v2 (af-critic BLOCK 2 + WARN 4 + af-doc-qa WARN 5 반영)
- 관련 이슈: 오늘 세션에서 `core/*.py` 수정 후 `[af-review-pending]` 트리거 0회 발동 확인. 원인 분석 결과 Claude Code 훅이 전체 no-op 상태였음

## 0.0 개정 이력

| 버전 | 일시 | 변경 요약 |
|------|------|-----------|
| v1 | 2026-04-17 13:00 | 초안. 3-stage 이행. Stage 1에 `post_edit_dispatch` 통합 훅 제안 |
| v2 | 2026-04-17 13:40 | **통합 dispatch 포기 — 개별 훅 분리 구조 유지**. stdin 파싱만 교체(timeout 스택 회피). `hook_runner.py`에 builtin 분기 테이블 신설 필요 명시(BLOCK-1). `enqueue_agent_review.py` atomic 쓰기(BLOCK-2). SSOT 범위를 "파일 선별 규칙"만으로 축소 + 검증자 동일성은 Stage 3 예정 명시. 각 Stage 롤백 커맨드, 쿨다운 로직, §11 에러 코드 항목 추가. P4(경로 B 작동 의심)를 Stage 2 사전조건으로 승격 |
| v3 | 2026-04-17 14:00 | af-critic 재검증 잔여 WARN 3건 반영: §8.2 E2E 예시에서 폐기된 `post_edit_dispatch` 이름 제거, builtin 함수 내 `except` 블록에 `hook_events.log` 기록 의무화, stdin 재사용 엣지케이스 금지 제약 명시 |

## 0. 배경

### 0.1 발견
오늘 `core/documentation_policy.py`, `core/project_task_board.py`, `core/dynamic_orchestrator.py` 등을 수정했으나 **CLAUDE.md가 규정한 교차검증 자동 트리거(`[af-review-pending]`)가 한 번도 발동하지 않았다**. 세션 로그 통계:
- UserPromptSubmit 655회, Stop 560회, **PostToolUse 0회**
- `.af_review_queue/pending_agent_review.json` 마커 부재

### 0.2 근본 원인
`.claude/settings.local.json:131-171`의 PostToolUse 훅 6개 중 5개가 **`$TOOL_INPUT_file_path`라는 존재하지 않는 환경변수**를 참조한다. Claude Code는 훅 데이터를 **stdin JSON**으로 전달하므로 `$fp`는 항상 빈 문자열이고, `case "$fp" in *.py)` 매칭이 실패해 전체 훅이 no-op로 실행된다.

실측:
```bash
$ echo '{"tool_input":{"file_path":"/x.py"}}' | bash -c 'fp=$TOOL_INPUT_file_path; echo [$fp]'
[]   # 빈 값
```

## 1. 현재 구조

### 1.1 두 개의 완전 분리된 경로

| 항목 | 경로 A (개발환경) | 경로 B (af 자체 실행) |
|------|-------------------|----------------------|
| 트리거 | Claude Code 훅 (`.claude/settings.local.json`) | `core/dynamic_orchestrator._inject_review_tasks_if_needed` |
| 실행 주체 | 사람 (Claude Code가 제안 메시지 받고 에이전트 수동 실행) | af 자체 에이전트 (자동 board 주입) |
| 검증 대상 규칙 | `core/*` + `model_utils.py` + `run_factory_cli.py` (hardcoded) | 모든 `build` phase 완료 태스크 (module 단위) |
| 검증 방식 | Claude Code의 Task 도구로 `af-critic` + `af-cross-review` subagent 호출 | `core/cross_verification.py:CrossVerificationLoop` (CLI 병렬 + 순환 리뷰 + Opus 판정) |
| 실행 빈도 (오늘 세션) | **0회** (훅 no-op) | 검증 대상 build 태스크 없어서 해당 없음 |
| 배포 zip 포함 | ❌ `.claude/`는 bundled 아님 | ✓ `core/cross_verification.py`는 `af.spec`에 포함 |
| SSOT | 없음 — 규칙 중복 기재 | 없음 — phase 필터만 사용 |

### 1.2 핵심 관찰
- **두 경로가 "같은 규칙"을 따르지 않는다.** 경로 A는 파일 whitelist, 경로 B는 phase 트리거.
- **두 경로가 "같은 검증자"를 부르지 않는다.** 경로 A는 Claude Code subagent(`af-critic`/`af-cross-review`), 경로 B는 CLI 프로바이더 병렬 호출.
- 따라서 "개발환경과 배포환경이 동일하게 작동한다"는 **현 상태에서 성립하지 않음**. 같은 상황에서 전혀 다른 체크리스트·검증자·결과 포맷이 나온다.

## 2. 문제 정의

- **P1 (오늘 확정)**: 경로 A 훅이 전체 no-op → 개발 중 코드리뷰·교차검증 자동 트리거가 실질적으로 0회.
- **P2**: 경로 A와 경로 B가 같은 "구현 완료" 이벤트에 대해 다른 규칙·다른 검증자를 적용 → 환경별로 결과가 달라 예측 불가능.
- **P3**: 검증 대상 파일·경로 whitelist가 훅 스크립트 내부에 하드코딩 → 공유 SSOT 부재, 추가·변경 시 여러 곳 동기화 필요.
- **P4 (잠재)**: 경로 B(`inject_review_tasks`) 자체가 실제로 작동하는지 검증된 흔적이 세션 로그에 없다 (오늘은 build 태스크가 없었음). 작동 검증이 필요.
- **P5 (배포물 범위)**: 배포 zip 사용자가 `af` CLI로 개발할 때는 경로 B만 작동. 그들이 Claude Code를 병행 사용해도 경로 A는 bundled 아님.

## 3. 요구사항 재정의

사용자 요청: "개발환경 및 배포물도 동일하게 작동하도록 다시 설계해"

이를 구체화하면:
1. **동일 이벤트 → 동일 규칙**: "구현 완료"(= 파일 편집 또는 build 태스크 완료)가 발생하면 규칙 집합이 같아야 한다.
2. **동일 규칙 → 동일 검증자**: 같은 규칙에 매칭되면 같은 검증자(같은 역할·같은 프롬프트)가 실행되어야 한다.
3. **단일 진실원천**: 대상 파일·검증 단계·검증자 목록이 한 곳에 정의되어야 한다.
4. **환경 격차 허용**: 환경 고유 제약(Claude Code subagent vs CLI 프로바이더 병렬 호출)은 어댑터 레이어에서 흡수.
5. **우선순위**: P1 즉시 복구 > P2/P3 공통화 > P4 검증 > P5 배포 확장.

## 4. 설계 대안

### 4.1 옵션 비교

| 옵션 | 방식 | 장점 | 단점 | 복잡도 |
|------|------|------|------|--------|
| **A. 최소 수정** | 훅 stdin JSON 파싱으로 복구. 경로 B는 그대로 | 즉시 복구, 리스크 최소 | P2/P3 미해결 (두 경로 여전히 다른 규칙) | 낮음 |
| **B. 중앙 디스패처** | `core/review_dispatcher.py` 신설. 양 경로가 동일 디스패처 호출 | 단일 진실원천, 규칙 일관성 | 경로 B 기존 `inject_review_tasks`와의 경합 정리 필요 | 중간 |
| **C. CLI 수렴** | `af review <file>` 서브커맨드 신설. 개발환경 훅은 이 CLI 호출. 배포물도 동일 CLI 사용 | 배포물 + 개발환경 완전 통합, CLI 하나로 수동 실행도 가능 | `af review`가 단일 파일/태스크 모드 지원해야 함 (신규 개발) | 중간·높음 |
| **D. 혼합 (추천)** | (1) 즉시 A로 복구 (2) 규칙 SSOT 모듈(`core/review_targets.py`) 추출 (3) 점진적으로 C 방향 이행 | 단계적 리스크 관리, 빠른 P1 해소 + 구조적 P2/P3 해결 경로 확보 | 2단계로 작업 | 중간 |

### 4.2 추천: **옵션 D (혼합, 3단계 이행)**

#### Stage 1 — 즉시 복구 (오늘)
- 훅 stdin JSON 파싱으로 교체. `hook_runner.py`에서 stdin을 파싱해 파일 경로를 자식 스크립트의 argv로 전달
- 각 `*.py` 조건부 bash 명령(`case "$fp" in *.py)`)을 stdin 기반 Python 래퍼로 전환
- 실행 로그 남겨 훅이 실제 동작했는지 감시

#### Stage 2 — 규칙 SSOT 추출 (이번 주)
- `core/review_targets.py` 신설:
  ```python
  REVIEW_PATH_PREFIXES = ("core/",)
  REVIEW_EXACT_FILES = ("model_utils.py", "run_factory_cli.py")
  REVIEW_AGENT_ROLES = ("code_review", "cross_validate")
  def is_review_target(relpath: str) -> bool: ...
  def review_agents_for(relpath: str) -> list[str]: ...
  ```
- 경로 A(`scripts/enqueue_agent_review.py`)와 경로 B(`core/project_task_board.py:inject_review_tasks`) 둘 다 이 모듈을 import
- whitelist 변경 시 한 곳만 수정

#### Stage 3 — CLI 통합 진입점 (다음 마일스톤)
- `af review <paths_or_module>` 서브커맨드 신설. 내부적으로:
  - 입력이 파일 경로 리스트면: 각 파일에 대해 규칙 매칭 → 해당하는 검증자 실행
  - 입력이 module_id면: 기존 `inject_review_tasks` 호출
- 개발환경 훅은 `af review "$file"`를 호출. 배포물 내부 파이프라인도 동일 CLI 경유
- 환경별 어댑터:
  - Claude Code 세션 감지(예: `CLAUDE_PROJECT_DIR` 환경변수) → 마커 파일 생성으로 `[af-review-pending]` 경로 유지
  - 그 외(af 자체 실행) → board에 태스크 주입 또는 즉시 CrossVerificationLoop 호출

## 5. 상세 설계 (Stage 1 + Stage 2 — 본 문서 범위)

### 5.1 설계 원칙 (v2 개정)

- **통합 dispatch 훅 포기**: v1에서 제안한 `post_edit_dispatch` 하나로 6개 서브스크립트를 순차 실행하는 방식은 timeout 스택(3+120+120+5+3+3=254초) 위험 + 단일 실패 시 뒤 스크립트 전부 skip 위험 → **포기**.
- **개별 훅 분리 유지**: `.claude/settings.local.json` 의 6개 PostToolUse 항목 구조(독립 timeout + statusMessage)를 **그대로 유지**. Claude Code가 각 hook command에 독립 stdin을 공급하므로 병렬성/격리 성질은 보존된다.
- **바뀌는 건 한 곳뿐**: 각 훅 명령의 `fp=$TOOL_INPUT_file_path` (존재하지 않는 env var) → `python3 scripts/hook_runner.py <builtin>`으로 교체. `hook_runner.py`가 stdin JSON에서 file_path를 읽어 해당 서브작업을 직접 수행한다.

### 5.2 훅 명령 재작성 (Stage 1)

**Before (`.claude/settings.local.json:137`)**
```json
"command": "fp=$TOOL_INPUT_file_path; case \"$fp\" in *.py) python3 -m py_compile \"$fp\" ...; esac"
```

**After (6개 항목 각각)**
```json
// py_compile 훅
"command": "python3 scripts/hook_runner.py post_edit_py_compile"

// enqueue_agent_review 훅
"command": "python3 scripts/hook_runner.py post_edit_enqueue"

// code_review_updater 훅
"command": "python3 scripts/hook_runner.py post_edit_code_review"

// blueprint_updater 훅
"command": "python3 scripts/hook_runner.py post_edit_blueprint"

// design_review_trigger 훅 (Write|Edit 전체 대상이므로 .py 필터 없음)
"command": "python3 scripts/hook_runner.py post_edit_design_review"

// notifications drain 훅 — 변경 없음 ($fp 미사용으로 원래 정상)
```

각 훅의 timeout/statusMessage는 기존 값 유지.

### 5.3 `hook_runner.py` 확장 — Builtin 분기 테이블 (BLOCK-1 대응)

**현행 `hook_runner.py:79-112`는 `sys.argv[1]`을 무조건 파일 이름으로 간주해 `scripts/<name>.py`를 해석한다.** `post_edit_*` 같은 내장 서브커맨드를 그대로 넘기면 `_resolve_script()`가 파일 미존재로 silent `return 0` → **또 no-op**. v1 설계의 치명적 누락.

**v2 해결**: `main()` 진입 지점에 **builtin 분기 테이블**을 먼저 둔다. builtin이면 내부 함수 호출, 아니면 기존 로직 유지(backward compat).

```python
# scripts/hook_runner.py (v2)
import json
import os
import subprocess
import sys

def _read_hook_stdin_once() -> dict:
    """Claude Code가 각 hook command에 독립 stdin을 공급하므로
    이 함수는 프로세스당 한 번만 호출된다. 여러 서브작업이 필요하면
    반환값(dict)을 재사용한다."""
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}

def _extract_file_path(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    return str(ti.get("file_path") or "")

def _post_edit_py_compile(payload: dict) -> int:
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    try:
        r = subprocess.run([sys.executable, "-m", "py_compile", fp], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            print(f"[af-hook] syntax error in {fp}\n{r.stderr}", file=sys.stderr)
        return 0  # 훅은 항상 0 exit (block 방지)
    except Exception as exc:
        print(f"[af-hook] py_compile error: {exc}", file=sys.stderr)
        return 0

def _post_edit_enqueue(payload: dict) -> int:
    fp = _extract_file_path(payload)
    if not fp or not fp.endswith(".py"):
        return 0
    # 기존 enqueue_agent_review.py 에 argv로 전달 (이 스크립트는 유지, 로직 변경 없음)
    try:
        subprocess.run([sys.executable, "scripts/enqueue_agent_review.py", fp], timeout=3)
        _log_hook_event("post_edit_enqueue", fp, 0)
    except Exception as exc:
        # v3: 관측성 보장 — except 블록에서도 반드시 로그 기록 (af-critic v2 WARN-2 대응)
        _log_hook_event("post_edit_enqueue", fp, 1, error=str(exc))
    return 0

def _log_hook_event(builtin: str, file: str, exit_code: int, error: str = "") -> None:
    """훅 실행 시점·파일·결과를 append-only 로그에 기록. 실패는 silently swallow.
    관측성 요구(§5.7)를 위해 모든 builtin 함수의 성공/실패 경로에서 호출."""
    try:
        from datetime import datetime
        line = f"{datetime.now().isoformat()}|{builtin}|{file}|{exit_code}|{error}\n"
        log_path = os.path.join(".af_review_queue", "hook_events.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # 로그 실패는 훅 전체를 막지 않음

# ... post_edit_code_review, post_edit_blueprint, post_edit_design_review 동형 ...

_BUILTINS = {
    "post_edit_py_compile": _post_edit_py_compile,
    "post_edit_enqueue": _post_edit_enqueue,
    "post_edit_code_review": _post_edit_code_review,
    "post_edit_blueprint": _post_edit_blueprint,
    "post_edit_design_review": _post_edit_design_review,
    # 기존 cli_hook_bridge, check_pending_review 등은 scripts/ 에 있는 파일이므로
    # _BUILTINS 에 없고 기존 _resolve_script 경로로 처리됨
}

def main() -> int:
    if len(sys.argv) < 2:
        return 0
    cmd = sys.argv[1]
    # v2: builtin 먼저 확인 — 없으면 기존 script-resolve 경로 fallthrough
    if cmd in _BUILTINS:
        payload = _read_hook_stdin_once()
        return _BUILTINS[cmd](payload)
    # ... 기존 _resolve_script / Popen 로직 그대로 ...
```

**stdin 일회성 소비 처리**: Claude Code는 각 hook command에 독립 프로세스·독립 stdin을 공급하므로, 한 프로세스 내에서 stdin이 한 번 읽히면 끝나도 문제없다. `_read_hook_stdin_once()`는 프로세스 수명 내 1회 호출 가정.

**stdin 재사용 엣지케이스 금지 제약 (v3)**: `_BUILTINS`에 등록된 함수는 **내부적으로 다른 builtin을 subprocess로 간접 호출해서는 안 된다**. 이유: subprocess 자식 프로세스는 부모의 stdin(`sys.stdin`)을 상속받는데, 부모가 이미 `_read_hook_stdin_once()`로 소비했으므로 자식은 빈 stdin을 받아 Claude Code JSON 페이로드를 파싱하지 못한다. 호출 필요 시 반드시 `payload` dict를 함수 인자로 직접 전달하는 in-process 방식 사용. 구현자는 이 계약을 docstring에 명시.

### 5.4 Atomic 마커 쓰기 (BLOCK-2 대응)

**문제**: `scripts/enqueue_agent_review.py:89-93`의 `open(marker, "w")`는 비원자적이다. 경로 A와 경로 B가 동시에 같은 마커에 쓸 경우 파일이 절단될 수 있다.

**v2 해결**: `tempfile` + `os.replace()` 패턴으로 교체. `locked_file`은 board 전용으로 두고, 마커는 POSIX atomic rename으로 충분.

```python
# scripts/enqueue_agent_review.py (수정)
import tempfile
...
    try:
        os.makedirs(marker_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".pending_", dir=marker_dir, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, marker)  # POSIX atomic
        except Exception:
            try: os.unlink(tmp_path)
            except Exception: pass
            raise
    except Exception:
        pass
```

### 5.5 `core/review_targets.py` 신설 (Stage 2)

**범위 축소 (v2)**: SSOT는 **"파일 선별 규칙 + 역할 이름 상수"만** 통합한다. 검증자 자체의 코드/프롬프트 동일성은 본 설계 범위 **밖**이며 Stage 3 이후 과제로 명시한다 (af-critic WARN-3 반영 — "역할 이름만 같고 실제 검증 로직이 달라 무의미"한 구조적 괴리는 SSOT 추출만으로 해결되지 않음).

```python
# core/review_targets.py
"""교차검증·코드리뷰 대상 파일·역할 이름 정의의 SSOT (파일 선별 한정).

NOTE: 본 모듈은 '어떤 파일이 검증 대상인가' 와 '역할 이름'만 통합한다.
역할 이름이 동일해도 경로 A(Claude Code subagent)와 경로 B(CLI 프로바이더 병렬)가
실제로 호출하는 검증자는 다르다. 검증자 통일은 Stage 3의 `af review` CLI 통합에서 다룬다.

입력 계약: 모든 함수는 POSIX 구분자(/) 사용 상대경로를 기대한다.
절대경로가 올 경우 호출 측이 workspace 기준 상대경로로 변환한 뒤 전달해야 한다.
"""
from __future__ import annotations
import os

REVIEW_PATH_PREFIXES: tuple[str, ...] = ("core/",)
REVIEW_EXACT_FILES: tuple[str, ...] = ("model_utils.py", "run_factory_cli.py")

REVIEW_ROLES: tuple[str, ...] = ("code_review", "cross_validate")

def is_review_target(relpath: str) -> bool:
    """입력: POSIX 구분자 상대경로. 절대경로가 오면 False 반환(호출 측 책임)."""
    rel = str(relpath or "").replace("\\", "/")
    if not rel or rel.startswith("/") or ":" in rel.split("/", 1)[0]:
        return False  # 절대경로·Windows 드라이브 표기 거부
    if not rel.endswith(".py"):
        return False
    if any(rel.startswith(p) for p in REVIEW_PATH_PREFIXES):
        return True
    return os.path.basename(rel) in REVIEW_EXACT_FILES

def review_roles_for(relpath: str) -> list[str]:
    return list(REVIEW_ROLES) if is_review_target(relpath) else []
```

**경로 A 통합**: `scripts/enqueue_agent_review.py`의 `_REVIEW_PREFIXES` / `_REVIEW_EXACT`/`_is_review_target`을 제거하고 `core/review_targets.py:is_review_target`을 사용.

**경로 B 통합**: `core/project_task_board.py:inject_review_tasks`에서 하드코딩된 `"code_review"` / `"cross_validate"` 문자열을 `REVIEW_ROLES` 상수로 대체.

스크립트가 `core/*`를 import하는 부담: `scripts/enqueue_agent_review.py` 상단에 프로젝트 루트를 `sys.path`에 추가 (기존 `scripts/hook_runner.py`와 동일 패턴).

**Stage 2 사전조건 (af-doc-qa WARN 승격)**: Stage 1 완료 후 실측에서 경로 B(`inject_review_tasks`)가 실제로 호출되는지 smoke test를 성공해야 Stage 2 착수. 실패 시 Stage 2 보류하고 경로 B 복구를 선결.

### 5.6 쿨다운 & 과잉 발화 방지 (af-critic WARN-5 대응)

`[af-review-pending]` 메시지를 세션당 무제한 발화하지 않도록 `check_pending_review.py`에 **쿨다운**과 **세션 throttle**을 추가한다.

- **파일 쿨다운**: 같은 파일이 최근 N분 이내 이미 발화됐으면 skip
- **배치 간격**: 기존 `MIN_BATCH_INTERVAL_SEC`를 명시적 상수(기본 300초)로 유지
- **세션 발화 상한**: `.af_review_queue/session_fires.json`에 세션 UUID당 발화 횟수 기록, 기본 10회 초과 시 stdout 대신 stderr로 warn-only
- **마커 consumed 표시**: 발화 후 마커 파일에 `"fired_at"` 타임스탬프 기록. 다음 UserPromptSubmit은 `fired_at` 이후 `updated_at`만 비교해 새 수정만 발화

설계 단순화를 위해 Stage 1에서는 **배치 간격 + 마커 consumed 표시**만 구현. 나머지(세션 상한)는 Stage 2로.

### 5.7 검증 가능성 (관측성)

- `.af_review_queue/hook_events.log`(append-only) 신설. 훅 실행 시점·파일·builtin 이름·exit code 기록
- 기록 포맷: `ISO8601 | builtin | file | exit`
- 배포물의 `CrossVerificationLoop` 완료 시점에도 동일 로그에 쓰기 (Stage 2)

## 6. 경로 B (배포물) 쪽 변경

### 6.1 본 설계 범위
- `inject_review_tasks`가 `REVIEW_ROLES` 상수 사용으로 전환 (Stage 2)
- 실제 작동 검증: 다음 build 태스크 주입 시 CrossVerificationLoop가 실행되는지 smoke test 추가

### 6.2 본 설계 범위 외 (Stage 3 이후)
- `af review <file>` CLI 서브커맨드 신설
- 배포 zip에 `.claude/settings.json` 선택적 포함 여부 — 엔드유저가 Claude Code를 쓰는지 수요 조사 필요

## 7. 회귀·리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 훅 교체 중 일부 경로 누락 | 자동 검증 부분 미작동 | Stage 1 완료 후 `Edit` → 마커 파일 생성 E2E 테스트 의무화 |
| `scripts/`에서 `core/` import 시 순환 or 배포 missing | ImportError | 최소 의존 모듈(`review_targets.py`)만 core에 두고 scripts에서 경량 import |
| Claude Code 버전 업으로 hook stdin 스키마 변경 | 다시 깨짐 | `hook_runner.py`에 스키마 버전 체크 + 경고 로그 |
| 경로 B `inject_review_tasks`가 실제로는 작동하지 않고 있었을 가능성 | P4 미해결 | 설계 문서 채택 후 실측(build 태스크 하나 태움) |
| `.claude/settings.local.json`을 `settings.json`으로 개명 (공유 설정화) | 엔드유저마다 다른 개인 설정 덮어씀 | 본 설계에서는 개명 안 함. 별도 결정 |

## 8. 테스트 전략

### 8.1 단위 테스트
- `tests/test_review_targets.py` 신규: `is_review_target` / `review_roles_for` 경계 케이스
- `tests/test_hook_runner.py` 신규 또는 확장: stdin JSON 파싱, 파일 경로 추출, 비정상 JSON 방어

### 8.2 통합(E2E) 테스트 (v3: 폐기 이름 제거)
1. 파일 편집 시뮬레이션: `echo '{"tool_input":{"file_path":"core/x.py"}}' | python3 scripts/hook_runner.py post_edit_enqueue` → 마커 생성 확인
2. py_compile 경로: `echo '{"tool_input":{"file_path":"core/x.py"}}' | python3 scripts/hook_runner.py post_edit_py_compile` → 문법 오류 시 stderr 출력, 파일 없으면 silent 0 exit
3. 비대상 파일 테스트: `echo '{"tool_input":{"file_path":"docs/x.md"}}' | python3 scripts/hook_runner.py post_edit_enqueue` → 마커 미생성 확인
4. 비정상 JSON stdin: `echo 'not-json' | python3 scripts/hook_runner.py post_edit_enqueue` → 훅 exit 0 + 마커 미생성
5. `check_pending_review.py` 단독 실행 → 마커 있을 때 `[af-review-pending]` 출력, 없을 때 침묵
6. 관측성 로그: 위 테스트들 실행 후 `.af_review_queue/hook_events.log`에 해당 builtin·file·exit_code가 기록됐는지 확인

### 8.3 회귀
- 기존 Claude Code `SessionStart`/`UserPromptSubmit` 훅 동작 불변 확인 (Continuity snapshot 로드 정상)
- `core/project_task_board.py:inject_review_tasks` 기존 테스트 전체 PASS

### 8.4 실측(Smoke)
- 설계 채택 후 세션에서 `Edit` 도구로 `core/*.py` 1건 수정 → 다음 UserPromptSubmit에 `[af-review-pending]` 출력되는지 확인

## 9. Master_Blueprint 갱신 범위

- §0 빠른 참조: `core/review_targets.py` 신규 행 추가 (Stage 2 완료 시)
- §3 서브시스템: 훅 시스템 섹션 보강 (경로 A / 경로 B 도식)
- §10 Blast Radius: `hook_runner.py`, `review_targets.py` 영향 범위
- §11 에러 코드 해설 (af-doc-qa WARN 반영): "PostToolUse hook no-op (env var reference)" 항목 추가 — 증상/근원/수정/감지법
- §12 변경 이력: "2026-04-17 교차검증 훅 복구 (stdin JSON 파싱) + 규칙 SSOT" 한 줄

## 9.5 롤백 절차 (af-critic WARN-6 대응)

각 Stage 별 명시적 롤백 커맨드 + 선행 조건.

### Stage 1 롤백
- **커맨드**: `git checkout HEAD~1 -- .claude/settings.local.json scripts/hook_runner.py scripts/enqueue_agent_review.py`
- **영향**: 훅이 다시 no-op 상태로 복귀 (이전 상태와 동일, 악화 없음)
- **후속**: 없음 (데이터 손실 없음, 마커는 생성돼도 새 로직이 소비하지 않으므로 무시됨)

### Stage 2 롤백
- **선행 조건**: Stage 2 커밋은 **두 단계로 나눈다**.
  1. 커밋 A: `core/review_targets.py` 신설 + 양 경로에서 **import만 추가**(기존 하드코딩 병존, 참조만 dead import)
  2. 커밋 B: 기존 하드코딩 제거 + `review_targets` 사용으로 전환
- 이 순서를 지키면 커밋 B만 롤백해도 커밋 A의 신규 모듈은 dead code로 남을 뿐 크래시 없음.
- **커맨드**: `git revert <커밋 B SHA>` (A는 유지 가능)
- **크래시 조건**: 커밋 B만 존재하는 상태에서 `review_targets.py`를 삭제하면 ImportError. 순서를 반드시 지킬 것.

### Stage 3 롤백 (Out-of-Scope지만 기록)
- `af review` CLI 서브커맨드 제거 + 훅 명령을 Stage 1 상태로 되돌림

## 10. 실행 체크리스트 (v2 반영)

### Stage 1 (즉시 복구)
- [ ] v2 교차검증 재실행 (af-doc-qa + af-critic 병렬) → PASS 확인
- [ ] `hook_runner.py:main()` 진입 지점에 `_BUILTINS` 분기 테이블 추가 (기존 script-resolve 경로 보존)
- [ ] builtin 함수 5종 구현: `post_edit_py_compile`, `post_edit_enqueue`, `post_edit_code_review`, `post_edit_blueprint`, `post_edit_design_review`
- [ ] `_read_hook_stdin_once()` + `_extract_file_path()` 헬퍼 신설
- [ ] `enqueue_agent_review.py`를 tempfile + os.replace 기반 atomic write로 교체
- [ ] `.claude/settings.local.json`의 6개 PostToolUse 명령을 `python3 scripts/hook_runner.py post_edit_*`로 교체 (개별 항목 구조 · timeout · statusMessage 유지)
- [ ] `check_pending_review.py`에 마커 consumed 타임스탬프 + 배치 간격 상수 명시
- [ ] 단위 테스트 `tests/test_hook_runner_builtins.py` 신규
- [ ] E2E 시뮬레이션 테스트 (echo JSON | python3 hook_runner.py ...)
- [ ] Master_Blueprint §11 에러 코드 해설에 "PostToolUse hook no-op" 항목 추가
- [ ] 실제 Claude Code 세션 smoke: `Edit core/*.py` → 마커 생성 → 다음 UserPromptSubmit에서 `[af-review-pending]` 출력 확인

### Stage 2 (SSOT 통합) — Stage 1 smoke 성공 후 착수
- [ ] **사전조건**: 경로 B 실측 — build 태스크를 하나 태워 `inject_review_tasks` 호출 및 `CrossVerificationLoop` 실행 확인 (P4)
- [ ] 커밋 A: `core/review_targets.py` 신설 + 단위 테스트 + 양 경로에서 import만 추가 (dead import OK)
- [ ] 커밋 B: `enqueue_agent_review.py` · `inject_review_tasks` 하드코딩 제거, `review_targets` 상수/함수로 전환
- [ ] 회귀 테스트 전체 PASS
- [ ] 관측성 로그 `.af_review_queue/hook_events.log` 기록 시작 (양 경로)
- [ ] Master_Blueprint §0/§3/§10/§12 갱신
- [ ] 동일 커밋(B)에 Blueprint + 코드 포함

## 11. Out-of-Scope (후속 과제)

- Stage 3: `af review <file>` CLI 서브커맨드 신설 및 배포 zip 통합
- 배포 zip에 Claude Code 훅 동봉 여부 결정 (엔드유저 수요 조사)
- `.claude/settings.local.json` → `settings.json` 개명 (공유 설정화)
- 경로 B의 `CrossVerificationLoop` 실제 작동 감사 로그 정착
- Windows PowerShell 훅 실행 호환성 점검

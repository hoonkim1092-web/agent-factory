# Setup Wizard — TAVILY & NotebookLM 통합 설계 (v3.2, Phase 0.5 실측 반영)

- **작성일**: 2026-04-10 (v1) / 개정 2026-04-11 (v3 → v3.2)
- **버전**: v3.2 (Phase 0.5 실측으로 `_check_notebooklm_auth` exit code 정정 + 파서 확정)
- **상태**: Draft (최종 교차검증 대기)
- **Phase 0 검증 완료**: `notebooklm-cli` 0.1.12, import 이름 `nlm`, Typer 기반, 27 서브모듈, CDP 사용(Playwright 비의존), `nlm notebook {list,create,get,query,delete}` + `nlm auth status` + `nlm login [--manual -f FILE]` 실측
- **Phase 0.5 실측 완료 (2026-04-11)**: `nlm auth status` **exit code 0(성공)/2(실패)** 구분 확인, `nlm login` 성공 출력 확인, `nlm notebook create` UUID 포맷 확정, **`nlm notebook list` 출력이 순수 JSON 배열** 확인. `DEFAULT_ARCHIVE_NOTEBOOK_ID`가 원 저자 본인 노트북임을 실측 확인.
- **관련 파일**: `run_factory_cli.py`, `core/setup_wizard.py`, `core/researcher.py`, `core/research_engine.py`, `skills/research_assistant/skill.py`, `build_exe.py`, `af.spec`, `install-af.ps1`, `install-af.sh` (신규), `requirements.txt`, `version.py`, `Master_Blueprint.md`, `docs/2026-04-03-session-handoff.md`

---

## 0. 버전별 변경 요약

### v1 → v2 (Phase 0 실측 반영)
- 가정했던 `notebooklm-tools` 패키지가 PyPI에 없음을 Phase 0으로 확정
- 실제 패키지명 `notebooklm-cli`, import 이름 `nlm` 으로 전면 교체
- 수정 대상 파일이 7개 → 23행으로 확장 (데드코드 교체 포함)

### v2 → v3 (재교차검증 BLOCK 해소)

| 출처 | v2 지적 | v3 해소 |
|------|---------|---------|
| critic BLOCK-A | Windows `fcntl` 폴백 미구현 | **`filelock` 패키지 도입** (크로스플랫폼 자동) — `§4.1`, `§4.6.1`, `§4.6.2` |
| critic BLOCK-B | Typer `standalone_mode` 미명시 → `SystemExit` 전파 위험 | `app(rest, standalone_mode=False)` 명시 + subprocess 경계 설명 — `§4.5`, `§7.3` |
| **critic BLOCK-C** | **`DEFAULT_ARCHIVE_NOTEBOOK_ID` = Himari 개인 UUID → 신규 사용자 전면 실패** | **자동 노트북 생성 플로우** — 첫 로그인 시 `nlm notebook list` 탐색 → 없으면 `nlm notebook create` → UUID를 `.af_setup_state.json`에 저장. `research_engine.py`는 state에서 로드 (하드코딩 제거) — `§4.1`, `§4.4-C`, `§4.7` |
| critic WARN-1 | `sys.argv` 백업/복원 미반영 | `§4.5` 코드 스니펫에 `try/finally` 블록 |
| critic WARN-2 | `typer`/`rich` sub-module hiddenimports 불완전 | PyInstaller `--collect-submodules typer rich` 폴백 — `§4.6.2` |
| critic WARN-3 | M7 수동 회귀만으로 `nlm` 업그레이드 파손 감지 불가 | `@pytest.mark.slow` 통합 테스트 2건 추가 — `§8.2` |
| doc-qa Fix-1 | `§5` row 23 "12종" → 실제 19종 불일치 | `§5` row 23 "20종"으로 수정 (테스트 1건 추가 반영) |
| doc-qa Fix-2 | 환경변수 기존/신규 구분 누락 | `§2 G6` 각주 — `AGENT_SKIP_SETUP_HINT`는 기존, `AGENT_NONINTERACTIVE`/`AGENT_FORCE_SETUP_WIZARD`는 신규 |
| doc-qa Fix-3 | `--collect-submodules` 누락 (critic WARN-2와 동일) | 위 WARN-2와 동시 해소 |
| doc-qa Fix-4 | atomic write 주석 부족 | `§4.1` 주석에 "tmp는 path와 같은 디렉토리여야 `os.replace` 원자성 보장" 추가 |
| doc-qa Fix-5 | `researcher.py:336` 실측 `333` 오차 | `§3.2` 라인 정정 |

### v3 신규 추가 (Phase 0 확장 실측)
- `nlm notebook` 서브커맨드 트리 확인 — `list`, `create`, `get`, `describe`, `rename`, `delete`, `query` 모두 존재
- `nlm notebook query` = "Chat with notebook sources" — 기존 `research_engine.py::query_notebooklm`의 공식 대체
- 결론: BLOCK-C 해결책 (A) 자동 노트북 생성이 공식 CLI 기반으로 성립 가능

### v3 → v3.2 (Phase 0.5 실측 반영 — 2026-04-11)

| v3 가정 (부정확) | v3.2 실측 결과 |
|-------------------|----------------|
| `nlm auth status` exit code "항상 0" (→ stdout 파싱 의무) | **실제는 성공 0 / 실패 2로 구분 가능**. v3에서 제가 기록한 "exit 0"은 `... | head -20; echo $?` 파이프라인 마지막 명령인 `head`의 exit code를 본 관찰 오류. 실제 소스 `nlm/cli/auth.py:59`는 `raise typer.Exit(2)` |
| `_parse_notebook_create_output()` UUID 정규식 휴리스틱 (출력 포맷 미실측) | 실측 포맷: `✓ Created notebook: <title>\n  ID: <uuid>` → **multiline regex로 확정** (정확한 패턴은 §4.4 `_CREATE_ID_RE` 코드 스니펫 기준, UUID 하이픈 위치까지 엄격 검증) |
| `_parse_notebook_list_for_title()` "JSON 또는 표 포맷, 실측 필요" | **실측 결과 순수 JSON 배열**. `json.loads(stdout)` 한 줄로 충분. 각 객체 `{id, title, source_count, updated_at}`. **WARN "list 파서 실패 → 중복 생성" 자동 해소** |
| `DEFAULT_ARCHIVE_NOTEBOOK_ID` "Himari 개인 UUID, 신규 사용자 전면 실패" | **실측 확인**: 해당 UUID는 **원 저자(hoon) 본인** NotebookLM 계정의 "Google Antigravity: Comprehensive Guide..." 노트북 (`source_count=59`). 원 저자에게는 우연히 작동하지만 **신규 사용자는 여전히 접근 불가**. 따라서 BLOCK-C 해결책 (자동 생성 + state 저장)는 그대로 유효 |
| `nlm login` 성공 출력 포맷 (미실측) | **실측 포맷**: `✓ Successfully authenticated!` + `Profile: default` + `Cookies: N extracted` + `CSRF Token: Yes` + `Credentials saved to: <path>` |
| `nlm auth status` 성공 출력 포맷 (미실측) | **실측 포맷**: `Validating credentials for profile: <name>...` + `✓ Authenticated` + `Email: <email or Unknown>` + `Profile: <name>` + `Notebooks accessible: <count>` + `Credentials path: <path>` |
| `nlm auth status` 실패 출력 포맷 (부분 실측) | **실측 확인**: `✗ Not authenticated` + `Profile not found: <profile>` + Hint + **exit code 2** |

**v3.2의 시사점**:
- `_check_notebooklm_auth()` 구현이 **exit code 우선 + stdout 보조**로 단순화됨 (§4.4 코드 스니펫 수정)
- `_parse_notebook_list_for_title()` 구현이 **`json.loads()` 한 줄**로 단순화됨 (휴리스틱 regex 불필요)
- v3 §7.11의 "list 파서 실패 → 무음 중복 생성" WARN이 자동 해소 (JSON 파싱 실패 확률 극도로 낮음)
- U5 (파서 포맷 미검증) **완전 해소**

---

## 1. 배경 및 문제 정의

### 1.1 원래 문제 (v1)

`core/research_engine.py`, `core/researcher.py`, `skills/research_assistant/skill.py`가 `python -m notebooklm_tools.cli.main`을 호출하지만, `notebooklm_tools` import는 **한 번도 성공한 적이 없음**. `researcher.py:333`의 `importlib.util.find_spec("notebooklm_tools") is None` 가드가 **항상** 발동. `docs/2026-04-03-session-handoff.md:172`에 "미완료"로 기록된 항목은 실제로는 **존재하지 않는 패키지**를 가리키고 있었음.

### 1.2 Phase 0 실측 결과 (2026-04-10)

**패키지 확정**:
```
$ .venv/bin/pip install notebooklm-cli
Successfully installed notebooklm_cli-0.1.12 typer-0.24.1 rich-14.3.3
                      click-8.3.2 pygments-2.20.0 markdown-it-py-4.0.0
                      mdurl-0.1.2 shellingham-1.5.4 websocket-client-1.9.0
                      annotated-doc-0.0.4 platformdirs-4.9.6
```

**import 구조**:
```
$ .venv/bin/python -c "import nlm; ..."
nlm, nlm.__main__, nlm.ai_docs,
nlm.cli.{alias,auth,chat,config,main,notebook,repl,research,source,studio},
nlm.core.{alias,auth,auth_refresh,client,constants,exceptions,models},
nlm.output.{formatters},
nlm.utils.{browser,cdp,config}
→ 총 27 서브모듈, Playwright 비의존 (CDP 사용)
```

**CLI 커맨드 트리 실측**:
```
$ nlm --help
Commands: login, notebook, source, chat, studio, research, alias, config,
          audio, report, quiz, flashcards, mindmap, slides, infographic,
          video, data-table, auth

$ nlm notebook --help
Commands: list, create, get, describe, rename, delete, query

$ nlm notebook create --help
Usage: nlm notebook create [OPTIONS] [TITLE]
  --profile -p TEXT  Profile to use

$ nlm login --help
Usage: nlm login [OPTIONS]
  Default: Uses Chrome DevTools Protocol to extract cookies automatically.
  Use --manual to import cookies from a file.
  --manual -m            Manually provide cookies from a file
  --check                Only check if current auth is valid
  --profile -p TEXT      Profile to save to [default: default]
  --file -f TEXT         Path to file containing cookies (manual mode)

$ nlm auth status
✗ Not authenticated
  Profile not found: default
(exit code: 0)   ← ⚠ 실패인데도 0 반환. 반드시 stdout 파싱으로 판정.
```

### 1.3 사용자 요구 (2026-04-10~11 확정)

사용자 발언 원문:

> 비대화형이든, 대화형이든 FSA, ISE 모드 모두 TAVILY, NotebookLM 파이프라인에서 돌도록 한다.
> 단 TAVILY key가 없다면 사용자에게 "TAVILY가 없으면 결과물의 품질이 낮아진다" 경고 창을 띄움과 동시에 TAVILY key를 입력할 수 있는 UI를 제공한다.
> TAVILY key를 입력 안 하고도 다음으로 진행할 수 있도록 한다, 단 이때도 TAVILY가 없으면 결과물의 품질이 낮아진다 경고 창을 띄워준다.
> notebooklm_tools 패키지 설치는 배포된 빌드를 설치할 때 같이 설치가 되도록 설계.
> notebooklm OAuth 로그인을 하도록 강제 유도하도록 설계.
> install 스크립트는 macOS/Windows 모두 작동해야 한다, OS 별로 동등하게.

Q&A 확정:
- **Q1 = A**: PyInstaller bundle에 `nlm` 완전 내장
- **Q2 = Y/N 재확인 루프**: TAVILY 스킵 선택 → 재확인 박스 → `y`=진행/`N`=입력UI 복귀
- **Q3 = Medium**: 자동 `nlm login` 제안 → 스킵 가능
- **U1** (`AGENT_NO_BROWSER_LOGIN`): **제거** (`nlm login --manual`이 공식 대체)
- **U3** (`install-af.sh`): **포함** — Windows(`install-af.ps1`)와 **동등 동작**
- **BLOCK-C 해결안**: **(A) 자동 노트북 생성** — 첫 로그인 후 `nlm notebook list`로 기존 "Agent Factory Archive" 탐색 → 없으면 `nlm notebook create` → UUID를 `.af_setup_state.json`에 저장

---

## 2. 목표 / 비목표

### 2.1 Goals

- **G1**. 모든 실행 모드(bare `af`, `--fsa`, `--ise`, `--chat`, `-t`)에서 TAVILY/NotebookLM 점검 플로우가 동일하게 작동
- **G2**. TAVILY_API_KEY 미설정 시 경고 박스 → 입력 UI → 스킵 시 Y/N 재확인 → 둘 다 파이프라인 진행 가능
- **G3**. NotebookLM **Medium 강도**: 첫 실행 시 자동으로 `nlm login` 호출, 실패해도 파이프라인 진행
- **G4**. 배포 빌드(PyInstaller)에 `nlm` 완전 내장 — 사용자 `pip install` 불필요
- **G5**. 결정된 "스킵" 상태는 영속 저장, 재실행 시 반복 프롬프트 없음
- **G6**. CI/자동화 환경용 완전 억제 옵션
  - `AGENT_SKIP_SETUP_HINT=1` **(기존 변수)** — 이미 `core/setup_wizard.py:156`에 존재, v3에서는 `ensure_external_research_capabilities()`가 이를 감지해 `"silent"` 모드 진입
  - `AGENT_NONINTERACTIVE=1` **(신규 변수)** — TTY가 있어도 강제로 비대화형 모드
  - `AGENT_FORCE_SETUP_WIZARD=1` **(신규 변수)** — 상태 파일 무시하고 프롬프트 재표시
- **G7**. `install-af.ps1` (Windows) + `install-af.sh` (macOS/Linux) **동등 기능 보장**: 다운로드 → 설치 → PATH 등록 → Chrome 설치 확인 → `__check-nlm` 검증
- **G8**. 기존 데드코드(`notebooklm_tools` 참조) 전량을 살아있는 코드(`nlm`)로 교체
- **G9** (v3 신규). **사용자별 NotebookLM 아카이브 노트북을 자동 관리** — 하드코딩된 UUID 제거, `state.notebooklm.archive_notebook_id` 저장/로드. 신규 사용자도 즉시 사용 가능

### 2.2 Non-Goals

- **NG1**. `hound_librarian` skill 경로와 `researcher.py::DualMotorResearcher` 경로의 중복 통합
- **NG2**. `nlm` 자체의 OAuth 로직 재구현
- **NG3**. GOOGLE_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY 입력 플로우 개선
- **NG4**. Chrome 자동 설치 (경고만 표시)
- **NG5**. `requirements.txt` 전면 정리 — 이번 PR은 필요한 3줄만 추가

---

## 3. 현재 상태 분석

### 3.1 호출 그래프 (변경 없음)

```
run_factory_cli.main()
├─ (no args / --interactive) → check_and_hint() → 경고만, 입력 UI 없음
├─ (setup) → run_setup(interactive=True) → 완전한 입력 마법사 (수동 진입)
├─ (--fsa / --ise / --chat / -t / -p) → check_and_hint() 미호출
└─ _launch_interactive_mode()
    └─ run_interactive() → PDCAInteractiveChat → 사용자 입력 수신
        └─ Himari Bootstrap
            └─ core/researcher.py::DualMotorResearcher.gather_evidence()
                ├─ _collect_local_references()        ◀── 작동
                ├─ _collect_web_references()          ◀── TAVILY 키 있을 때만
                ├─ _collect_llm_prior_knowledge()     ◀── TAVILY 없을 때 폴백
                └─ _collect_notebook_summary()        ◀── 데드코드 (notebooklm_tools 미존재)
```

### 3.2 코드 참조 실측 (라인 정정 반영)

| 파일 | 라인 | 현재 내용 | 조치 |
|------|------|----------|------|
| `run_factory_cli.py` | 159-164 | bare `af` → `check_and_hint()` | gate 확장 대체 |
| `run_factory_cli.py` | 167-170 | `setup` → `run_setup()` | STAGE 1 이전 처리 유지 |
| `run_factory_cli.py` | 172-177 | `worker` 서브커맨드 분기 | STAGE 1 이전 처리 유지 |
| `run_factory_cli.py` | 217-227 | `--fsa` 등 setup 미호출 | gate 추가 |
| `core/setup_wizard.py` | 15-44 | `_KEYS` 리스트 (TAVILY 포함) | 유지 + 확장 |
| `core/setup_wizard.py` | 97-148 | `run_setup()` 대화형 | 유지 |
| `core/setup_wizard.py` | 151-179 | `check_and_hint()` 경고만 | `ensure_external_research_capabilities()`로 대체 |
| `core/setup_wizard.py` | 156 | `AGENT_SKIP_SETUP_HINT` 가드 | v3 기존 변수로 재활용 |
| `core/researcher.py` | 307-331 | `_collect_web_references()` TAVILY 게이트 | 스킵 로그 1회 추가 |
| `core/researcher.py` | 330-362 | `_collect_notebook_summary()` `notebooklm_tools` 참조 | **`nlm`으로 전면 교체** |
| `core/researcher.py` | **333** | `find_spec("notebooklm_tools")` (**v2 오차 정정: 기존 v2는 336 표기**) | `find_spec("nlm")` |
| `core/researcher.py` | 507-511 | Sufficiency Gate 분기 | 유지 |
| `core/researcher.py` | 543-553 | NotebookLM 호출 조건 | 유지 |
| `core/research_engine.py` | 1-286 | **전체 파일이 `notebooklm_tools.cli.main` 호출 + 하드코딩 UUID** | **전면 재작성** (`nlm` 사용 + state 로드) |
| `core/research_engine.py` | 13 | `DEFAULT_ARCHIVE_NOTEBOOK_ID = "eaa34a54-..."` | **제거** — state에서 로드 |
| `core/research_engine.py` | 33 | `cmd = [sys.executable, "-m", "notebooklm_tools.cli.main", *args]` | `_nlm_cmd_base()` 유틸 + frozen 분기 |
| `core/research_engine.py` | 61 | `notebooklm_tools.cli.main` login | `["nlm", "login"]` or `["af", "__nlm", "login"]` |
| `skills/research_assistant/skill.py` | 38-82 | `notebooklm_tools` 3회 참조 | **전면 교체** |
| `af.spec` | 19-240 | `hiddenimports` (`core.setup_wizard` 있음) | `nlm.*` 27개 + typer/rich/tavily/filelock 추가 |
| `requirements.txt` | 1-4 | 4줄만 (langchain) | `notebooklm-cli>=0.1.12,<0.2`, `tavily-python`, **`filelock>=3.0`** 추가 |
| `install-af.ps1` | 1-159 | Windows 설치 스크립트 | Chrome 체크 추가, 버전 문자열 bump, `__check-nlm` 검증 |
| `install-af.sh` | — | **존재하지 않음** | **신규 작성** |
| `Master_Blueprint.md` | §3.1~§3.10 | Setup Wizard 섹션 없음 | **§3.11 신규 생성** |
| `docs/2026-04-03-session-handoff.md` | 172 | `pip install notebooklm-tools` (잘못됨) | `pip install notebooklm-cli`로 수정 + 완료 체크 |

---

## 4. 설계

### 4.1 영속 상태 파일 — `.af_setup_state.json` (BLOCK-C 확장 + BLOCK-A 해소)

**경로**: `.env`와 동일 디렉토리.

**스키마 v2** (BLOCK-C 해결을 위한 `archive_notebook_id` 필드 추가):
```json
{
  "schema_version": 2,
  "tavily": {
    "decision": "pending" | "configured" | "skipped",
    "last_prompt_at": "2026-04-10T12:30:00Z"
  },
  "notebooklm": {
    "decision": "pending" | "logged_in" | "skipped" | "login_failed" | "chrome_missing",
    "profile": "default",
    "archive_notebook_id": "eaa34a54-a898-46a0-835a-cdb6024887f0",   /* 사용자별 생성 */
    "archive_notebook_title": "Agent Factory Archive",
    "last_login_attempt_at": "2026-04-10T12:30:00Z",
    "last_login_error": "optional short message"
  }
}
```

**schema_version 마이그레이션**:
- `1 → 2`: 기존 파일에 `archive_notebook_id`, `archive_notebook_title` 필드 없음. 로드 시 자동으로 `null`로 채움 → 다음 로그인 시 재생성 플로우 진입.

**`_save_setup_state(state)` 구현 명세 (BLOCK-A 해소 — `filelock` 사용)**:

```python
import json, os, tempfile
from filelock import FileLock, Timeout  # 크로스플랫폼 (Linux/macOS/Windows)

def _save_setup_state(state: dict) -> None:
    """
    Atomic write + 크로스플랫폼 파일락.

    BLOCK-A 해소: filelock 패키지는 POSIX(fcntl)와 Windows(msvcrt.locking)를
                 내부적으로 자동 선택하므로 OS 분기 코드 불필요.
    BLOCK #3 해소: tempfile은 path와 같은 디렉토리에 생성해야
                   os.replace가 원자적으로 작동한다 (cross-device rename 금지).
    """
    path = _get_setup_state_path()
    dir_ = os.path.dirname(path) or "."
    os.makedirs(dir_, exist_ok=True)

    # 스키마 검증 (쓰기 전)
    if not isinstance(state, dict) or "schema_version" not in state:
        raise ValueError("setup_state: schema_version 누락")

    lock_path = path + ".lock"
    lock = FileLock(lock_path, timeout=10)
    try:
        with lock:
            # 동일 디렉토리에 tmp 생성 → os.replace 원자성 보장
            # (tmpdir이 다른 파일시스템이면 os.replace가 cross-device로 실패)
            fd, tmp = tempfile.mkstemp(
                prefix=".af_setup_state.",
                suffix=".tmp",
                dir=dir_,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)  # atomic on POSIX and Windows (NTFS)
            except Exception:
                try: os.unlink(tmp)
                except OSError: pass
                raise
    except Timeout:
        # 다른 프로세스가 10초 동안 락을 쥐고 있음 — gate가 파이프라인을
        # 막아서는 안 되므로 경고만 출력하고 진행
        print("[Setup] Warning: state 파일 락 타임아웃, 저장 스킵", file=sys.stderr)
```

**`_load_setup_state()` 스키마 v2 검증**:

```python
_DEFAULT_STATE = {
    "schema_version": 2,
    "tavily": {"decision": "pending", "last_prompt_at": None},
    "notebooklm": {
        "decision": "pending",
        "profile": "default",
        "archive_notebook_id": None,
        "archive_notebook_title": "Agent Factory Archive",
        "last_login_attempt_at": None,
        "last_login_error": None,
    },
}

_VALID_TAVILY = {"pending", "configured", "skipped"}
_VALID_NOTEBOOKLM = {"pending", "logged_in", "skipped", "login_failed", "chrome_missing"}

def _load_setup_state() -> dict:
    path = _get_setup_state_path()
    if not os.path.isfile(path):
        return _deep_copy_default()

    lock = FileLock(path + ".lock", timeout=5)
    try:
        with lock:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except (json.JSONDecodeError, OSError, Timeout):
        return _deep_copy_default()

    # 엄격 스키마 검증
    if not isinstance(data, dict):
        return _deep_copy_default()

    # schema_version 1 → 2 마이그레이션
    if data.get("schema_version") == 1:
        data["schema_version"] = 2
        data.setdefault("notebooklm", {}).setdefault("archive_notebook_id", None)
        data["notebooklm"].setdefault("archive_notebook_title", "Agent Factory Archive")

    if data.get("schema_version") != 2:
        return _deep_copy_default()

    # 필드별 enum 검증
    tv = data.get("tavily", {})
    if not isinstance(tv, dict) or tv.get("decision") not in _VALID_TAVILY:
        data["tavily"] = dict(_DEFAULT_STATE["tavily"])

    nb = data.get("notebooklm", {})
    if not isinstance(nb, dict) or nb.get("decision") not in _VALID_NOTEBOOKLM:
        data["notebooklm"] = dict(_DEFAULT_STATE["notebooklm"])

    return data
```

**재설정 수단**:
- `af setup`: `run_setup()` 강제 호출
- `AGENT_FORCE_SETUP_WIZARD=1` **(신규)**: 상태 파일 무시
- `AGENT_NONINTERACTIVE=1` **(신규)**: 강제 비대화형
- `AGENT_SKIP_SETUP_HINT=1` **(기존, `core/setup_wizard.py:156`)**: 완전 침묵
- 파일 직접 삭제

### 4.2 `core/setup_wizard.py` 확장 — 공개 API

```python
def ensure_external_research_capabilities(
    *,
    mode: str = "auto",
) -> dict:
    """
    파이프라인 실행 직전 호출되는 단일 진입점.

    mode:
        "auto"           — stdin.isatty() + AGENT_NONINTERACTIVE 감안 자동 결정
        "interactive"    — 강제 대화형
        "noninteractive" — 강제 비대화형 (경고만)
        "silent"         — AGENT_SKIP_SETUP_HINT=1 상태 (완전 침묵)

    Returns:
        {
          "tavily":     {"available": bool, "decision": str},
          "notebooklm": {"available": bool, "decision": str, "chrome": bool,
                         "archive_notebook_id": str | None},
        }
    """
```

**mode 결정 로직** (`_resolve_mode`):
```python
def _resolve_mode(mode: str) -> str:
    if mode != "auto":
        return mode
    # AGENT_SKIP_SETUP_HINT (기존 변수, setup_wizard.py:156에서 이미 사용)
    if os.getenv("AGENT_SKIP_SETUP_HINT"):
        return "silent"
    # AGENT_NONINTERACTIVE (v3 신규 변수)
    if os.getenv("AGENT_NONINTERACTIVE"):
        return "noninteractive"
    # TTY 자동 판별
    if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
        return "noninteractive"
    return "interactive"
```

**내부 함수**:
- `_load_setup_state()` / `_save_setup_state()` — §4.1
- `_ensure_tavily(state, resolved_mode)` — §4.3
- `_ensure_notebooklm(state, resolved_mode)` — §4.4
- `_check_chrome_installed()` — OS별 Chrome 감지
- `_check_notebooklm_auth(profile)` — stdout 파싱으로 인증 상태 판정
- `_run_notebooklm_login(profile, manual_cookie_file)` — `nlm login` subprocess
- `_find_or_create_archive_notebook(profile, title)` — **BLOCK-C 핵심 함수**
- `_parse_notebook_create_output(stdout)` — `nlm notebook create` 출력에서 UUID 파싱
- `_list_notebooks(profile)` — `nlm notebook list` JSON 파싱

### 4.3 TAVILY 인터랙티브 플로우 (Q2 = Y/N 재확인)

변경 없음 — v2와 동일.

```
┌─────────────────────────────────────────────────────────┐
│  ⚠  TAVILY_API_KEY 미설정                                │
│                                                         │
│  TAVILY가 없으면 웹 검색이 비활성화되어                    │
│  생성되는 문서/코드의 품질이 낮아집니다.                   │
│                                                         │
│  무료 발급: https://app.tavily.com                      │
└─────────────────────────────────────────────────────────┘
TAVILY_API_KEY 입력 (엔터=스킵): █
```

- **키 입력** → `.env` 저장 → `decision=configured`
- **엔터 (스킵)** → 재확인 박스 → `y`=skipped / `N`=입력 프롬프트로 복귀
- **Ctrl+C** → skipped 저장 후 다음 단계

### 4.4 NotebookLM Medium 강도 플로우 (BLOCK-C 해결 포함)

**선행 체크 순서**:
1. `importlib.util.find_spec("nlm")` — 모듈 존재
2. `_check_chrome_installed()` — Chrome 브라우저 시스템 설치 여부
3. `_check_notebooklm_auth(profile)` — 기존 로그인 세션 유효성
4. **(v3 신규)** `state.notebooklm.archive_notebook_id` 존재 + `nlm notebook get <id>`로 유효성 확인

#### `_check_notebooklm_auth()` 구현 (Phase 0.5 실측 반영)

```python
def _check_notebooklm_auth(profile: str = "default") -> str:
    """
    Phase 0.5 실측 기준 (nlm 0.1.12):
      성공 → exit code 0 + stdout "✓ Authenticated"
      실패 → exit code 2 + stdout "✗ Not authenticated" / "Profile not found"

    1차 판정: exit code (0=성공, 2=실패)
    2차 보조: stdout 문자열 패턴 (exit code 외 unknown 상태 방어)
    """
    try:
        cmd = _nlm_cmd_base() + ["auth", "status", "--profile", profile]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # 주의: nlm auth status 성공 시 실제 API 호출로 검증 (list_notebooks 1회)
        # → 네트워크 왕복 때문에 timeout 15→30초로 여유
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"

    out = (p.stdout or "") + (p.stderr or "")

    # 1차: exit code (Phase 0.5에서 nlm/cli/auth.py:59 `raise typer.Exit(2)` 확인)
    if p.returncode == 0:
        # 성공 exit 에도 출력 패턴 크로스체크 (방어적)
        if "✓" in out and "authenticated" in out.lower():
            return "logged_in"
        # exit 0인데 성공 패턴 없으면 nlm 버전 변경 가능성 → unknown
        # ⚠ 호출자는 "unknown"을 "logged_in 추정"으로 취급하되 경고 로그 출력 (§4.4 플로우)
        # R5/R11 Slow Integration Test가 다음 실행 주기에서 포맷 회귀 감지
        return "unknown"

    if p.returncode == 2:
        # 2차: 구체적 실패 원인 매칭 (로그/디버깅용, 판정은 동일)
        if "Profile not found" in out: return "not_authenticated"
        if "✗ Not authenticated" in out: return "not_authenticated"
        if "Authentication expired" in out or "Authentication failed" in out:
            return "not_authenticated"
        return "not_authenticated"

    # 다른 exit code → 알 수 없는 상태 (예: 네트워크 장애, 패키지 파손)
    return "unknown"
```

**⚠ v3 → v3.2 정정**: v3의 `_check_notebooklm_auth()`는 "nlm은 exit code 항상 0을 반환"이라고 잘못 기록했습니다. 이건 Phase 0 관찰 오류(파이프라인 `... | head -20`의 `$?`가 `head`의 exit를 본 것)였고, 실측 소스 `nlm/cli/auth.py:59`는 `raise typer.Exit(2)`로 명확히 2를 반환합니다. v3.2는 exit code 우선 판정으로 단순화.

#### **4.4-C. BLOCK-C 해결: `_find_or_create_archive_notebook()`**

**원칙**: 사용자 계정에 Agent Factory 전용 아카이브 노트북을 **자동으로 확보**한다. 이미 존재하면 재사용, 없으면 생성, 생성 실패 시 사용자 입력으로 폴백.

```python
def _find_or_create_archive_notebook(
    profile: str = "default",
    title: str = "Agent Factory Archive",
) -> tuple[str | None, str]:
    """
    Returns:
        (notebook_id, reason)
        notebook_id가 None이면 확보 실패 → 호출자가 스킵 또는 사용자 입력 폴백
    """
    # Step 1: 기존 노트북 목록 조회 (Phase 0.5 실측: JSON 배열 반환)
    list_parse_failed = False   # §7.11 완화책용 플래그
    try:
        cmd = _nlm_cmd_base() + ["notebook", "list", "--profile", profile]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if p.returncode == 0:
            nb_id = _parse_notebook_list_for_title(p.stdout, title)
            if nb_id:
                return (nb_id, "found_existing")
            # p.returncode == 0 + stdout 비어있지 않음 + nb_id is None
            # → JSON 파싱 실패 가능성 (매우 드묾, §7.11 완화책)
            if (p.stdout or "").strip() and not _looks_like_valid_json_array(p.stdout):
                list_parse_failed = True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        pass

    # §7.11 완화책: JSON 파싱 실패 감지 시 사용자에게 원본 stdout 표시 + 확인
    # (이 분기는 interactive mode에서만 활성, noninteractive는 조용히 create 진행)
    if list_parse_failed and _is_interactive_mode():
        if not _confirm_create_despite_parse_failure(p.stdout):
            # 사용자가 'u' 선택 → 수동 UUID 입력 경로로 전환
            manual_uuid = _prompt_manual_notebook_uuid(profile)
            if manual_uuid:
                return (manual_uuid, "manual_input")
            return (None, "list_parse_failed_user_canceled")

    # Step 2: 새 노트북 생성
    try:
        cmd = _nlm_cmd_base() + ["notebook", "create", title, "--profile", profile]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if p.returncode == 0:
            nb_id = _parse_notebook_create_output(p.stdout)
            if nb_id:
                return (nb_id, "created_new")
            return (None, "created_but_parse_failed")
        return (None, f"create_failed: {p.stderr[:200]}")
    except subprocess.TimeoutExpired:
        return (None, "create_timeout")
    except OSError as e:
        return (None, f"oserror: {e}")
```

**`_parse_notebook_list_for_title()`, `_parse_notebook_create_output()` — Phase 0.5 실측 확정**:

**Phase 0.5 실측 원본 (nlm 0.1.12)**:

```
# nlm notebook create "AF Phase 0.5 Tet"
✓ Created notebook: AF Phase 0.5 Tet
  ID: 03662da6-f29e-43aa-b403-79f41b728cf4
```

```json
# nlm notebook list (stdout은 순수 JSON 배열)
[
  {
    "id": "03662da6-f29e-43aa-b403-79f41b728cf4",
    "title": "AF Phase 0.5 Tet",
    "source_count": 0,
    "updated_at": "2026-04-11T02:03:26Z"
  },
  ...
]
```

**확정 파서 구현**:

```python
import json
import re

# create 출력: "  ID: <uuid>" 라인 매칭
_CREATE_ID_RE = re.compile(
    r"^\s*ID:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$",
    re.MULTILINE,
)

def _parse_notebook_create_output(stdout: str) -> str | None:
    """
    Phase 0.5 실측 포맷:
        ✓ Created notebook: <title>
          ID: <uuid>
    """
    m = _CREATE_ID_RE.search(stdout or "")
    return m.group(1) if m else None


def _parse_notebook_list_for_title(stdout: str, title: str) -> str | None:
    """
    Phase 0.5 실측 확인: nlm notebook list 출력은 순수 JSON 배열.
    각 객체: {id, title, source_count, updated_at}.
    """
    try:
        notebooks = json.loads(stdout or "[]")
        if not isinstance(notebooks, list):
            return None
        for nb in notebooks:
            if isinstance(nb, dict) and nb.get("title") == title:
                nb_id = nb.get("id")
                if isinstance(nb_id, str) and nb_id:
                    return nb_id
    except (json.JSONDecodeError, TypeError):
        pass
    return None
```

**왜 이게 robust한가**:
- `_CREATE_ID_RE`는 `  ID: ` prefix를 요구하므로 stdout에 다른 UUID(에러 메시지 등)가 섞여도 오매칭 없음
- `_parse_notebook_list_for_title`은 `json.loads()`라 파싱 실패 확률 극도로 낮음. v3 §7.11의 "list 파서 실패 → 중복 생성 위험" WARN이 자동 해소
- 두 파서 모두 **빈 결과를 안전하게 `None` 반환** → 호출자 (`_find_or_create_archive_notebook`)가 `§6.3` 폴백 박스로 자연스럽게 전환

#### NotebookLM Medium 플로우 전체 (v3)

```
[로그인 상태 체크: not_authenticated]

┌─────────────────────────────────────────────────────────┐
│  ⚠  NotebookLM 로그인 필요                               │
│  (Chrome DevTools Protocol 사용)                        │
└─────────────────────────────────────────────────────────┘
지금 브라우저를 열어 로그인하시겠습니까? [Y/n]: Y
  $ nlm login --profile default
  ✓ 로그인 완료

[아카이브 노트북 확보 시도]
  $ nlm notebook list --profile default
  (기존 "Agent Factory Archive" 없음)
  $ nlm notebook create "Agent Factory Archive" --profile default
  ✓ 노트북 생성: {uuid}
  → state.notebooklm.archive_notebook_id 저장

[Setup] ✓ NotebookLM 활성화 (archive: {uuid})
```

**아카이브 노트북 생성 실패 시 폴백**:

```
  ✗ 노트북 생성 실패: {error}
┌─────────────────────────────────────────────────────────┐
│  ⚠  아카이브 노트북 확보 실패                              │
│                                                         │
│  [1] 기존 노트북 UUID를 직접 입력                         │
│  [2] 지금 스킵 (다음 실행 시 재시도)                      │
│  [3] NotebookLM 없이 진행                                │
└─────────────────────────────────────────────────────────┘
선택 [1/2/3]: █
```

- **[1]** 사용자가 UUID 입력 → `nlm notebook get <id>`로 유효성 확인 → OK면 `state.archive_notebook_id` 저장
- **[2]** `decision=logged_in` 유지, `archive_notebook_id=None` → 다음 실행 때 재시도
- **[3]** 재확인 Y/N → `y`=`skipped`

**📌 원 저자 재설치 시 Note (v3.3, critic INFO#4 반영)**:

Phase 0.5 실측에서 원 저자(hoon) 계정에는 이미 `eaa34a54-a898-46a0-835a-cdb6024887f0` (`"Google Antigravity: Comprehensive Guide..."`, source_count=59)가 존재함을 확인했습니다. 그러나 `_find_or_create_archive_notebook()`은 **title 매칭**으로 기존 노트북을 찾으므로, 원 저자도 새 설치 시:
1. `nlm notebook list` → 기존 "Google Antigravity..." 노트북 발견하지만 title이 "Agent Factory Archive"와 불일치
2. → 새 "Agent Factory Archive" 빈 노트북 생성 → 새 UUID가 state에 저장
3. → **기존 59-source 노트북은 무시되고 새 빈 노트북이 사용됨**

이건 기능 오류가 아니라 **의도된 동작**입니다. 이유:
- 기존 노트북에는 Agent Factory와 무관한 자료가 섞여 있을 수 있음 (실제로 "Google Antigravity"는 Antigravity IDE에 대한 노트북)
- Agent Factory 전용 공간을 분리하는 것이 사서(Librarian) 모듈의 본래 취지
- 원 저자가 기존 노트북을 재사용하고 싶다면 §6.3 "[1] 기존 UUID 직접 입력" 경로로 명시적 선택 가능

구현 시 원 저자 / power user를 위해 다음 옵션을 setup wizard에 추가하는 것을 고려할 수 있으나 이번 PR 범위는 아님:
- `af setup --nlm-archive-uuid <uuid>` 플래그로 자동 생성 대신 기존 UUID 연결

**Chrome 미설치 분기** (변경 없음, v2와 동일):
```
┌─────────────────────────────────────────────────────────┐
│  ⚠  Chrome 미감지                                        │
│  [1] Chrome 설치 후 재시도                               │
│  [2] 수동 쿠키 파일 경로 입력                            │
│  [3] NotebookLM 없이 진행                                │
└─────────────────────────────────────────────────────────┘
선택 [1/2/3]: █
```

**`_check_notebooklm_auth()` 반환값 처리 플로우** (v3.3에서 critic WARN#1 해소):

| 반환값 | 호출자 처리 |
|--------|------------|
| `"logged_in"` | 정상 — 다음 단계(`_find_or_create_archive_notebook()`)로 |
| `"not_authenticated"` | 위의 "로그인 필요" 박스 표시 → Medium 플로우 |
| `"unknown"` | **stderr 경고 1회 출력** (`[Setup] ⚠ nlm auth status 출력 포맷을 해석하지 못함 — 로그인 상태 추정으로 진행. R5/R11 CI 회귀 감지 예정`) 후 **`"logged_in"`으로 간주하여 `_find_or_create_archive_notebook()` 호출**. 만약 이 단계에서 실제 인증이 깨져 있다면 `notebook list`/`create` 호출에서 drop되어 §6.3 폴백 박스로 자연스럽게 전환됨 |

**왜 `"unknown"`을 `"not_authenticated"`가 아닌 `"logged_in" 추정`으로 처리하는가**:
- exit code 0은 Click/Typer 성공 경로이므로 인증이 실제로 살아있을 가능성이 높음
- 잘못된 포맷 해석으로 사용자에게 불필요한 재로그인을 강요하는 것은 오히려 나쁜 UX
- 후속 `notebook list` 호출 실패가 "진짜 미인증"을 포착하는 2차 방어벽 역할
- R5/R11 Slow Integration Test가 CI에서 포맷 회귀를 감지

### 4.5 `run_factory_cli.py` 진입점 통합 (BLOCK-B 해결 + WARN-1)

**BLOCK-B 해결**: Typer `app(rest)` 호출은 기본 `standalone_mode=True` → `SystemExit`으로 종료. v3에서 명시적으로 `standalone_mode=False`를 사용.

**WARN-1 해결**: `sys.argv` 백업/복원 try-finally 블록.

```python
# run_factory_cli.py

_INTERNAL_SUBCOMMANDS_BEFORE_GATE = {
    "setup",           # 기존
    "worker",          # 기존
    "skill-create",    # 기존
    "skill-spec",      # 기존
    "preflight",       # 기존
    "skill-eval",      # 기존
    "skill-promote",   # 기존
    "__nlm",           # v3 신규
    "__check-nlm",     # v3 신규
}

def _run_setup_gate() -> None:
    """파이프라인 실행 전 setup 점검. 실패해도 진행."""
    try:
        from core.setup_wizard import ensure_external_research_capabilities
        ensure_external_research_capabilities(mode="auto")
    except Exception as e:
        print(f"[Setup] Warning: setup 점검 실패 — {e}", file=sys.stderr)


def _invoke_nlm_app(rest: list[str]) -> int:
    """
    frozen 환경 전용: nlm Typer app을 af 프로세스 내부에서 직접 호출.

    중요:
    - standalone_mode=False 로 호출해 SystemExit 전파를 차단한다
      (그렇지 않으면 Typer가 기본적으로 sys.exit()을 호출해
       run_factory_cli.main()의 정상 return이 깨진다 — BLOCK-B 해소)
    - sys.argv를 일시적으로 nlm 관점으로 바꾸고, 끝나면 반드시 복원한다
      (WARN-1 해소 — 전역 sys.argv 오염 방지)
    """
    from nlm.cli.main import app

    saved_argv = sys.argv
    try:
        sys.argv = ["nlm"] + list(rest)
        try:
            result = app(rest, standalone_mode=False)
            # Typer/Click이 standalone_mode=False일 때 int 또는 None을 반환
            return int(result) if isinstance(result, int) else 0
        except SystemExit as e:
            # 혹시 내부에서 SystemExit이 올라와도 프로세스를 죽이지 않음
            return int(e.code) if isinstance(e.code, int) else 1
        except Exception as e:
            print(f"[__nlm] 실행 오류: {e}", file=sys.stderr)
            return 2
    finally:
        sys.argv = saved_argv


def main(argv=None):
    effective_argv = argv if argv is not None else sys.argv[1:]

    # ── STAGE 1: 내부/숨은 서브커맨드는 gate 전에 즉시 분기 ──
    if effective_argv and effective_argv[0] in _INTERNAL_SUBCOMMANDS_BEFORE_GATE:
        cmd = effective_argv[0]
        rest = effective_argv[1:]

        if cmd == "setup":
            from core.setup_wizard import run_setup
            run_setup(interactive=True); return

        if cmd == "worker":
            from core.agent_worker import main as worker_main
            sys.argv = ["af-worker"] + rest
            worker_main(); return

        if cmd == "__nlm":
            exit_code = _invoke_nlm_app(rest)
            sys.exit(exit_code)   # 명시적 exit

        if cmd == "__check-nlm":
            try:
                import nlm  # noqa: F401
                sys.exit(0)
            except ImportError:
                sys.exit(1)

        if cmd == "skill-create": _run_skill_creator(rest); return
        if cmd == "skill-spec":   _run_skill_spec(rest); return
        if cmd == "preflight":    _run_preflight(rest); return
        if cmd == "skill-eval":   _run_skill_eval(rest); return
        if cmd == "skill-promote":_run_skill_promote(rest); return

    # ── STAGE 2: 일반 실행은 반드시 gate를 거침 ──
    _run_setup_gate()

    # ── STAGE 3: 기존 로직 ──
    if not effective_argv or effective_argv == ["--interactive"]:
        projects_root = _resolve_projects_root()
        _launch_interactive_mode(projects_root)
        return
    # ... 기존 argparse 분기 그대로 ...
```

**재귀 방지 + SystemExit 차단 증명**:
- `__nlm`은 STAGE 1에서 즉시 분기 → `_run_setup_gate()` 호출되지 않음 → 재귀 없음 (BLOCK-B의 §7.3 subprocess 경계 설명과 결합)
- `_invoke_nlm_app()`은 `standalone_mode=False` + `SystemExit` try/except로 프로세스 종료를 차단 (BLOCK-B 해소)
- `sys.argv` try/finally로 전역 오염 방지 (WARN-1 해소)

### 4.6 배포 빌드 변경

#### 4.6.1 `requirements.txt` (BLOCK-A + BLOCK-C 대응)

```diff
 langchain>=1.0,<2.0
 langchain-core>=1.0,<2.0
 langgraph>=1.0,<2.0
 langsmith>=0.3.0
+notebooklm-cli>=0.1.12,<0.2    # NotebookLM CLI (import name: nlm)
+tavily-python                  # Tavily 웹 검색 클라이언트
+filelock>=3.0                  # 크로스플랫폼 파일락 (BLOCK-A 해소)
```

#### 4.6.2 `af.spec` hiddenimports (BLOCK-A + WARN-2 + Fix-3 반영)

```python
hiddenimports=[
    # ... 기존 core.* 항목 ...

    # ── NotebookLM CLI (import name: nlm) ──
    'nlm',
    'nlm.__main__',
    'nlm.ai_docs',
    'nlm.cli',
    'nlm.cli.alias',
    'nlm.cli.auth',
    'nlm.cli.chat',
    'nlm.cli.config',
    'nlm.cli.main',
    'nlm.cli.notebook',
    'nlm.cli.repl',
    'nlm.cli.research',
    'nlm.cli.source',
    'nlm.cli.studio',
    'nlm.core',
    'nlm.core.alias',
    'nlm.core.auth',
    'nlm.core.auth_refresh',
    'nlm.core.client',
    'nlm.core.constants',
    'nlm.core.exceptions',
    'nlm.core.models',
    'nlm.output',
    'nlm.output.formatters',
    'nlm.utils',
    'nlm.utils.browser',
    'nlm.utils.cdp',
    'nlm.utils.config',

    # ── Typer/Rich 체인 (top-level) ──
    'typer',
    'rich',
    'shellingham',
    'websocket',          # websocket-client
    'annotated_doc',

    # ── 파일락 (BLOCK-A 해소) ──
    'filelock',

    # ── Tavily ──
    'tavily',
]
```

**PyInstaller collect-submodules 옵션 (WARN-2 / Fix-3 해소)**:

`build_exe.py`에서 PyInstaller 호출 시 `--collect-submodules typer rich` 옵션을 추가해 sub-modules 자동 수집:

```python
# build_exe.py
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--clean",
    "--noconfirm",
    "--collect-submodules", "typer",
    "--collect-submodules", "rich",
    "--collect-submodules", "nlm",   # 안전 장치 (hiddenimports와 중복 OK)
    SPEC_PATH,
]
```

이유: `typer`와 `rich`는 lazy import를 많이 쓰기 때문에 hiddenimports의 top-level 항목만으로는 `rich.console`, `rich.prompt`, `typer.main` 등이 누락될 수 있음. `--collect-submodules`는 패키지 내 **모든** `.py` 파일을 수집하므로 안전 장치가 된다.

#### 4.6.3 `build_exe.py` 사전 검증 단계

```python
# main() 안에
print("\n  의존성 사전 검증...")
for pkg in ("nlm", "tavily", "filelock"):
    try:
        __import__(pkg)
        print(f"    ✓ {pkg}")
    except ImportError:
        print(f"    ✗ {pkg} 미설치. pip install -r requirements.txt 먼저 실행.")
        sys.exit(1)
```

#### 4.6.4 `install-af.ps1` (Windows) 업데이트

v2와 동일:
- Chrome 감지 (레지스트리 기반)
- `__check-nlm` 검증
- 버전 1.2.18 → 1.2.19 bump

#### 4.6.5 `install-af.sh` (macOS/Linux, 신규)

v2와 동일 — 이미 전문 포함 완료. 단 **schema_version 2 마이그레이션 주석**만 추가:

```bash
# 기존 .af_setup_state.json이 schema_version 1이면 로드 시 자동 마이그레이션됨
# 별도 처리 불필요 (core/setup_wizard.py::_load_setup_state에서 처리)
```

### 4.7 `core/research_engine.py` 재작성 (BLOCK-C 하드코딩 제거)

**핵심 변경**: `DEFAULT_ARCHIVE_NOTEBOOK_ID` 상수 **제거**. 대신 `.af_setup_state.json`에서 로드.

```python
"""
core/research_engine.py — 사서(Librarian) 모듈 + NotebookLM 통합 엔진
v3: notebooklm_tools → nlm, 하드코딩 UUID 제거, state 기반 로드
"""
import sys, os, subprocess, json
from typing import Optional
from enum import Enum

class ResearchMode(Enum):
    FAST = "fast"
    DEEP = "deep"


def _get_archive_notebook_id() -> Optional[str]:
    """
    BLOCK-C 해소: state 파일에서 사용자별 archive_notebook_id를 로드.
    설정되어 있지 않으면 None → 호출자가 쿼리를 스킵하거나
    create 플로우를 재시도해야 함.
    """
    try:
        from core.setup_wizard import _load_setup_state
        state = _load_setup_state()
        return state.get("notebooklm", {}).get("archive_notebook_id")
    except Exception:
        return None


def _nlm_cmd_base() -> list[str]:
    """frozen vs 개발 환경에 따라 nlm 호출 prefix 반환."""
    if getattr(sys, "frozen", False):
        # PyInstaller frozen: af 자체의 __nlm 내부 서브커맨드 사용
        return [sys.executable, "__nlm"]
    return ["nlm"]


def _nlm_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _is_auth_error(text: str) -> bool:
    t = (text or "").lower()
    return any(f in t for f in (
        "authentication expired",
        "authentication failed",
        "profile not found",
        "not authenticated",
        "clientauthenticationerror",
    ))


def _nlm_cli(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    cmd = _nlm_cmd_base() + list(args)
    env = _nlm_env()
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", env=env, timeout=timeout)
    combined = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 or _is_auth_error(combined):
        print("[RESEARCH] 인증 만료 감지 → 자동 재인증 시도...")
        if _reauth_notebooklm():
            p = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", env=env, timeout=timeout)
    return p


def _reauth_notebooklm() -> bool:
    cmd = _nlm_cmd_base() + ["login"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", timeout=300)
        combined = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0 and not _is_auth_error(combined)
    except subprocess.TimeoutExpired:
        return False


def query_notebooklm(query: str, notebook_id: Optional[str] = None) -> str:
    """
    NotebookLM 노트북에 쿼리. notebook_id 미지정 시 state의 archive 사용.
    archive도 없으면 빈 문자열 반환 (graceful skip).
    """
    target_id = notebook_id or _get_archive_notebook_id()
    if not target_id:
        print("[RESEARCH] NotebookLM archive 노트북 미설정 → 쿼리 스킵", file=sys.stderr)
        return ""

    try:
        p = _nlm_cli("notebook", "query", target_id, query, timeout=180)
        if p.returncode != 0:
            print(f"[RESEARCH Error] NotebookLM query 실패: {(p.stderr or '').strip()}", file=sys.stderr)
            return ""
        return (p.stdout or "").strip()
    except Exception as e:
        print(f"[RESEARCH Error] NotebookLM 연결 실패: {e}", file=sys.stderr)
        return ""
```

### 4.8 `core/researcher.py` 수정

- `line 333`의 `find_spec("notebooklm_tools")` → `find_spec("nlm")` (**v2 표기 336은 오차, 실측 333**)
- TAVILY/NotebookLM 스킵 시 stderr에 1회 로그 (`_tavily_skip_logged`, `_notebook_skip_logged` 인스턴스 플래그)

### 4.9 `skills/research_assistant/skill.py` 수정

- `line 44, 65`의 `notebooklm_tools.cli.main` → `nlm` 호출 교체
- `_query_notebooklm()` 내부 `_nlm_cli` 기반 재정렬

---

## 5. 파일별 변경사항 (Fix-1 반영 — 테스트 20종)

| # | 파일 | 변경 유형 | 내용 |
|---|------|----------|------|
| 1 | `core/setup_wizard.py` | 확장 | `ensure_external_research_capabilities()`, `_ensure_tavily()`, `_ensure_notebooklm()`, `_load_setup_state()`, `_save_setup_state()` (filelock + atomic), `_check_chrome_installed()`, `_check_notebooklm_auth()`, `_run_notebooklm_login()`, `_find_or_create_archive_notebook()`, `_parse_notebook_list_for_title()`, `_parse_notebook_create_output()` 추가 |
| 2 | `core/setup_wizard.py` | 수정 | `check_and_hint()`는 deprecated 주석 + 새 진입점 호출로 래핑 |
| 3 | `run_factory_cli.py` | 수정 | `main()` 진입부에 `_run_setup_gate()` 추가 |
| 4 | `run_factory_cli.py` | 수정 | `_INTERNAL_SUBCOMMANDS_BEFORE_GATE` + STAGE 1 즉시 분기 |
| 5 | `run_factory_cli.py` | 추가 | `__nlm` 숨은 서브커맨드 + `_invoke_nlm_app()` (`standalone_mode=False` + sys.argv try/finally) |
| 6 | `run_factory_cli.py` | 추가 | `__check-nlm` 숨은 서브커맨드 |
| 7 | `core/researcher.py` | 수정 | `find_spec("notebooklm_tools")` → `find_spec("nlm")` (line 333) |
| 8 | `core/researcher.py` | 수정 | TAVILY/NotebookLM 스킵 시 stderr 1회 로그 + 인스턴스 플래그 |
| 9 | `core/research_engine.py` | **전면 재작성** | `notebooklm_tools.cli.main` → `nlm`, `_nlm_cmd_base()` frozen 분기, **`DEFAULT_ARCHIVE_NOTEBOOK_ID` 제거 → state 로드** |
| 10 | `skills/research_assistant/skill.py` | 수정 | `notebooklm_tools.cli.main` → `nlm`, `_query_notebooklm` 재구성 |
| 11 | `af.spec` | 수정 | `hiddenimports`에 `nlm.*` 27개 + typer/rich/tavily/**filelock** 추가 |
| 12 | `requirements.txt` | 수정 | `notebooklm-cli>=0.1.12,<0.2`, `tavily-python`, **`filelock>=3.0`** 추가 |
| 13 | `build_exe.py` | 수정 | PyInstaller 옵션에 `--collect-submodules typer rich nlm` + import 사전 검증 추가 |
| 14 | `install-af.ps1` | 수정 | 버전 bump + `__check-nlm` 검증 + Chrome 설치 확인 |
| 15 | `install-af.sh` | **신규** | macOS/Linux 동등 설치 스크립트 |
| 16 | `version.py` | 수정 | `__version__ = "1.2.19"` |
| 17 | `Master_Blueprint.md` | **신규 추가** | **§3.11 Setup Wizard** 서브섹션 신규 생성 — 본 feature 머지 시점에 추가됨. 기존 Blueprint는 §3.1~§3.10 + §3.8.1~§3.8.3만 존재하며 §3.11은 현재 **부재**. 이번 PR이 섹션을 **최초로 생성**하는 것임을 명시 |
| 18 | `Master_Blueprint.md` | 수정 | §0 빠른 참조 테이블 갱신 |
| 19 | `Master_Blueprint.md` | 수정 | §8 (빌드/배포)에 install-af.sh 추가 |
| 20 | `Master_Blueprint.md` | 수정 | §10 (Blast Radius) 반영 |
| 21 | `Master_Blueprint.md` | 수정 | §12 변경 이력 2026-04-10/11 항목 추가 |
| 22 | `docs/2026-04-03-session-handoff.md` | 수정 | 172행 `notebooklm-tools` → `notebooklm-cli`, "미완료" → "완료" |
| 23 | `tests/test_setup_wizard_gate.py` | 신규 | `§8.1` 단위 테스트 **20종** |

---

## 6. UX 시나리오

### 6.1 첫 실행, 전부 승인 (v3: 노트북 생성 포함)

```
$ af --fsa
[Auto-Config] CLI 프로바이더 자동 감지: claude_cli, codex_cli
[Setup] 외부 리서치 도구 점검 중...

┌──────────────────────────────┐
│  ⚠  TAVILY_API_KEY 미설정   │
└──────────────────────────────┘
TAVILY_API_KEY 입력 (엔터=스킵): tvly-abc...
  ✓ 저장 완료 → .env

[Setup] Chrome 감지됨: /Applications/Google Chrome.app
┌──────────────────────────────┐
│  ⚠  NotebookLM 로그인 필요  │
└──────────────────────────────┘
지금 브라우저를 열어 로그인하시겠습니까? [Y/n]: [엔터]
  브라우저 로그인 중 (최대 5분)...
  ✓ 로그인 완료

[Setup] 아카이브 노트북 확인 중...
  $ nlm notebook list
  (기존 "Agent Factory Archive" 없음)
  $ nlm notebook create "Agent Factory Archive"
  ✓ 노트북 생성: eaa34a54-a898-...
  → state 저장

[Setup] ✓ TAVILY + NotebookLM + Archive(eaa34a54...) 활성화
[Chat] 시작 중...
```

### 6.2 TAVILY 스킵 재확인 루프

```
TAVILY_API_KEY 입력 (엔터=스킵): [엔터]
┌──────────────────────────────┐
│  ⚠  재확인                  │
└──────────────────────────────┘
진행하시겠습니까? [y/N]: N
TAVILY_API_KEY 입력 (엔터=스킵): tvly-xyz...
  ✓ 저장 완료
```

### 6.3 노트북 생성 실패 → 사용자 UUID 입력 (BLOCK-C 폴백)

```
[Setup] 아카이브 노트북 확인 중...
  $ nlm notebook create "Agent Factory Archive"
  ✗ 생성 실패: rate limit exceeded

┌──────────────────────────────────────────┐
│  ⚠  아카이브 노트북 확보 실패             │
│                                          │
│  [1] 기존 노트북 UUID 직접 입력          │
│  [2] 지금 스킵 (다음 실행 시 재시도)      │
│  [3] NotebookLM 없이 진행                │
└──────────────────────────────────────────┘
선택 [1/2/3]: 1
기존 노트북 UUID: {사용자가 본인 노트북 UUID 입력}
  $ nlm notebook get {uuid}
  ✓ 노트북 확인됨
  → state 저장
```

### 6.4 Chrome 미설치 → 수동 쿠키 (변경 없음)

```
[Setup] ⚠ Chrome 미감지
[1] Chrome 설치 후 재시도
[2] 수동 쿠키 파일 경로 입력
[3] NotebookLM 없이 진행
선택 [1/2/3]: 2
쿠키 파일 경로: /Users/hoon/nlm-cookies.txt
  $ nlm login --manual -f /Users/hoon/nlm-cookies.txt --profile default
  ✓ 로그인 완료
[Setup] 아카이브 노트북 확인 중... (이어서)
```

### 6.5 재실행, 상태 파일 있음

```
$ af --fsa
[Setup] ✓ TAVILY 설정됨, NotebookLM logged_in (archive: eaa34a54...)
[Chat] 시작 중...
```

### 6.6 CI / `AGENT_SKIP_SETUP_HINT=1` (기존 변수)

```
$ AGENT_SKIP_SETUP_HINT=1 af --fsa -t "..."
[Chat] 시작 중...   # setup gate 완전 침묵
```

### 6.7 비TTY (pipe)

```
$ echo "..." | af --fsa
[Setup] TTY 없음 → 비대화형 모드, TAVILY/NotebookLM 스킵
[Chat] 시작 중...
```

### 6.8 frozen 환경 nlm 호출

```
$ dist/af/af __nlm auth status
✗ Not authenticated
  Profile not found: default
  (af.main() → STAGE 1 → _invoke_nlm_app(["auth","status"])
   → nlm.cli.main.app(["auth","status"], standalone_mode=False))
```

---

## 7. 엣지 케이스

### 7.1 stdin 리다이렉트 (`af --fsa < input.txt`)
변경 없음 — mode=noninteractive, 프롬프트 생략.

### 7.2 `af setup` 재귀 방지
변경 없음 — STAGE 1 즉시 분기.

### 7.3 `af __nlm` 재귀 방지 + SystemExit 차단 (BLOCK-B 해소)

- **재귀 방지**: STAGE 1에서 즉시 분기 → `_run_setup_gate()` 호출되지 않음 → `_check_notebooklm_auth()`가 frozen 환경에서 `[af, __nlm, auth, status]`를 subprocess로 호출해도 안전.
- **SystemExit 차단 — 실제 방어벽은 `try/except SystemExit`**:
  - `standalone_mode=False`는 **SystemExit을 차단하는 옵션이 아니다**. Click/Typer에서 이 플래그는 Click 레이어가 직접 관리하는 종료 경로(예: `--help` 출력, 인자 파싱 오류)에서 `sys.exit()`을 우회하고 **반환값을 돌려주게** 만드는 것이 본래 목적이다. 즉 "성공 경로의 종료 코드 처리"를 정상화하는 역할.
  - `nlm` 내부 서브커맨드 구현체가 **직접 `sys.exit()`을 호출**하면 Click 레이어를 우회하므로 `standalone_mode=False`가 이를 잡지 못한다.
  - 따라서 실제 SystemExit을 막는 **유일한 방어벽은 `_invoke_nlm_app()` 안의 `try/except SystemExit as e:` 블록**이다. 이것이 부모 프로세스를 보호한다.
- **두 레이어의 역할 정리**:
  - `standalone_mode=False` → **반환값 처리** (Click 성공 경로의 정상 반환). 없으면 `--help` 같은 정상 종료도 `SystemExit`이 되어 복잡해짐.
  - `try/except SystemExit` → **실제 SystemExit 차단**. 이게 "중복 방어처럼 보인다고" 제거되면 서브커맨드의 직접 `sys.exit()`이 `run_factory_cli.main()`을 죽인다. **제거 금지**.
- **부가 효과**:
  - (a) `run_factory_cli.main()`이 정상 `return`으로 종료
  - (b) `sys.argv` try/finally 복원으로 전역 오염 없음 (WARN-1 해소)
  - (c) subprocess 경계가 없어도 직접 호출 안전 (향후 코드 변경에도 robust)

**⚠ 코드 주석 의무**: `_invoke_nlm_app()` 구현 시 `except SystemExit` 블록 위에 다음 주석을 반드시 달아야 한다:
```python
# ⚠ DO NOT REMOVE — nlm 내부 서브커맨드가 직접 sys.exit()을 호출할 수 있다.
# standalone_mode=False는 Click 성공 경로의 반환값 처리 목적이며,
# SystemExit을 잡는 유일한 벽은 이 except 블록이다.
```

**subprocess 경계 + in-process 이중 안전 장치 관계**:
- `_check_notebooklm_auth()`는 frozen 환경에서도 `[sys.executable, "__nlm", "auth", "status"]`를 **subprocess**로 호출하므로, 설령 `except SystemExit`이 없어도 자식 프로세스 격리로 부모는 안전하다 (프로세스 단위 격리).
- `_invoke_nlm_app()` 자체는 **in-process 직접 호출** 경로이므로, 여기서는 `except SystemExit`이 필수.
- 즉 현재 설계에서 subprocess 경계는 "외부 호출자 측의 격리"이고, `except SystemExit`은 "내부 호출 진입점 측의 격리"이며, **서로 다른 레이어의 독립 보호 장치**이다.

### 7.4 `.af_setup_state.json` 손상

- JSON 파싱 실패 → 기본값 복구
- 스키마 실패(`schema_version != 2`, decision 필드 누락/잘못된 enum) → 기본값 복구
- schema_version 1 → 2 자동 마이그레이션 (archive_notebook_id 필드 추가)

### 7.5 동시 실행 경쟁 (BLOCK-A 해소)

`filelock` 라이브러리는 POSIX(`fcntl.flock`)와 Windows(`msvcrt.locking`)를 자동 선택. 동일한 `.af_setup_state.json.lock` 파일에 `FileLock(...)` 컨텍스트를 걸면 두 프로세스가 순차적으로 진입. 10초 타임아웃 시 경고 후 스킵 (파이프라인 블록 금지).

### 7.6 frozen 환경 `sys.executable` (v2 R4 해소 + BLOCK-B)
- `__nlm` 분기에서 Typer `app(rest, standalone_mode=False)` 직접 호출
- `sys.argv` try/finally 백업/복원

### 7.7 TAVILY 빈 문자열
변경 없음 — `os.getenv()` falsy로 처리.

### 7.8 `nlm auth status` exit code — v3 관찰 오류 정정 (Phase 0.5 재실측)

**v3 서술 오류**: "exit code 항상 0, 반드시 stdout 파싱 의무"는 제가 Phase 0에서 범한 관찰 오류에 기반한 잘못된 서술이었습니다. 원인은 `... 2>&1 | head -20; echo "exit: $?"` 형태 파이프라인의 마지막 명령 exit code가 `head`의 exit(항상 0)를 보여준 것. 소스 `nlm/cli/auth.py:59`를 읽고 `.venv/bin/nlm auth status; echo $?`로 재실측한 결과 **실패 시 exit code 2** 확인.

**Phase 0.5 확정**:
- **성공**: exit code **0** + stdout `✓ Authenticated` + `Notebooks accessible: N`
- **실패**: exit code **2** + stdout `✗ Not authenticated` / `Profile not found`
- 다른 exit code: `unknown` (네트워크 장애, 패키지 파손 가능성)

**구현 지침** (§4.4 코드 스니펫 참조):
- 1차 판정: `p.returncode` (0=성공, 2=실패, 그 외=unknown)
- 2차 크로스체크: stdout 문자열 패턴 (nlm 버전 변경 방어)
- R5 회귀 모니터링: §8.2 M7 + Slow Integration Test에서 두 경우의 exit code + stdout를 모두 assert

### 7.9 내부 서브커맨드 prefix 컨벤션
- `__` 접두사 — `__nlm`, `__check-nlm`
- 향후 확장 시 동일 규칙. 규칙은 `Master_Blueprint §3.11`에 기록.

### 7.10 `notebooklm-cli` 버전 핀 파손
- 버전 범위 `>=0.1.12,<0.2`
- 0.1.x semver 미보장 → 0.1.13 출시 시 파손 가능
- 완화: §8.2 Slow Integration Test가 실제 `nlm` 바이너리 호출을 주기적으로 검증

### 7.11 `_find_or_create_archive_notebook()` 실패 케이스 (Phase 0.5 반영)

| 실패 원인 | 반환 `reason` | 사용자 UX |
|----------|--------------|-----------|
| `notebook list` 타임아웃 | (로그만, list 없이 create 시도) | 계속 |
| `notebook list` JSON 파싱 실패 (극히 드묾) | (조용히 create로 진행) | **완화책 아래 참조** — Phase 0.5 이전보다 위험도 크게 낮음 |
| `notebook create` 실패 (rate limit 등) | `"create_failed: ..."` | §6.3 폴백 박스 |
| `notebook create` 성공 but UUID regex 매치 실패 | `"created_but_parse_failed"` | §6.3 폴백 박스 |
| 타임아웃 | `"create_timeout"` | §6.3 폴백 박스 |

**중복 노트북 생성 위험도 평가 (Phase 0.5 이후)**:

Phase 0.5에서 `nlm notebook list` 출력이 **순수 JSON 배열**임이 확인되어, v3에서 우려했던 "표 포맷 파싱 실패" 경로가 제거됐습니다. `json.loads()`가 실패할 경우는 사실상:
1. `nlm`이 stderr에 에러 메시지 출력하고 stdout을 완전히 비움 (rate limit, 네트워크 장애)
2. `nlm` 업그레이드로 출력 포맷이 JSON이 아닌 다른 것으로 변경 (semver violation)

둘 다 **매우 드문 경우**이지만, 발생 시 조용한 중복 생성을 막기 위해 다음 완화책을 구현에 포함한다:

1. `p.returncode == 0`이지만 `_parse_notebook_list_for_title()` 결과가 `None` AND stdout이 비어있지 않음 → "파싱 실패" 케이스 감지
2. 이 경우 create **직전에** 사용자에게 경고 + 원본 stdout 1회 표시:
   ```
   [Setup] ⚠ nlm notebook list JSON 파싱 실패 — 원본 출력 확인 요청
   ---begin stdout---
   {raw stdout snippet ≤ 500 chars}
   ---end stdout---
   중복 생성을 방지하기 위해 계속할지 확인합니다.
   계속 생성하시겠습니까? [Y/n/u=UUID 직접 입력]:
   ```
3. `u` 선택 시 §6.3 [1] 수동 UUID 입력으로 전환
4. 기본 동작(`Y`)이 create 진행해도 생성 직후 `state.notebooklm.archive_possibly_duplicate = true` 플래그 저장 → 다음 실행에서 자동 재탐지 시도

### 7.12 사용자가 기존 노트북 UUID 수동 입력 시 유효성
- `_find_or_create_archive_notebook()`의 [1] 폴백에서 사용자가 입력한 UUID를 `nlm notebook get <id>`로 검증
- 응답이 에러(403/404)면 재입력 요청 (최대 3회)
- 3회 실패 → `decision=logged_in, archive_notebook_id=None` 상태로 저장 후 진행

---

## 8. 테스트 계획 (WARN-3 + Fix-1 반영 — 20종)

### 8.1 단위 테스트 (`tests/test_setup_wizard_gate.py` 신규, 20종)

1. `test_ensure_tavily_configured_no_prompt`
2. `test_ensure_tavily_interactive_input_saves_env`
3. `test_ensure_tavily_skip_reconfirm_yes`
4. `test_ensure_tavily_skip_reconfirm_no_loop`
5. `test_ensure_tavily_noninteractive_mode`
6. `test_ensure_notebooklm_module_missing_in_source_mode`
7. `test_ensure_notebooklm_chrome_missing_branch`
8. `test_ensure_notebooklm_auth_status_parsing_not_authenticated`
9. `test_ensure_notebooklm_auth_status_parsing_success`
10. `test_ensure_notebooklm_login_subprocess_mock_success`
11. `test_ensure_notebooklm_login_failure_retry_then_skip`
12. `test_setup_state_atomic_write_crash_simulation`
13. `test_setup_state_schema_v1_to_v2_migration`     ← **v3 신규**
14. `test_setup_state_schema_corrupted_recovery`
15. `test_setup_state_filelock_contention`          ← **v3 변경 (fcntl → filelock)**
16. `test_setup_gate_skips_setup_subcommand`
17. `test_setup_gate_skips_nlm_internal_subcommand`
18. `test_setup_gate_skips_worker_subcommand`
19. `test_invoke_nlm_app_standalone_mode_false`     ← **v3 신규** (SystemExit 차단 + sys.argv 복원)
20. `test_find_or_create_archive_notebook_parses_uuid`  ← **v3 신규** (`_parse_notebook_create_output` regex)

### 8.2 통합/수동 테스트

**수동 스모크 (v3 신규 M8, M9 추가)**:
- **M1**. 비TTY 모드 → 경고만, 파이프라인 정상 진행
- **M2**. TTY `af --fsa` → TAVILY + NotebookLM 전체 플로우 (승인 경로)
- **M3**. 재실행 → 프롬프트 0회
- **M4**. `af setup` → 강제 재설정
- **M5**. `AGENT_SKIP_SETUP_HINT=1 af --fsa` → 완전 침묵
- **M6**. Chrome 미설치 상태 → 3지 메뉴
- **M7**. `.venv/bin/nlm auth status` 출력이 Phase 0 실측과 동일
- **M8**. **(v3 신규)** 첫 실행 시 `nlm notebook create "Agent Factory Archive"` 실제 실행 → state 저장 확인
- **M9**. **(v3 신규)** 기존 노트북 재사용 시나리오: 같은 환경에서 두 번째 실행 시 `nlm notebook list`로 기존 아카이브 발견 → create 안 하고 재사용

**Slow Integration Test (WARN-3 해소)** — `@pytest.mark.slow` 마킹, CI 주기 실행:

```python
# tests/test_nlm_regression.py
@pytest.mark.slow
def test_nlm_auth_status_output_format():
    """실제 nlm 바이너리를 호출해 stdout 포맷 회귀 검증.
    nlm 버전 업그레이드 시 출력이 바뀌면 이 테스트가 감지."""
    result = subprocess.run(
        ["nlm", "auth", "status", "--profile", "regression_test_profile"],
        capture_output=True, text=True, timeout=15
    )
    combined = result.stdout + result.stderr
    # Phase 0 실측 패턴 — 이 중 하나는 반드시 있어야 함
    assert any(p in combined for p in [
        "✗ Not authenticated",
        "Profile not found",
        "Authentication failed",
    ]), f"nlm auth status 출력 포맷 변경 감지: {combined!r}"

@pytest.mark.slow
def test_nlm_notebook_help_subcommands_exist():
    """nlm notebook 서브커맨드 목록 회귀 검증."""
    result = subprocess.run(
        ["nlm", "notebook", "--help"],
        capture_output=True, text=True, timeout=10
    )
    for sub in ("list", "create", "get", "query"):
        assert sub in result.stdout, f"nlm notebook {sub} 사라짐 — breaking change"
```

CI 설정에서 `pytest -m slow --tb=short` 를 일일 주기 또는 PR 병합 전 게이트로 실행.

### 8.3 PyInstaller 빌드 검증

- **B1**. `python build_exe.py` 성공
- **B2**. bundle 크기 측정 (+20~50MB 예상, +100MB 초과 시 위험)
- **B3**. `dist/af/af --version`
- **B4**. `dist/af/af __check-nlm` → exit 0
- **B5**. `dist/af/af __nlm auth status` → Phase 0 실측과 동일 출력
- **B6**. `dist/af/af --fsa < input.txt` → 비TTY 플로우 정상
- **B7**. `dist/af/af setup` → 인터랙티브 마법사 동작
- **B8**. **(v3 신규)** `dist/af/af __nlm notebook list` (미인증 상태) → "Profile not found" 출력, SystemExit이 bundle 프로세스를 죽이지 않음

### 8.4 설치 스크립트 검증

- **I1**. Windows: `install-af.ps1` 실행 → 구버전 제거 → 다운로드 → PATH 등록 → Chrome 확인
- **I2**. macOS: `bash install-af.sh` 실행 → symlink → Chrome 확인
- **I3**. Linux VM: `bash install-af.sh` 실행 (선택)

### 8.5 회귀 테스트

- `af setup` 기존 동작 불변
- `check_and_hint()` 기존 동작 불변 (deprecation 주석만)
- 전체 `pytest` suite 통과

---

## 9. 롤아웃 및 호환성

### 9.1 마이그레이션

- **기존 사용자**: `.af_setup_state.json` 없음 → `schema_version=2` 기본값 → 첫 실행 프롬프트
- **schema_version 1 사용자**: 자동 마이그레이션(`archive_notebook_id=None` 추가)
- **기존 `.env`의 TAVILY_API_KEY**: 자동 인식

### 9.2 버전 bump

- `version.py`: 1.2.18 → **1.2.19**
- `install-af.ps1`, `install-af.sh` 버전 문자열 동기화
- `dist/af-1.2.19.zip`, 태그 `af-fsa_v1.2.19`

### 9.3 Rollback 계획

- `_run_setup_gate()` 주석 처리 → 기존 동작 복귀
- `af.spec`의 `nlm.*` / `filelock` 제거 → bundle 원상 복구
- `.af_setup_state.json` 삭제 → 상태 초기화
- `research_engine.py`는 재작성이므로 git revert 수준 롤백만 가능

---

## 10. 리스크

### 10.1 해소된 리스크 (v1/v2/v3)

- ✅ **R1** (`notebooklm-tools` PyPI 존재): 해소 — 실제 `notebooklm-cli`
- ✅ **R2** (Playwright 의존): 해소 — CDP 사용
- ✅ **R3** (`_check_notebooklm_auth` 구현): 해소 — **exit code 0/2 구분 + stdout 크로스체크** (Phase 0.5 재실측)
- ✅ **R4** (frozen `sys.executable` 재귀): 해소 — `__nlm` + `app(rest, standalone_mode=False)`
- ✅ **v2 BLOCK-A** (Windows fcntl): 해소 — `filelock` 크로스플랫폼
- ✅ **v2 BLOCK-B** (Typer standalone_mode): 해소 — try/except SystemExit (실제 방어벽) + `standalone_mode=False` (반환값 처리) 이중 설명
- ✅ **v2 BLOCK-C** (하드코딩 UUID): 해소 — `_find_or_create_archive_notebook()` + state 저장 + Phase 0.5 실측으로 파서 확정
- ✅ **v3 U5** (`notebook create/list` 출력 포맷 미검증): **Phase 0.5 실측 완료** — create는 `  ID: <uuid>` regex, list는 JSON 배열 `json.loads()`
- ✅ **v3 R10** (`notebook create` 출력 파싱): Phase 0.5 실측으로 `_CREATE_ID_RE` 확정

### 10.2 잔존 리스크

- **R5 (중위)**. `nlm auth status` 출력 포맷 회귀 → §8.2 Slow Integration Test가 CI에서 감지. Phase 0.5 baseline 스냅샷(exit code 0/2, `✓ Authenticated` + `Notebooks accessible: N` vs `✗ Not authenticated` + `Profile not found`)을 테스트 assert로 고정
- **R6 (중위)**. Chrome 브라우저 필수 → `--manual` 쿠키 파일 폴백 공식 제공
- **R7 (저위)**. `sys.argv` 오염 → `_invoke_nlm_app()` try/finally 백업/복원 명시
- **R8 (저위)**. `install-af.sh` curl/wget 미설치 → 명시 에러 메시지
- **R9 (저위)**. `filelock` 10초 타임아웃 시 상태 저장 실패 → 경고 후 파이프라인 진행 (블록 금지)
- **R11 (저위, v3.2 신규)**. `nlm notebook list`가 JSON 이외 포맷으로 파손되는 미래 버전 업그레이드 → R5와 동일 메커니즘(Slow Integration Test)으로 감지. 파손 감지 시 §7.11 중복 생성 완화책 자동 발동

### 10.3 미결정 (구현 단계에서 결정)

- **U2**. NotebookLM 로그인 로그 출력 경로 → 구현 시 결정
- (**U5 제거** — Phase 0.5 실측으로 완전 해소)

---

## 11. 작업 순서 (v3)

**Phase 0 — 검증 (완료, 2026-04-10)**
- ✅ `pip install notebooklm-cli` 성공
- ✅ import 이름 `nlm`, Typer 기반 확인
- ✅ 27개 서브모듈 확보
- ✅ Playwright 비의존
- ⚠ `nlm auth status` exit code "0" 관찰 — **Phase 0.5에서 관찰 오류로 정정 (실제는 실패 시 2)**
- ✅ `nlm notebook {list,create,get,query,delete}` 서브커맨드 확인
- ✅ `nlm login [--manual -f]` 실측

**Phase 0.5 — 실측 완료 (2026-04-11)**
- ✅ `.venv/bin/nlm login` 수행 → `✓ Successfully authenticated!` + `Profile: default` + `Cookies: 25 extracted` + `CSRF Token: Yes` + `Credentials saved to: <path>` 확인
- ✅ `.venv/bin/nlm auth status` (로그인 후) → exit **0** + `Validating credentials for profile: default...` + `✓ Authenticated` + `Notebooks accessible: 33` 확인
- ✅ `.venv/bin/nlm auth status` (미인증 재현) → exit **2** + `✗ Not authenticated` + `Profile not found: default` 재확인 (v3의 "exit 0" 관찰은 파이프라인 `$?` 오류였음을 확증)
- ✅ `.venv/bin/nlm notebook create "AF Phase 0.5 Tet"` → `✓ Created notebook: <title>` + `  ID: 03662da6-f29e-43aa-b403-79f41b728cf4` 포맷 확인 → `_CREATE_ID_RE` regex 확정
- ✅ `.venv/bin/nlm notebook list` → **순수 JSON 배열** 포맷 확인, 각 객체 `{id, title, source_count, updated_at}` → `_parse_notebook_list_for_title()`를 `json.loads()` 기반으로 확정
- ✅ **부수 발견**: v2 BLOCK-C에서 "Himari 개인 UUID"로 지칭한 `eaa34a54-a898-46a0-835a-cdb6024887f0`가 실제로는 원 저자(hoon) 본인 NotebookLM 계정 소유 노트북 `"Google Antigravity: Comprehensive Guide..."`임을 실측 확인. 원 저자에게는 우연히 작동했으나 신규 사용자는 여전히 접근 불가 → BLOCK-C 해결책 (자동 생성 + state 저장) 유효성 재확인

**Phase 1 — Core setup_wizard**
1. `_load_setup_state()` / `_save_setup_state()` (filelock + atomic + 스키마 v2)
2. `_check_chrome_installed()` OS별
3. `_check_notebooklm_auth()` stdout 파싱
4. `_run_notebooklm_login()` subprocess
5. `_find_or_create_archive_notebook()` + `_parse_*`
6. `_ensure_tavily()`, `_ensure_notebooklm()`
7. `ensure_external_research_capabilities()` 공개 API
8. 단위 테스트 §8.1 20종 작성

**Phase 2 — run_factory_cli**
1. `_INTERNAL_SUBCOMMANDS_BEFORE_GATE` + STAGE 1 분기
2. `_invoke_nlm_app()` (standalone_mode=False + sys.argv try/finally)
3. `__nlm` / `__check-nlm` 숨은 서브커맨드
4. `_run_setup_gate()` STAGE 2 호출
5. 테스트 §8.1-16~19

**Phase 3 — 데드코드 복구**
1. `research_engine.py` 전면 재작성 (하드코딩 UUID 제거, `_get_archive_notebook_id()` state 로드)
2. `researcher.py:333` 수정
3. `skills/research_assistant/skill.py:44,65` 수정

**Phase 4 — 배포 빌드**
1. `requirements.txt`에 `notebooklm-cli`, `tavily-python`, `filelock` 추가
2. `af.spec` hiddenimports 27+5개 + filelock
3. `build_exe.py` `--collect-submodules typer rich nlm` + 사전 import 검증
4. `install-af.ps1` Chrome 체크 + `__check-nlm` + 버전 bump
5. `install-af.sh` 신규 작성
6. `version.py` 1.2.18 → 1.2.19
7. 빌드 §8.3 B1~B8 검증

**Phase 5 — 스모크**
1. §8.2 M1~M9 수행
2. §8.2 Slow Integration Test 실행
3. §8.4 I2 macOS install-af.sh 검증

**Phase 6 — 문서 동기화 (코드와 같은 커밋)**
1. `Master_Blueprint.md` §3.11 신규 생성
2. §0 / §8 / §10 / §12 갱신
3. `docs/2026-04-03-session-handoff.md:172` 완료 체크
4. 이 설계 문서 상태: Draft → Implemented

**Phase 7 — 교차검증 재실행**
1. af-critic v3 BLOCK 0건 확인
2. af-doc-qa v3 FAIL 0건 확인
3. (선택) af-cross-review Codex 교차검증

**Phase 8 — 커밋 + 태깅**
- 코드 + Blueprint 동일 커밋
- `git tag af-fsa_v1.2.19`

---

## 12. 승인 체크리스트

- [x] **Phase 0 완료** — `notebooklm-cli` + `nlm notebook` 서브커맨드 트리 검증
- [x] **Q1 = A (Bundle)** / **Q2 = Y/N 재확인** / **Q3 = Medium** 반영
- [x] **BLOCK #2 (v1)** — STAGE 1/2/3 구조 (§4.5)
- [x] **BLOCK #3 (v1)** — atomic write + filelock (§4.1)
- [x] **FAIL B3 (v1)** — Blueprint §3.11 신규 생성 (§5 row 17)
- [x] **WARN #4 (v1)** — Medium 강도 사용자 합의 (§1.3, §2 G3)
- [x] **WARN A4 (v1)** — §5 표 행 분할
- [x] **BLOCK-A (v2)** — `filelock` 패키지 크로스플랫폼 해소 (§4.1, §4.6.1)
- [x] **BLOCK-B (v2)** — `standalone_mode=False` + sys.argv try/finally (§4.5, §7.3)
- [x] **BLOCK-C (v2)** — `_find_or_create_archive_notebook()` + state 저장 (§4.1, §4.4-C, §4.7)
- [x] **WARN-1 (v2)** — sys.argv 백업/복원 명시 (§4.5, §7.3)
- [x] **WARN-2 / Fix-3 (v2)** — `--collect-submodules typer rich` (§4.6.2)
- [x] **WARN-3 (v2)** — `@pytest.mark.slow` 통합 테스트 (§8.2)
- [x] **Fix-1 (v2)** — `§5` row 23 "20종" 반영
- [x] **Fix-2 (v2)** — 환경변수 기존/신규 구분 각주 (§2 G6)
- [x] **Fix-4 (v2)** — atomic write 주석 보강 (§4.1)
- [x] **Fix-5 (v2)** — `researcher.py` 라인 336→333 정정 (§3.2)
- [ ] **Phase 0.5 실측** — 구현 착수 직후 `nlm login` + `notebook create` 출력 포맷 (U5)
- [ ] **재교차검증 v3** — af-critic / af-doc-qa BLOCK/FAIL 0건 확인

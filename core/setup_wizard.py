"""
af setup — API 키 / NotebookLM 등록 마법사 + 외부 리서치 도구 점검 게이트.

역사:
  v1 (최초): _KEYS 리스트 기반 대화형 마법사 (TAVILY, GOOGLE, ANTHROPIC, OPENAI)
  v2 (2026-04-11): ensure_external_research_capabilities() 추가
                   - 모든 실행 모드에서 호출되는 단일 진입점
                   - .af_setup_state.json 영속 상태 (schema v2)
                   - TAVILY 입력 UI + Y/N 재확인 루프
                   - NotebookLM Medium 강도 로그인 유도 + 자동 아카이브 노트북 관리
                   - Chrome DevTools Protocol 감지 + 수동 쿠키 폴백
  설계 문서: docs/features/2026-04-10-setup-wizard-tavily-notebooklm-integration.md (v3.3)

주의:
  **core.* 모듈을 절대 top-level로 import하지 말 것.** research_engine 등 downstream
  모듈이 `_get_archive_notebook_id()` 내부에서 본 모듈의 `_load_setup_state()`를
  lazy import로 호출하기 때문에, setup_wizard가 core.* 모듈을 top-level import하면
  즉시 순환 발생. 필요한 core 유틸은 함수 내부에서만 import 할 것.
  (af-cross-review Q1: 현재 top-level은 stdlib + filelock만 허용)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from filelock import FileLock, Timeout  # type: ignore
    _HAS_FILELOCK = True
except ImportError:
    _HAS_FILELOCK = False


# ═══════════════════════════════════════════════════════════════════════════
# 1. 기존 v1 마법사 유지 (하위호환)
# ═══════════════════════════════════════════════════════════════════════════

_KEYS = [
    {
        "name": "Tavily (웹 검색)",
        "env": "TAVILY_API_KEY",
        "url": "https://app.tavily.com",
        "required": False,
        "desc": "프로젝트 리서치 품질을 높이는 웹 검색 API",
    },
    {
        "name": "Google (Gemini CLI)",
        "env": "GOOGLE_API_KEY",
        "url": "https://aistudio.google.com/apikey",
        "required": False,
        "desc": "Gemini CLI 제공자 사용 시 필요",
    },
    {
        "name": "Anthropic (Claude API)",
        "env": "ANTHROPIC_API_KEY",
        "url": "https://console.anthropic.com",
        "required": False,
        "desc": "Claude API 직접 호출 시 필요 (CLI 모드에서는 불필요)",
    },
    {
        "name": "OpenAI (Codex CLI)",
        "env": "OPENAI_API_KEY",
        "url": "https://platform.openai.com/api-keys",
        "required": False,
        "desc": "Codex CLI 제공자 사용 시 필요",
    },
]


def _get_env_path() -> str:
    """exe 옆 또는 소스 루트의 .env 경로."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), ".env")
    factory_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(factory_dir, ".env")


def _load_existing(env_path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if not os.path.isfile(env_path):
        return result
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, v = raw.split("=", 1)
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def _save_env(env_path: str, data: dict[str, str]) -> None:
    lines: list[str] = []
    existing_keys: set[str] = set()

    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                raw = line.rstrip("\n")
                if "=" in raw and not raw.startswith("#"):
                    k = raw.split("=", 1)[0].strip()
                    if k in data:
                        lines.append(f"{k}={data[k]}")
                        existing_keys.add(k)
                        continue
                lines.append(raw)

    for k, v in data.items():
        if k not in existing_keys and v:
            lines.append(f"{k}={v}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run_setup(interactive: bool = True) -> None:
    """API 키 등록 마법사 실행 (`af setup` 서브커맨드)."""
    env_path = _get_env_path()
    existing = _load_existing(env_path)

    print()
    print("=" * 60)
    print("  Agent Factory — API 키 설정")
    print("=" * 60)
    print(f"  저장 위치: {env_path}")
    print()

    updated: dict[str, str] = {}
    changed = False

    for key_info in _KEYS:
        env_key = key_info["env"]
        current = existing.get(env_key) or os.getenv(env_key, "")
        masked = f"{current[:8]}..." if len(current) > 8 else ("(미설정)" if not current else current)

        print(f"▶ {key_info['name']}")
        print(f"  {key_info['desc']}")
        print(f"  발급: {key_info['url']}")
        print(f"  현재: {masked}")

        if not interactive:
            print()
            continue

        prompt = "  새 값 입력 (엔터=유지, s=건너뛰기): "
        try:
            val = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n설정 중단.")
            break

        if val.lower() == "s" or val == "":
            updated[env_key] = current
        else:
            updated[env_key] = val
            changed = True
            print(f"  ✓ {env_key} 저장됨")
        print()

    if changed:
        _save_env(env_path, updated)
        print(f"✓ .env 저장 완료: {env_path}")
        print("  변경사항은 af 재시작 후 적용됩니다.")
    else:
        print("변경사항 없음.")

    print()


def check_and_hint() -> None:
    """
    [DEPRECATED in v3] — `ensure_external_research_capabilities()`로 이전.
    하위호환을 위해 유지. 내부적으로 새 진입점을 호출.
    """
    if os.getenv("AGENT_SKIP_SETUP_HINT"):
        return
    try:
        ensure_external_research_capabilities(mode="auto")
    except Exception as e:
        print(f"[Setup] Warning: check_and_hint fallback failed: {e}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# 2. v2 신규 — 외부 리서치 도구 점검 게이트
# ═══════════════════════════════════════════════════════════════════════════

_STATE_SCHEMA_VERSION = 2
_ARCHIVE_NOTEBOOK_TITLE = "Agent Factory Archive"

_VALID_TAVILY_DECISIONS = {"pending", "configured", "skipped"}
_VALID_NOTEBOOKLM_DECISIONS = {
    "pending", "logged_in", "skipped", "login_failed", "chrome_missing",
}


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": _STATE_SCHEMA_VERSION,
        "tavily": {
            "decision": "pending",
            "last_prompt_at": None,
        },
        "notebooklm": {
            "decision": "pending",
            "profile": "default",
            "archive_notebook_id": None,
            "archive_notebook_title": _ARCHIVE_NOTEBOOK_TITLE,
            "archive_possibly_duplicate": False,
            "last_login_attempt_at": None,
            "last_login_error": None,
        },
    }


def _get_setup_state_path() -> str:
    """`.env`와 같은 디렉토리에 `.af_setup_state.json`."""
    env_path = _get_env_path()
    return os.path.join(os.path.dirname(env_path), ".af_setup_state.json")


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_setup_state() -> dict[str, Any]:
    """
    상태 파일 로드 + 스키마 v2 검증 + v1→v2 마이그레이션.
    깨진 파일/스키마는 기본값으로 복구.
    """
    path = _get_setup_state_path()
    if not os.path.isfile(path):
        return _default_state()

    lock_path = path + ".lock"
    try:
        if _HAS_FILELOCK:
            with FileLock(lock_path, timeout=5):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_state()
    except Exception:
        # filelock.Timeout 포함 모든 예외 → 기본값
        return _default_state()

    if not isinstance(data, dict):
        return _default_state()

    # schema_version 1 → 2 마이그레이션
    if data.get("schema_version") == 1:
        data["schema_version"] = 2
        nb = data.setdefault("notebooklm", {})
        nb.setdefault("archive_notebook_id", None)
        nb.setdefault("archive_notebook_title", _ARCHIVE_NOTEBOOK_TITLE)
        nb.setdefault("archive_possibly_duplicate", False)

    if data.get("schema_version") != _STATE_SCHEMA_VERSION:
        return _default_state()

    # 필드별 enum 검증
    tv = data.get("tavily")
    if not isinstance(tv, dict) or tv.get("decision") not in _VALID_TAVILY_DECISIONS:
        data["tavily"] = dict(_default_state()["tavily"])

    nb = data.get("notebooklm")
    if not isinstance(nb, dict) or nb.get("decision") not in _VALID_NOTEBOOKLM_DECISIONS:
        data["notebooklm"] = dict(_default_state()["notebooklm"])

    return data


def _save_setup_state(state: dict[str, Any]) -> None:
    """
    Atomic write + 크로스플랫폼 파일락.

    - filelock 패키지가 POSIX/Windows 분기를 자동 선택
    - tempfile.mkstemp(dir=dir_)로 원본과 동일 파일시스템에 tmp 생성 →
      os.replace()가 cross-device 없이 원자적으로 작동
    - fsync로 디스크 동기화
    - 10초 타임아웃 시 경고 후 진행 (파이프라인 블록 금지)
    """
    if not isinstance(state, dict) or "schema_version" not in state:
        raise ValueError("setup_state: schema_version missing")

    path = _get_setup_state_path()
    dir_ = os.path.dirname(path) or "."
    try:
        os.makedirs(dir_, exist_ok=True)
    except OSError:
        pass

    def _atomic_write() -> None:
        fd, tmp = tempfile.mkstemp(
            prefix=".af_setup_state.", suffix=".tmp", dir=dir_
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass  # fsync 실패는 치명적 아님
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    lock_path = path + ".lock"
    try:
        if _HAS_FILELOCK:
            with FileLock(lock_path, timeout=10):
                _atomic_write()
        else:
            # filelock 없어도 atomic write는 수행 (경쟁 조건 위험 존재)
            print(
                "[Setup] Warning: filelock 미설치 — 동시 실행 경쟁 조건 보호 없음",
                file=sys.stderr,
            )
            _atomic_write()
    except Exception as e:
        print(f"[Setup] Warning: state 파일 저장 실패 — {e}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# 3. 모드 결정 + Chrome/nlm 감지
# ═══════════════════════════════════════════════════════════════════════════


def _resolve_mode(mode: str) -> str:
    """
    auto → interactive/noninteractive/silent 중 하나로 결정.
    """
    if mode != "auto":
        return mode
    if os.getenv("AGENT_SKIP_SETUP_HINT"):
        return "silent"
    if os.getenv("AGENT_NONINTERACTIVE"):
        return "noninteractive"
    if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        return "interactive"
    return "noninteractive"


def _is_interactive_mode(mode: Optional[str] = None) -> bool:
    if mode is not None:
        return mode == "interactive"
    return _resolve_mode("auto") == "interactive"


def _check_chrome_installed() -> bool:
    """
    OS별 Chrome 브라우저 존재 확인. nlm login (CDP)의 전제조건.
    """
    import shutil
    if sys.platform == "darwin":
        if os.path.isdir("/Applications/Google Chrome.app"):
            return True
        return shutil.which("google-chrome") is not None
    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        return any(os.path.isfile(p) for p in candidates)
    # Linux / others
    for cmd in ("google-chrome", "chromium", "google-chrome-stable", "chromium-browser"):
        if shutil.which(cmd):
            return True
    return False


def _nlm_cmd_base() -> list[str]:
    """
    frozen 환경: af 자체의 __nlm 내부 서브커맨드 사용 (run_factory_cli.py STAGE 1)
    개발 환경: 시스템 PATH의 nlm 바이너리 사용
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "__nlm"]
    return ["nlm"]


# ═══════════════════════════════════════════════════════════════════════════
# 4. NotebookLM 인증/노트북 관리
# ═══════════════════════════════════════════════════════════════════════════


def _check_notebooklm_auth(profile: str = "default") -> str:
    """
    Phase 0.5 실측 기준 (nlm 0.1.12):
      성공 → exit 0 + stdout `✓ Authenticated` + `Notebooks accessible: N`
      실패 → exit 2 + stdout `✗ Not authenticated` / `Profile not found`

    반환: "logged_in" | "not_authenticated" | "unknown"
    """
    try:
        cmd = _nlm_cmd_base() + ["auth", "status", "--profile", profile]
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"
    except Exception:
        return "unknown"

    out = (p.stdout or "") + (p.stderr or "")

    if p.returncode == 0:
        if "✓" in out and "authenticated" in out.lower():
            return "logged_in"
        # exit 0인데 성공 패턴 없으면 nlm 버전 변경 가능성 → unknown
        # 호출자는 "logged_in 추정"으로 진행 (§4.4 플로우)
        return "unknown"

    if p.returncode == 2:
        return "not_authenticated"

    return "unknown"


def _run_notebooklm_login(
    profile: str = "default",
    manual_cookie_file: Optional[str] = None,
    timeout: int = 300,
) -> tuple[bool, str]:
    """
    nlm login 실행. 성공/실패 + 메시지 반환.
    """
    try:
        cmd = _nlm_cmd_base() + ["login", "--profile", profile]
        if manual_cookie_file:
            cmd.extend(["--manual", "-f", manual_cookie_file])
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return (False, "login_timeout")
    except FileNotFoundError:
        return (False, "nlm_not_found")
    except Exception as e:
        return (False, f"exception: {e}")

    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode == 0 and "Successfully authenticated" in out:
        return (True, "ok")
    return (False, (p.stderr or p.stdout or "unknown_error").strip()[:500])


_CREATE_ID_RE = re.compile(
    r"^\s*ID:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$",
    re.MULTILINE,
)


def _parse_notebook_create_output(stdout: str) -> Optional[str]:
    """
    Phase 0.5 실측 포맷:
        ✓ Created notebook: <title>
          ID: <uuid>
    """
    m = _CREATE_ID_RE.search(stdout or "")
    return m.group(1) if m else None


def _parse_notebook_list_for_title(stdout: str, title: str) -> Optional[str]:
    """
    Phase 0.5 실측: nlm notebook list 출력은 순수 JSON 배열.
    """
    try:
        notebooks = json.loads(stdout or "[]")
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(notebooks, list):
        return None
    for nb in notebooks:
        if isinstance(nb, dict) and nb.get("title") == title:
            nb_id = nb.get("id")
            if isinstance(nb_id, str) and nb_id:
                return nb_id
    return None


def _looks_like_valid_json_array(s: str) -> bool:
    """
    stdout이 JSON 배열로 보이는지 가벼운 사전 체크 (§7.11 완화책).
    """
    s = (s or "").strip()
    return s.startswith("[") and s.endswith("]")


def _validate_notebook_uuid(nb_id: str, profile: str = "default") -> bool:
    """nlm notebook get <id>로 UUID 유효성 검증."""
    try:
        cmd = _nlm_cmd_base() + ["notebook", "get", nb_id, "--profile", profile]
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
        return p.returncode == 0
    except Exception:
        return False


def _find_or_create_archive_notebook(
    profile: str = "default",
    title: str = _ARCHIVE_NOTEBOOK_TITLE,
    interactive: bool = True,
) -> tuple[Optional[str], str]:
    """
    사용자 계정에 Agent Factory 전용 아카이브 노트북을 확보.

    Returns:
        (notebook_id, reason)
        notebook_id가 None이면 확보 실패 → 호출자가 §6.3 폴백 박스 호출
    """
    # Step 1: 기존 노트북 목록 조회
    list_parse_failed = False
    list_stdout_snippet = ""
    try:
        cmd = _nlm_cmd_base() + ["notebook", "list", "--profile", profile]
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
        if p.returncode == 0:
            nb_id = _parse_notebook_list_for_title(p.stdout, title)
            if nb_id:
                return (nb_id, "found_existing")
            # 파싱 실패 감지 (§7.11 완화책)
            if (p.stdout or "").strip() and not _looks_like_valid_json_array(p.stdout):
                list_parse_failed = True
                list_stdout_snippet = (p.stdout or "")[:500]
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        pass
    except Exception:
        pass

    # §7.11 완화책: JSON 파싱 실패 + interactive 모드 → 사용자 확인
    if list_parse_failed and interactive:
        print()
        print("[Setup] ⚠ nlm notebook list JSON 파싱 실패 — 원본 출력:")
        print("---begin stdout---")
        print(list_stdout_snippet)
        print("---end stdout---")
        print("중복 생성을 방지하기 위해 계속할지 확인합니다.")
        try:
            choice = input("계속 생성하시겠습니까? [Y/n/u=UUID 직접 입력]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return (None, "list_parse_failed_user_canceled")
        if choice == "n":
            return (None, "list_parse_failed_user_canceled")
        if choice == "u":
            manual = _prompt_manual_notebook_uuid(profile)
            if manual:
                return (manual, "manual_input")
            return (None, "list_parse_failed_manual_canceled")
        # 'Y' or empty → 계속 create 진행 (중복 가능성 플래그는 호출자가 저장)

    # Step 2: 새 노트북 생성
    try:
        cmd = _nlm_cmd_base() + ["notebook", "create", title, "--profile", profile]
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=False
        )
        if p.returncode == 0:
            nb_id = _parse_notebook_create_output(p.stdout)
            if nb_id:
                reason = "created_new_after_list_parse_failure" if list_parse_failed else "created_new"
                return (nb_id, reason)
            return (None, "created_but_parse_failed")
        return (None, f"create_failed: {(p.stderr or '')[:200]}")
    except subprocess.TimeoutExpired:
        return (None, "create_timeout")
    except FileNotFoundError:
        return (None, "nlm_not_found")
    except Exception as e:
        return (None, f"exception: {e}")


def _prompt_manual_notebook_uuid(profile: str = "default") -> Optional[str]:
    """사용자가 기존 노트북 UUID를 수동 입력하고 유효성 검증. 최대 3회 재시도."""
    for attempt in range(3):
        try:
            uuid_input = input("기존 노트북 UUID: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not uuid_input:
            return None
        # UUID 형식 간단 검증
        if not re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            uuid_input,
        ):
            print(f"  ✗ UUID 형식 오류 (예: 03662da6-f29e-43aa-b403-79f41b728cf4)")
            continue
        # 실제 유효성 검증
        if _validate_notebook_uuid(uuid_input, profile):
            print(f"  ✓ 노트북 확인됨")
            return uuid_input
        print(f"  ✗ 노트북 접근 불가 (권한 또는 존재하지 않음). {2 - attempt}회 남음")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 5. TAVILY / NotebookLM 개별 ensure 플로우
# ═══════════════════════════════════════════════════════════════════════════


def _box(lines: list[str]) -> None:
    """간단한 경고 박스 출력."""
    width = max(len(l) for l in lines) + 4
    print("┌" + "─" * (width - 2) + "┐")
    for l in lines:
        print(f"│ {l.ljust(width - 4)} │")
    print("└" + "─" * (width - 2) + "┘")


def _ensure_tavily(state: dict[str, Any], mode: str) -> None:
    """
    TAVILY_API_KEY 확보 플로우. state 인플레이스 수정.
    """
    tv = state.setdefault("tavily", dict(_default_state()["tavily"]))

    # 이미 환경변수에 있으면 configured
    if os.getenv("TAVILY_API_KEY"):
        tv["decision"] = "configured"
        return

    # .env에 있는지 확인 (로드해서 process env에 주입)
    env_path = _get_env_path()
    existing = _load_existing(env_path)
    if existing.get("TAVILY_API_KEY"):
        os.environ["TAVILY_API_KEY"] = existing["TAVILY_API_KEY"]
        tv["decision"] = "configured"
        return

    # 이미 "skipped"로 기록된 경우 조용히 진행
    if tv.get("decision") == "skipped":
        print("[Setup] TAVILY 스킵 상태 (af setup 실행 시 재설정)")
        return

    if mode == "silent":
        return

    if mode == "noninteractive":
        _box([
            "⚠  TAVILY_API_KEY 미설정",
            "웹 검색 비활성화 — 문서 품질 저하 가능",
            "af setup 실행으로 등록 가능",
        ])
        return

    # interactive 모드: 입력 UI + Y/N 재확인 루프
    while True:
        print()
        _box([
            "⚠  TAVILY_API_KEY 미설정",
            "",
            "TAVILY가 없으면 웹 검색이 비활성화되어",
            "생성되는 문서/코드의 품질이 낮아집니다.",
            "",
            "무료 발급: https://app.tavily.com",
        ])
        try:
            val = input("TAVILY_API_KEY 입력 (엔터=스킵): ").strip()
        except (EOFError, KeyboardInterrupt):
            tv["decision"] = "skipped"
            tv["last_prompt_at"] = _now_utc_iso()
            return

        if val:
            _save_env(env_path, {"TAVILY_API_KEY": val})
            os.environ["TAVILY_API_KEY"] = val
            tv["decision"] = "configured"
            tv["last_prompt_at"] = _now_utc_iso()
            print("  ✓ 저장 완료 → .env")
            return

        # 스킵 재확인
        print()
        _box([
            "⚠  재확인",
            "",
            "TAVILY 없이 진행하시겠습니까?",
            "→ 웹 검색 결과가 파이프라인에 반영되지 않습니다",
            "→ LLM 내재 지식만으로 리서치가 수행됩니다",
            "→ 최신 정보가 필요한 작업은 부정확할 수 있습니다",
        ])
        try:
            confirm = input("진행하시겠습니까? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            tv["decision"] = "skipped"
            tv["last_prompt_at"] = _now_utc_iso()
            return

        if confirm == "y":
            tv["decision"] = "skipped"
            tv["last_prompt_at"] = _now_utc_iso()
            print("  ⚠ TAVILY 스킵됨")
            return
        # 다른 입력 → 입력 프롬프트로 복귀 (루프)


def _ensure_notebooklm(state: dict[str, Any], mode: str) -> None:
    """
    NotebookLM 준비 플로우 (Medium 강도).
    """
    nb = state.setdefault("notebooklm", dict(_default_state()["notebooklm"]))

    # Step 1: nlm 모듈 존재 여부
    import importlib.util
    if importlib.util.find_spec("nlm") is None:
        nb["decision"] = "skipped"
        nb["last_login_error"] = "nlm module not found (source mode)"
        if mode != "silent":
            print("[Setup] nlm 미설치 — NotebookLM 경로 비활성화")
            print("        소스 모드 개발자: pip install notebooklm-cli")
        return

    # 이미 skipped 상태
    if nb.get("decision") == "skipped":
        if mode != "silent":
            print("[Setup] NotebookLM 스킵 상태 (af setup 실행 시 재설정)")
        return

    profile = nb.get("profile", "default")

    # Step 2: Chrome 설치 확인
    chrome_ok = _check_chrome_installed()
    if not chrome_ok:
        if mode != "interactive":
            nb["decision"] = "chrome_missing"
            if mode != "silent":
                print("[Setup] ⚠ Chrome 미감지 — NotebookLM 스킵 (수동 설치 필요)")
            return
        # interactive: Chrome 미설치 3지 선택
        _handle_chrome_missing(nb, profile)
        if nb.get("decision") in ("chrome_missing", "skipped"):
            return

    # Step 3: 로그인 상태 체크
    auth_status = _check_notebooklm_auth(profile)

    if auth_status == "logged_in":
        # Step 4: 아카이브 노트북 확보
        _ensure_archive_notebook(nb, profile, mode)
        return

    if auth_status == "unknown":
        # ⚠ critic WARN#1: "logged_in 추정"으로 진행
        print(
            "[Setup] ⚠ nlm auth status 출력 포맷을 해석하지 못함 — 로그인 상태 추정으로 진행.",
            file=sys.stderr,
        )
        print(
            "        R5/R11 CI 회귀 감지 예정. nlm 버전 업그레이드 가능성 확인 필요.",
            file=sys.stderr,
        )
        nb["decision"] = "logged_in"
        _ensure_archive_notebook(nb, profile, mode)
        return

    # auth_status == "not_authenticated"
    if mode == "silent":
        return

    if mode == "noninteractive":
        _box([
            "⚠  NotebookLM 미로그인 — 비대화형 모드라 스킵",
            "af setup 또는 nlm login --profile default 실행 필요",
        ])
        nb["decision"] = "skipped"
        return

    # interactive: Medium 강도 로그인 유도
    _handle_notebooklm_login(nb, profile)
    if nb.get("decision") == "logged_in":
        _ensure_archive_notebook(nb, profile, mode)


def _handle_chrome_missing(nb: dict[str, Any], profile: str) -> None:
    """Chrome 미설치 시 3지 선택 메뉴."""
    while True:
        print()
        _box([
            "⚠  Chrome 미감지",
            "",
            "NotebookLM 로그인은 Chrome DevTools Protocol을",
            "사용하므로 Google Chrome이 필요합니다.",
            "",
            "다운로드: https://www.google.com/chrome",
        ])
        print("[1] Chrome 설치 후 재시도")
        print("[2] 수동 쿠키 파일 경로 입력")
        print("[3] NotebookLM 없이 진행")
        try:
            choice = input("선택 [1/2/3]: ").strip()
        except (EOFError, KeyboardInterrupt):
            nb["decision"] = "skipped"
            return

        if choice == "1":
            nb["decision"] = "chrome_missing"
            print("  → 다음 af 실행 시 Chrome 재검사")
            return
        if choice == "2":
            try:
                cookie_path = input("쿠키 파일 경로: ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not cookie_path or not os.path.isfile(cookie_path):
                print(f"  ✗ 파일을 찾을 수 없음: {cookie_path}")
                continue
            ok, msg = _run_notebooklm_login(profile, manual_cookie_file=cookie_path)
            nb["last_login_attempt_at"] = _now_utc_iso()
            if ok:
                nb["decision"] = "logged_in"
                nb["last_login_error"] = None
                print("  ✓ 로그인 완료 (manual profile)")
                return
            nb["last_login_error"] = msg
            print(f"  ✗ 로그인 실패: {msg}")
            continue
        if choice == "3":
            try:
                confirm = input("NotebookLM 없이 진행하시겠습니까? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                nb["decision"] = "skipped"
                return
            if confirm == "y":
                nb["decision"] = "skipped"
                return


def _handle_notebooklm_login(nb: dict[str, Any], profile: str) -> None:
    """Medium 강도 NotebookLM 로그인 유도."""
    max_retries = 2
    for attempt in range(max_retries + 1):
        print()
        _box([
            "⚠  NotebookLM 로그인 필요",
            "",
            "NotebookLM은 리서치 품질의 핵심 구성요소입니다.",
            "브라우저가 열리면 Google 계정으로 로그인하세요.",
            "",
            "(취소하려면 Ctrl+C)",
        ])
        try:
            choice = input("지금 브라우저를 열어 로그인하시겠습니까? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            nb["decision"] = "skipped"
            nb["last_login_attempt_at"] = _now_utc_iso()
            return

        if choice == "n":
            if _confirm_skip_notebooklm():
                nb["decision"] = "skipped"
                nb["last_login_attempt_at"] = _now_utc_iso()
                return
            continue

        # 'Y' or empty → 로그인 시도
        print("  브라우저 로그인 중 (최대 5분)...")
        ok, msg = _run_notebooklm_login(profile)
        nb["last_login_attempt_at"] = _now_utc_iso()

        if ok:
            nb["decision"] = "logged_in"
            nb["last_login_error"] = None
            print("  ✓ 로그인 완료")
            return

        nb["last_login_error"] = msg
        nb["decision"] = "login_failed"
        print(f"  ✗ 로그인 실패: {msg}")

        if attempt >= max_retries:
            break

        # 재시도/수동/스킵 선택
        print()
        print("[R] 다시 시도  [M] 수동 쿠키 파일 모드  [s] 스킵")
        try:
            retry_choice = input("선택 [R/M/s]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            nb["decision"] = "skipped"
            return
        if retry_choice == "s":
            if _confirm_skip_notebooklm():
                nb["decision"] = "skipped"
                return
            continue
        if retry_choice == "m":
            try:
                cookie_path = input("쿠키 파일 경로: ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if cookie_path and os.path.isfile(cookie_path):
                ok, msg = _run_notebooklm_login(profile, manual_cookie_file=cookie_path)
                if ok:
                    nb["decision"] = "logged_in"
                    nb["last_login_error"] = None
                    print("  ✓ 로그인 완료 (manual)")
                    return
                nb["last_login_error"] = msg
                print(f"  ✗ 수동 로그인 실패: {msg}")
            continue
        # 'R' or empty → 다음 루프

    # 최종 실패 시 스킵 유도
    if _confirm_skip_notebooklm():
        nb["decision"] = "skipped"


def _confirm_skip_notebooklm() -> bool:
    """NotebookLM 스킵 재확인 박스."""
    print()
    _box([
        "⚠  재확인",
        "",
        "NotebookLM 없이 진행하시겠습니까?",
        "→ 심층 분석 쿼리가 수행되지 않습니다",
        "→ 문서 품질이 낮아집니다",
    ])
    try:
        confirm = input("진행하시겠습니까? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return True
    return confirm == "y"


def _ensure_archive_notebook(
    nb: dict[str, Any], profile: str, mode: str
) -> None:
    """
    Step 4: 아카이브 노트북 확보 (logged_in 이후).
    state.notebooklm.archive_notebook_id 저장.
    """
    # 이미 저장된 UUID가 있으면 유효성만 확인
    existing_uuid = nb.get("archive_notebook_id")
    if existing_uuid and _validate_notebook_uuid(existing_uuid, profile):
        if mode != "silent":
            print(f"[Setup] ✓ NotebookLM archive 재사용: {existing_uuid}")
        return

    # 탐색 + 생성
    if mode != "silent":
        print("[Setup] 아카이브 노트북 확인 중...")
    nb_id, reason = _find_or_create_archive_notebook(
        profile=profile,
        title=nb.get("archive_notebook_title", _ARCHIVE_NOTEBOOK_TITLE),
        interactive=(mode == "interactive"),
    )

    if nb_id:
        nb["archive_notebook_id"] = nb_id
        nb["archive_possibly_duplicate"] = (
            reason == "created_new_after_list_parse_failure"
        )
        if mode != "silent":
            prefix = "재사용" if reason == "found_existing" else "생성"
            print(f"[Setup] ✓ NotebookLM archive {prefix}: {nb_id}")
        return

    # 확보 실패 → 폴백 박스
    if mode != "interactive":
        if mode != "silent":
            print(f"[Setup] ⚠ 아카이브 노트북 확보 실패: {reason}")
        return

    _handle_archive_fallback(nb, profile, reason)


def _handle_archive_fallback(
    nb: dict[str, Any], profile: str, reason: str
) -> None:
    """아카이브 확보 실패 시 3지 선택."""
    print()
    _box([
        "⚠  아카이브 노트북 확보 실패",
        f"사유: {reason[:60]}",
        "",
        "[1] 기존 노트북 UUID를 직접 입력",
        "[2] 지금 스킵 (다음 실행 시 재시도)",
        "[3] NotebookLM 없이 진행",
    ])
    try:
        choice = input("선택 [1/2/3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "1":
        manual = _prompt_manual_notebook_uuid(profile)
        if manual:
            nb["archive_notebook_id"] = manual
            print(f"  ✓ 저장: {manual}")
        return
    if choice == "2":
        # decision=logged_in 유지, archive_notebook_id=None
        return
    if choice == "3":
        if _confirm_skip_notebooklm():
            nb["decision"] = "skipped"


# ═══════════════════════════════════════════════════════════════════════════
# 6. 공개 API
# ═══════════════════════════════════════════════════════════════════════════


def ensure_external_research_capabilities(
    *,
    mode: str = "auto",
) -> dict[str, Any]:
    """
    파이프라인 실행 직전 호출되는 단일 진입점.

    mode:
        "auto"           — stdin.isatty() + AGENT_NONINTERACTIVE 감안 자동 결정
        "interactive"    — 강제 대화형
        "noninteractive" — 강제 비대화형 (경고만)
        "silent"         — 완전 침묵 (AGENT_SKIP_SETUP_HINT=1 대응)

    Returns:
        {
          "tavily":     {"available": bool, "decision": str},
          "notebooklm": {"available": bool, "decision": str,
                         "chrome": bool, "archive_notebook_id": str | None},
          "mode": str,
        }
    """
    resolved_mode = _resolve_mode(mode)
    if resolved_mode == "silent":
        # 완전 침묵: state 로드만, 출력/프롬프트 없음
        state = _load_setup_state()
        return {
            "tavily": {
                "available": bool(os.getenv("TAVILY_API_KEY")),
                "decision": state.get("tavily", {}).get("decision", "pending"),
            },
            "notebooklm": {
                "available": False,  # silent 모드에서는 체크하지 않음
                "decision": state.get("notebooklm", {}).get("decision", "pending"),
                "chrome": False,
                "archive_notebook_id": state.get("notebooklm", {}).get("archive_notebook_id"),
            },
            "mode": "silent",
        }

    if resolved_mode not in ("interactive", "noninteractive"):
        resolved_mode = "noninteractive"

    if resolved_mode == "interactive":
        print("[Setup] 외부 리서치 도구 점검 중...")

    state = _load_setup_state()

    try:
        _ensure_tavily(state, resolved_mode)
    except Exception as e:
        print(f"[Setup] Warning: TAVILY 점검 실패 — {e}", file=sys.stderr)

    try:
        _ensure_notebooklm(state, resolved_mode)
    except Exception as e:
        print(f"[Setup] Warning: NotebookLM 점검 실패 — {e}", file=sys.stderr)

    try:
        _save_setup_state(state)
    except Exception as e:
        print(f"[Setup] Warning: state 저장 실패 — {e}", file=sys.stderr)

    tv = state.get("tavily", {})
    nb = state.get("notebooklm", {})
    return {
        "tavily": {
            "available": bool(os.getenv("TAVILY_API_KEY")),
            "decision": tv.get("decision", "pending"),
        },
        "notebooklm": {
            "available": nb.get("decision") == "logged_in"
            and bool(nb.get("archive_notebook_id")),
            "decision": nb.get("decision", "pending"),
            "chrome": _check_chrome_installed(),
            "archive_notebook_id": nb.get("archive_notebook_id"),
        },
        "mode": resolved_mode,
    }

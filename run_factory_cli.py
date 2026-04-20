import argparse
import os
import re
import sys

# PyInstaller 환경에서 stdout 버퍼링 해제
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(FACTORY_DIR)

# .env 자동 로드 — TAVILY_API_KEY 등 외부 서비스 키 포함
def _load_dotenv() -> None:
    # 탐색 순서: exe 옆 디렉토리(frozen) → 소스 루트 → cwd
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), ".env"))
    candidates.append(os.path.join(FACTORY_DIR, ".env"))
    candidates.append(os.path.join(os.getcwd(), ".env"))

    for env_path in candidates:
        if not os.path.isfile(env_path):
            continue
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                k, v = raw.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        break  # 첫 번째 발견한 .env만 사용

_load_dotenv()

CLI_PROVIDER_CHOICES = ("claude_cli", "gemini_cli", "codex_cli")
CLI_PROVIDER_COMMAND_ENVS = {
    "claude_cli": "AGENT_CLAUDE_CLI_COMMAND",
    "gemini_cli": "AGENT_GEMINI_CLI_COMMAND",
    "codex_cli": "AGENT_CODEX_CLI_COMMAND",
}

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 메타 플래그 상수 — `_is_meta_only`(모듈 최상위 CLI 자동 탐색 가드)와
# `_is_meta_arg`(STAGE 2 gate 가드; 현재는 gate가 parse_args 뒤로 이동해 gate용
# 역할은 제거되었지만 테스트·외부 임포트 호환을 위해 유지) 양쪽에서 사용.
_HELP_FLAGS = ("--help", "-h")
_META_FLAGS = _HELP_FLAGS + ("--version", "-V")

# 시작 즉시 CLI 프로바이더 자동 탐색 및 런타임 레지스트리 설정.
# `--help`/`-h`/`--version`/`-V` 메타 플래그는 argparse가 즉시 처리·종료하므로
# LLM 탐색 불필요 → 스킵해서 즉시 출력 + stdout 오염 ([Auto-Config] 배너) 방지.
_is_meta_only = any(a in sys.argv for a in _META_FLAGS)
if not _is_meta_only:
    try:
        from core.engine_auth import auto_configure_cli_provider
        auto_configure_cli_provider()
    except Exception:
        pass  # 임포트 실패 시 무시 (이후 check_llm_available()에서 재시도)



def _safe_project_id(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9_\-]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t



def _resolve_projects_root(override: str | None = None) -> str:
    raw = str(override or os.getenv("AGENT_PROJECTS_DIR", "") or "").strip()
    if not raw:
        raw = os.path.join(FACTORY_DIR, "projects")
    return os.path.abspath(os.path.expanduser(raw))



def _run_skill_creator(argv: list[str] | None = None):
    """skill-create subcommand."""
    from core.skill_creator import cli_main

    cli_main(argv)



def _run_skill_spec(argv: list[str] | None = None):
    """skill-spec subcommand."""
    from core.skill_spec_synthesizer import cli_main

    cli_main(argv)



def _run_preflight(argv: list[str] | None = None):
    """preflight subcommand."""
    from core.skill_preflight import cli_main

    cli_main(argv)



def _run_skill_eval(argv: list[str] | None = None):
    """skill-eval subcommand."""
    from core.skill_eval_harness import cli_main

    cli_main(argv)



def _run_skill_promote(argv: list[str] | None = None):
    """skill-promote subcommand."""
    from core.skill_promotion import cli_main

    cli_main(argv)



# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — STAGE 1/2/3 진입점 통합 (설계문서 §4.5)
# ─────────────────────────────────────────────────────────────────────────────

def _run_setup_subcommand(rest: list[str]) -> None:
    from core.setup_wizard import run_setup
    run_setup(interactive=True)


def _run_worker_subcommand(rest: list[str]) -> None:
    """worker 서브커맨드: PyInstaller exe에서 에이전트 워커 실행.

    sys.argv는 try/finally로 백업·복원해 호출자(테스트 하네스 등)의 전역
    상태를 오염시키지 않는다 — _invoke_nlm_app()와 동일한 패턴.
    """
    from core.agent_worker import main as worker_main
    saved_argv = sys.argv
    try:
        sys.argv = ["af-worker"] + list(rest)
        worker_main()
    finally:
        sys.argv = saved_argv


def _run_nlm_subcommand(rest: list[str]) -> None:
    """__nlm 숨은 서브커맨드: af 프로세스 내부에서 nlm Typer app 호출.

    설계문서 §4.5에 따라 명시적으로 sys.exit()을 호출한다 (다른 서브커맨드의
    return 패턴과 비대칭). 이유: __nlm은 _check_notebooklm_auth()가 subprocess
    경계로 호출하는 진입점이라 exit code가 호출자 측의 판정 신호로 쓰인다.
    """
    exit_code = _invoke_nlm_app(rest)
    sys.exit(exit_code)


def _run_check_nlm_subcommand(rest: list[str]) -> None:
    """__check-nlm 숨은 서브커맨드: nlm 패키지 import 가능 여부 검사."""
    try:
        import nlm  # noqa: F401
        sys.exit(0)
    except ImportError:
        sys.exit(1)


def _run_nightly_start(rest: list[str]) -> None:
    """nightly-start: 야간 자율 모드 활성화 + launchd plist 설치."""
    import argparse
    import subprocess
    from core.nightly_state import load_state, save_state

    parser = argparse.ArgumentParser(prog="af nightly-start")
    parser.add_argument("--workspace", "-w", type=str, default=None)
    parser.add_argument("--budget", type=int, default=0, help="야간 최대 토큰 (0=unlimited)")
    parser.add_argument("--project", "-p", type=str, default=None, help="활성 프로젝트 ID")
    args = parser.parse_args(rest)

    ws = args.workspace or FACTORY_DIR
    state = load_state(ws)
    state.nightly_autonomy_enabled = True
    if args.project:
        state.active_project = args.project
        import os
        from core.utils import safe_id
        projects_root = os.environ.get("AGENT_PROJECTS_DIR", os.path.join(FACTORY_DIR, "projects"))
        state.active_workspace = os.path.join(projects_root, safe_id(args.project))
    if args.budget > 0:
        state.budget.max_tokens = args.budget
    save_state(state, ws)

    # 플랫폼별 스케줄러 설치
    import importlib.util
    from pathlib import Path as _Path
    _sched_path = os.path.join(FACTORY_DIR, "scripts", "install_scheduler.py")
    if os.path.exists(_sched_path):
        _spec = importlib.util.spec_from_file_location("install_scheduler", _sched_path)
        if _spec is None:
            print("[nightly-start] install_scheduler.py 로드 실패. 수동으로 15분 주기 설정 필요.", file=sys.stderr)
        else:
            _sched = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_sched)  # type: ignore[union-attr]
            _sched.install(_Path(FACTORY_DIR), _Path(ws))
    else:
        print("[nightly-start] install_scheduler.py 없음. 수동으로 15분 주기 설정 필요.", file=sys.stderr)

    print(f"[nightly-start] 자율 모드 활성화됨. 프로젝트={state.active_project or '(미지정)'}")


def _run_nightly_stop(rest: list[str]) -> None:
    """nightly-stop: 야간 자율 모드 비활성화 + launchd plist 언로드."""
    import subprocess
    from core.nightly_state import load_state, save_state

    import argparse
    parser = argparse.ArgumentParser(prog="af nightly-stop")
    parser.add_argument("--workspace", "-w", type=str, default=None)
    args = parser.parse_args(rest)

    ws = args.workspace or FACTORY_DIR
    state = load_state(ws)
    state.nightly_autonomy_enabled = False
    save_state(state, ws)

    import importlib.util
    from pathlib import Path as _Path
    _sched_path = os.path.join(FACTORY_DIR, "scripts", "install_scheduler.py")
    if os.path.exists(_sched_path):
        _spec = importlib.util.spec_from_file_location("install_scheduler", _sched_path)
        if _spec is not None:
            _sched = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_sched)  # type: ignore[union-attr]
            _sched.uninstall(_Path(FACTORY_DIR))

    print("[nightly-stop] 자율 모드 비활성화됨.")


def _run_nightly_status(rest: list[str]) -> None:
    """nightly-status: 야간 파이프라인 현재 상태 출력."""
    from core.nightly_state import load_state, summary_path, alert_flag_path
    from core.watchdog import WatchdogState

    import argparse
    parser = argparse.ArgumentParser(prog="af nightly-status")
    parser.add_argument("--workspace", "-w", type=str, default=None)
    args = parser.parse_args(rest)

    ws = args.workspace or FACTORY_DIR
    state = load_state(ws)
    b = state.budget
    w = state.watchdog

    print(f"=== 야간 자율 파이프라인 상태 ===")
    print(f"  활성: {'예' if state.nightly_autonomy_enabled else '아니오'}")
    print(f"  프로젝트: {state.active_project or '(없음)'}")
    print(f"  Watchdog: {w.watchdog_level} (연속 무진전: {w.consecutive_no_progress_ticks})")
    print(f"  예산: {b.consumed_tokens:,}/{b.max_tokens or 'unlimited'} tokens")
    print(f"  Tick 횟수: {b.tick_count}")
    print(f"  마지막 tick: {state.last_tick_id or '(없음)'}")
    alert = alert_flag_path(ws)
    if alert.exists():
        print(f"  ⚠️  ALERT 플래그 존재: {alert.read_text()[:200]}")
    summary = summary_path(ws)
    if summary.exists():
        print(f"  요약 파일: {summary}")


def _run_nightly_tick(rest: list[str]) -> None:
    """nightly-tick: 수동 1회 tick (launchd 호출과 동일)."""
    from scripts.nightly_tick import main as tick_main
    sys.exit(tick_main(rest))


# STAGE 1에서 setup gate 이전에 즉시 분기되어야 하는 서브커맨드 dispatch.
# 단일 진실원천: 새 항목 추가 시 이 dict만 수정하면 STAGE 1 분기에 자동 반영된다
# (af-critic WARN 5 해소 — 집합/if-체인 이중 진실원천 제거).
# - 기존 내부 서브커맨드: setup / worker / skill-* / preflight
# - v3 신규: __nlm / __check-nlm (NotebookLM CLI를 af 프로세스 내부에서 invoke)
# - Phase 0 신규: nightly-start / nightly-stop / nightly-status / nightly-tick
_STAGE1_DISPATCH: dict[str, "callable[[list[str]], None]"] = {
    "setup":           _run_setup_subcommand,
    "worker":          _run_worker_subcommand,
    "skill-create":    lambda rest: _run_skill_creator(rest),
    "skill-spec":      lambda rest: _run_skill_spec(rest),
    "preflight":       lambda rest: _run_preflight(rest),
    "skill-eval":      lambda rest: _run_skill_eval(rest),
    "skill-promote":   lambda rest: _run_skill_promote(rest),
    "__nlm":           _run_nlm_subcommand,
    "__check-nlm":     _run_check_nlm_subcommand,
    "nightly-start":   _run_nightly_start,
    "nightly-stop":    _run_nightly_stop,
    "nightly-status":  _run_nightly_status,
    "nightly-tick":    _run_nightly_tick,
}


def _is_help_arg(argv: list[str]) -> bool:
    """argparse `--help`/`-h` 단락 검사 — STAGE 1 서브커맨드 레벨 usage 가드 전용.

    서브커맨드 `--version` 등은 하위 Typer/argparse가 직접 처리해야 하므로
    여기서는 `--help`/`-h`만 막는다.
    """
    return any(a in _HELP_FLAGS for a in argv)


def _is_meta_arg(argv: list[str]) -> bool:
    """메타 플래그(`--help`/`-h`/`--version`/`-V`) 감지 — 외부 호환용.

    원래 STAGE 2 setup gate 우회용이었으나, e024ed8f 교차검증(Q1/Q2)에 따라
    gate 자체를 `parse_args()` 뒤로 이동해 구조적으로 해소됨(2026-04-14).
    `af --invalid-flag`처럼 argparse가 거부하는 모든 경로가 자동으로 보호되어
    이 함수는 테스트/외부 진단용으로만 유지된다.
    """
    return any(a in _META_FLAGS for a in argv)


# STAGE 1 서브커맨드별 한 줄 usage. `af <cmd> --help` 시 실제 핸들러를 호출하지
# 않고 이 사전의 문자열만 출력하고 종료한다 (cross-review BLOCK A 해소).
# 하위 argparse/Typer가 자체 --help를 처리하는 커맨드(worker, skill-*, __nlm 등)
# 라도 setup_wizard처럼 부작용이 먼저 시작되는 경우가 있으므로 일괄 가드한다.
_STAGE1_USAGE = {
    "setup":           "usage: af setup    # API 키·TAVILY·NotebookLM 대화형 설정 마법사",
    "worker":          "usage: af worker --task-file PATH    # PyInstaller exe 전용 에이전트 워커",
    "skill-create":    "usage: af skill-create [ARGS...]    # 스킬 생성 (자세한 옵션은 core/skill_creator.py)",
    "skill-spec":      "usage: af skill-spec [ARGS...]    # 스킬 스펙 합성 (core/skill_spec_synthesizer.py)",
    "preflight":       "usage: af preflight [ARGS...]    # 스킬 preflight 검사 (core/skill_preflight.py)",
    "skill-eval":      "usage: af skill-eval [ARGS...]    # 스킬 평가 하네스 (core/skill_eval_harness.py)",
    "skill-promote":   "usage: af skill-promote [ARGS...]    # 스킬 승격 (core/skill_promotion.py)",
    "__nlm":           "usage: af __nlm <nlm-args>    # (hidden) af 프로세스 내부 nlm Typer 호출",
    "__check-nlm":     "usage: af __check-nlm    # (hidden) nlm 패키지 import 가능 여부 검사",
    "nightly-start":   "usage: af nightly-start [--workspace PATH] [--budget TOKENS] [--project ID]    # 야간 자율 모드 활성화",
    "nightly-stop":    "usage: af nightly-stop [--workspace PATH]    # 야간 자율 모드 비활성화",
    "nightly-status":  "usage: af nightly-status [--workspace PATH]    # 야간 파이프라인 상태 조회",
    "nightly-tick":    "usage: af nightly-tick [--workspace PATH]    # 수동 1회 tick 실행",
}


def _run_setup_gate() -> None:
    """일반 파이프라인 실행 직전에 setup 점검을 수행. 실패해도 진행한다."""
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
    - 호출 시그니처: typer 0.24.1 + nlm 0.1.12에서 `app(args, standalone_mode=False)`
      가 동작함을 실측 확인. 향후 Typer가 시그니처를 변경하면
      `from typer.main import get_command; get_command(app).main(args=rest,
      standalone_mode=False, prog_name="nlm")` 패턴으로 전환 (cross-review (A) 안전망).
    """
    try:
        from nlm.cli.main import app
    except ImportError as e:
        print(f"[__nlm] notebooklm-cli 미설치: {e}", file=sys.stderr)
        return 127

    # 명시적 list 복사로 의도를 분명히 한다 (cross-review (B) 가독성 권고)
    saved_argv = list(sys.argv)
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


def _launch_interactive_mode(
    projects_root: str,
    *,
    role: str = "General Assistant",
    model: str = "",
    execution_mode: str = "approval",
    pipeline_mode: str = "auto",
    enable_build: bool = False,
):
    """대화형 모드 진입점 (인자 없이 af 실행 시) — 바로 채팅 시작."""
    from core.interactive_chat import run_interactive

    project_id = "default"
    workspace = os.path.join(projects_root, project_id)
    os.makedirs(workspace, exist_ok=True)
    os.environ["AGENT_PROJECTS_DIR"] = projects_root
    os.environ["AGENT_PROJECT_ID"] = project_id
    os.environ["AGENT_PROJECT_ROOT"] = workspace
    os.environ.setdefault("AGENT_AUTO_INSTALL_CLI", "1")

    run_interactive(
        project_id=project_id,
        workspace=workspace,
        role=role,
        model=model,
        auto_approve=(execution_mode == "fsa"),
        execution_mode=execution_mode,
        pipeline_mode=pipeline_mode,
        enable_build=enable_build,
    )


def main(argv: list[str] | None = None):
    effective_argv = argv if argv is not None else sys.argv[1:]

    # ── STAGE 1: 내부/숨은 서브커맨드는 setup gate 전에 즉시 분기 ──
    # (재귀 방지: __nlm 등이 gate를 거치면 setup_wizard 내부에서 nlm을 다시
    #  호출하는 경로와 무한 루프가 발생할 수 있음 — 설계문서 §4.5, §7.2, §7.3)
    if effective_argv:
        handler = _STAGE1_DISPATCH.get(effective_argv[0])
        if handler is not None:
            rest = effective_argv[1:]
            # 서브커맨드 레벨 --help 가드: `af setup --help`가 wizard를,
            # `af worker --help`가 agent_worker를 트리거하지 않게 usage만 출력
            # (cross-review BLOCK A 해소).
            if _is_help_arg(rest):
                print(_STAGE1_USAGE[effective_argv[0]])
                return
            handler(rest)
            return

    # ── STAGE 2: 인자 없음 / `--interactive` 단독 → 대화형 PDCA 모드 ──
    # 이 짧은 경로는 argparse를 거치지 않으므로 setup gate를 직접 호출.
    # (가드 불필요: argparse가 처리할 메타 플래그 케이스가 아니라 명시적 진입점)
    if not effective_argv or effective_argv == ["--interactive"]:
        _run_setup_gate()
        projects_root = _resolve_projects_root()
        _launch_interactive_mode(projects_root)
        return

    # ── STAGE 3: argparse 우선 (gate는 parse_args 성공 후로 이동) ──
    # cross-review Q1/Q2 ACCEPT (2026-04-14) 해소:
    # - `af --version`/`-V` → action='version'이 SystemExit(0)으로 즉시 종료 → gate 미실행
    # - `af --help`/`-h` → argparse가 SystemExit(0)으로 즉시 종료 → gate 미실행
    # - `af --invalid-flag` → argparse가 SystemExit(2)로 즉시 종료 → gate 미실행
    # → "인자 검증 전 사이드이펙트" 클래스 버그 전체가 구조적으로 차단된다.
    try:
        from version import __version__ as _af_version
    except Exception:
        _af_version = "0.0.0"

    parser = argparse.ArgumentParser(description="Agent Factory CLI")
    parser.add_argument(
        "--version", "-V", action="version",
        version=f"af {_af_version}",
    )
    parser.add_argument("--interactive", action="store_true", help="대화형 PDCA 모드 시작")
    parser.add_argument("--project", "-p", type=str, required=False, help="Project id")
    parser.add_argument("--role", "-r", type=str, help="Agent role")
    parser.add_argument("--task", "-t", type=str, help="Task input")
    parser.add_argument("--model", "-m", type=str, default=None, help="Model override")
    parser.add_argument("--provider", choices=CLI_PROVIDER_CHOICES, help="Force CLI provider")
    parser.add_argument("--provider-command", type=str, help="CLI provider command path")
    parser.add_argument("--projects-root", type=str, help="Projects root override")
    parser.add_argument("--workflow", "-w", type=str, help="Workflow YAML path")
    parser.add_argument("--agents", "-a", type=str, help="Comma-separated workflow roles")
    parser.add_argument("--mode", choices=["approval", "fsa", "ise"], default="approval", help="Execution mode")
    parser.add_argument("--fsa", action="store_true", help="Shortcut for full self automation mode")
    parser.add_argument("--ise", action="store_true", help="Infinite Self-Evolution mode (무한 자기진화 루프)")
    parser.add_argument("--build", action="store_true", help="Build missing skills before run")
    parser.add_argument("--no-cli-auto-install", action="store_true", help="Disable missing CLI auto install")
    parser.add_argument("--pipeline", choices=["auto", "single", "project"], default="auto", help="Pipeline mode")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode (continuous conversation)")
    # WARN-1 fix: argv가 아닌 effective_argv를 전달해 단일 진실원천 유지.
    args = parser.parse_args(effective_argv)

    # ── STAGE 4: parse_args 성공 후 setup gate 실행 ──
    # 여기까지 오면 인자가 모두 유효함이 검증된 상태. 실제 파이프라인이 돌기 전
    # 외부 리서치 도구(TAVILY/NotebookLM)를 확보한다.
    _run_setup_gate()
    execution_mode = "ise" if (args.ise or args.mode == "ise") else ("fsa" if (args.fsa or args.mode == "fsa") else "approval")

    # --interactive 또는 --project 미입력 → 대화형 PDCA 모드
    if getattr(args, "interactive", False) or not args.project:
        projects_root = _resolve_projects_root(args.projects_root if hasattr(args, "projects_root") else None)
        _launch_interactive_mode(
            projects_root,
            role=(args.role or "").strip() or "General Assistant",
            model=args.model or "",
            execution_mode=execution_mode,
            pipeline_mode=args.pipeline,
            enable_build=bool(args.build),
        )
        return

    if args.provider_command and not args.provider:
        parser.error("--provider-command requires --provider")

    project_id = _safe_project_id(args.project)
    if not project_id:
        print("Enter a valid project id.")
        return

    role = (args.role or "").strip() or "General Assistant"

    projects_root = _resolve_projects_root(args.projects_root)
    project_root = os.path.join(projects_root, project_id)
    os.makedirs(project_root, exist_ok=True)
    os.environ["AGENT_PROJECTS_DIR"] = projects_root
    os.environ["AGENT_PROJECT_ID"] = project_id
    os.environ["AGENT_PROJECT_ROOT"] = project_root
    if args.model:
        os.environ["AGENT_CHAT_MODEL"] = args.model.strip()
    if args.provider:
        try:
            from core.providers.registry import configure_providers
            configure_providers([args.provider])
        except Exception as _exc:
            import logging as _logging
            _logging.getLogger(__name__).debug("configure_providers 실패: %s", _exc)
        os.environ["AGENT_CHAT_PROVIDER"] = args.provider  # 항상 설정
    if args.provider_command:
        os.environ[CLI_PROVIDER_COMMAND_ENVS[args.provider]] = args.provider_command.strip()
    if args.no_cli_auto_install:
        os.environ["AGENT_AUTO_INSTALL_CLI"] = "0"
    else:
        os.environ.setdefault("AGENT_AUTO_INSTALL_CLI", "1")

    # ── 대화형 채팅 모드 ──
    if args.chat:
        from core.interactive_chat import run_interactive
        run_interactive(
            project_id=project_id,
            workspace=project_root,
            role=role,
            model=args.model or "",
            auto_approve=(execution_mode == "fsa"),
            execution_mode=execution_mode,
            pipeline_mode=args.pipeline,
            enable_build=bool(args.build),
        )
        return

    # ── 기존 태스크 실행 모드 ──
    task = args.task
    if not task:
        print("\n[Task Input]")
        task = input("  Enter the task: ").strip()

    if not task:
        print("Task input is empty. Exiting.")
        return

    from agent_launcher import AgentFactory

    print("\n[Logi-Mind Agent Factory] start")
    print(f"Project ID: {project_id}")
    print(f"Projects Root: {projects_root}")
    print(f"Project Root: {project_root}")
    print(f"Role: {role}")
    print("-" * 50)

    try:
        factory = AgentFactory()
        if args.workflow:
            roles = [item.strip() for item in (args.agents or "").split(",") if item.strip()]
            factory.run_workflow(task_input=task, workflow_path=args.workflow, role_specs=roles)
        else:
            factory.run(
                task_input=task,
                role_spec=role,
                enable_build=bool(args.build),
                execution_mode=execution_mode,
                pipeline_mode=args.pipeline,
            )
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as exc:
        print(f"\nError: {exc}")


if __name__ == "__main__":
    main()

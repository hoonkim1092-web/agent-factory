"""
tests/test_setup_wizard_gate.py — Setup Wizard + STAGE 1 gate 단위 테스트 20종.

설계 문서: docs/features/2026-04-10-setup-wizard-tavily-notebooklm-integration.md §8.1
Blueprint: Master_Blueprint.md §3.11
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from core import setup_wizard


# ═══════════════════════════════════════════════════════════════════════════
# 공용 fixture — state 파일을 tmp_path 내부로 유도 (실사용 ~/.env 오염 방지)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """_get_env_path / _get_setup_state_path를 tmp_path로 고정."""
    env_path = str(tmp_path / ".env")
    monkeypatch.setattr(setup_wizard, "_get_env_path", lambda: env_path)
    for k in ("TAVILY_API_KEY", "AGENT_SKIP_SETUP_HINT", "AGENT_NONINTERACTIVE"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path


def _write_state(tmp_path: Path, state: dict) -> Path:
    p = tmp_path / ".af_setup_state.json"
    p.write_text(json.dumps(state), encoding="utf-8")
    return p


# ═══════════════════════════════════════════════════════════════════════════
# 1~5. TAVILY 플로우
# ═══════════════════════════════════════════════════════════════════════════

def test_ensure_tavily_configured_no_prompt(isolated_state, monkeypatch):
    """env에 TAVILY_API_KEY 있으면 프롬프트 없이 decision=configured."""
    monkeypatch.setenv("TAVILY_API_KEY", "key-env")
    state = setup_wizard._default_state()
    setup_wizard._ensure_tavily(state, mode="interactive")
    assert state["tavily"]["decision"] == "configured"


def test_ensure_tavily_interactive_input_saves_env(isolated_state, monkeypatch):
    """interactive + 유효 입력 → .env 저장 + configured."""
    inputs = iter(["my-tavily-key"])
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: next(inputs))
    state = setup_wizard._default_state()
    setup_wizard._ensure_tavily(state, mode="interactive")
    assert state["tavily"]["decision"] == "configured"
    assert os.environ.get("TAVILY_API_KEY") == "my-tavily-key"
    env_path = isolated_state / ".env"
    assert env_path.is_file()
    assert "TAVILY_API_KEY=my-tavily-key" in env_path.read_text()


def test_ensure_tavily_skip_reconfirm_yes(isolated_state, monkeypatch):
    """interactive + 빈 입력 → 재확인 y → decision=skipped."""
    inputs = iter(["", "y"])
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: next(inputs))
    state = setup_wizard._default_state()
    setup_wizard._ensure_tavily(state, mode="interactive")
    assert state["tavily"]["decision"] == "skipped"


def test_ensure_tavily_skip_reconfirm_no_loop(isolated_state, monkeypatch):
    """interactive + 빈 입력 → 재확인 아무값 → 루프 복귀 → 이번엔 키 입력 → configured."""
    inputs = iter(["", "n", "second-key"])
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: next(inputs))
    state = setup_wizard._default_state()
    setup_wizard._ensure_tavily(state, mode="interactive")
    assert state["tavily"]["decision"] == "configured"
    assert os.environ.get("TAVILY_API_KEY") == "second-key"


def test_ensure_tavily_noninteractive_mode(isolated_state, capsys):
    """noninteractive: 경고박스만, decision 건드리지 않음 (pending 유지)."""
    state = setup_wizard._default_state()
    setup_wizard._ensure_tavily(state, mode="noninteractive")
    out = capsys.readouterr().out
    assert "TAVILY_API_KEY 미설정" in out
    assert state["tavily"]["decision"] == "pending"


# ═══════════════════════════════════════════════════════════════════════════
# 6~11. NotebookLM 플로우
# ═══════════════════════════════════════════════════════════════════════════

def test_ensure_notebooklm_module_missing_in_source_mode(isolated_state, monkeypatch):
    """nlm 모듈 없음 → decision=skipped + last_login_error 기록."""
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name: None if name == "nlm" else mock.DEFAULT,
    )
    state = setup_wizard._default_state()
    setup_wizard._ensure_notebooklm(state, mode="noninteractive")
    assert state["notebooklm"]["decision"] == "skipped"
    assert "nlm module not found" in (state["notebooklm"]["last_login_error"] or "")


def test_ensure_notebooklm_chrome_missing_branch(isolated_state, monkeypatch):
    """nlm OK + Chrome 미설치 + noninteractive → decision=chrome_missing."""
    import importlib.util as _u
    monkeypatch.setattr(_u, "find_spec", lambda name: object() if name == "nlm" else None)
    monkeypatch.setattr(setup_wizard, "_check_chrome_installed", lambda: False)
    state = setup_wizard._default_state()
    setup_wizard._ensure_notebooklm(state, mode="noninteractive")
    assert state["notebooklm"]["decision"] == "chrome_missing"


def test_ensure_notebooklm_auth_status_parsing_not_authenticated(monkeypatch):
    """exit code 2 → not_authenticated (Phase 0.5 실측)."""
    fake = subprocess.CompletedProcess(
        args=[], returncode=2,
        stdout="✗ Not authenticated\n  Profile not found: default\n",
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake)
    assert setup_wizard._check_notebooklm_auth("default") == "not_authenticated"


def test_ensure_notebooklm_auth_status_parsing_success(monkeypatch):
    """exit code 0 + ✓ Authenticated → logged_in."""
    fake = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout="✓ Authenticated\n  Notebooks accessible: 3\n",
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake)
    assert setup_wizard._check_notebooklm_auth("default") == "logged_in"


def test_ensure_notebooklm_login_subprocess_mock_success(monkeypatch):
    """nlm login 성공 (Successfully authenticated) → (True, 'ok')."""
    fake = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout="✓ Successfully authenticated as test@example.com\n",
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake)
    ok, msg = setup_wizard._run_notebooklm_login("default")
    assert ok is True and msg == "ok"


def test_ensure_notebooklm_login_failure_retry_then_skip(isolated_state, monkeypatch):
    """noninteractive + auth=not_authenticated → decision=skipped (Medium 미진입)."""
    import importlib.util as _u
    monkeypatch.setattr(_u, "find_spec", lambda name: object() if name == "nlm" else None)
    monkeypatch.setattr(setup_wizard, "_check_chrome_installed", lambda: True)
    monkeypatch.setattr(setup_wizard, "_check_notebooklm_auth", lambda profile="default": "not_authenticated")
    state = setup_wizard._default_state()
    setup_wizard._ensure_notebooklm(state, mode="noninteractive")
    assert state["notebooklm"]["decision"] == "skipped"


# ═══════════════════════════════════════════════════════════════════════════
# 12~15. state 파일 I/O (atomic / schema / filelock)
# ═══════════════════════════════════════════════════════════════════════════

def test_setup_state_atomic_write_crash_simulation(isolated_state, monkeypatch):
    """_atomic_write 실패 시 tmp 정리 + 원본 파일 무손상."""
    # 정상 파일 먼저 저장
    state = setup_wizard._default_state()
    state["tavily"]["decision"] = "configured"
    setup_wizard._save_setup_state(state)
    original = (isolated_state / ".af_setup_state.json").read_text()

    # 다음 쓰기 시 json.dump가 중간에 실패하도록 강제
    orig_dump = json.dump

    def _boom(*a, **kw):
        raise IOError("simulated disk failure mid-write")

    monkeypatch.setattr(json, "dump", _boom)
    # 실패는 stderr 경고로만 흡수되므로 예외 없음 (파이프라인 블록 금지)
    broken_state = setup_wizard._default_state()
    broken_state["tavily"]["decision"] = "skipped"
    setup_wizard._save_setup_state(broken_state)

    monkeypatch.setattr(json, "dump", orig_dump)
    # 원본 파일 불변 + tmp 잔존 없음
    assert (isolated_state / ".af_setup_state.json").read_text() == original
    leftover = list(isolated_state.glob(".af_setup_state.*.tmp"))
    assert leftover == []


def test_setup_state_schema_v1_to_v2_migration(isolated_state):
    """v1 파일 → _load_setup_state가 schema_version=2로 마이그레이션 + 신규 필드 채움."""
    v1 = {
        "schema_version": 1,
        "tavily": {"decision": "configured"},
        "notebooklm": {"decision": "logged_in", "profile": "default"},
    }
    _write_state(isolated_state, v1)
    loaded = setup_wizard._load_setup_state()
    assert loaded["schema_version"] == 2
    assert loaded["notebooklm"]["archive_notebook_id"] is None
    assert loaded["notebooklm"]["archive_notebook_title"] == setup_wizard._ARCHIVE_NOTEBOOK_TITLE
    assert loaded["notebooklm"]["archive_possibly_duplicate"] is False


def test_setup_state_schema_corrupted_recovery(isolated_state):
    """깨진 JSON → _default_state로 복구 (예외 전파 없음)."""
    (isolated_state / ".af_setup_state.json").write_text("{not json}", encoding="utf-8")
    loaded = setup_wizard._load_setup_state()
    assert loaded == setup_wizard._default_state()


def test_setup_state_filelock_contention(isolated_state, monkeypatch):
    """filelock 타임아웃/미설치 분기에서도 _default_state 반환 + 예외 없음."""
    if not setup_wizard._HAS_FILELOCK:
        pytest.skip("filelock 미설치 환경 — 경합 테스트 스킵")

    # 실제 락을 선점해 timeout=5초 내 획득 실패하도록 만든다
    from filelock import FileLock
    lock_path = str(isolated_state / ".af_setup_state.json.lock")
    state = setup_wizard._default_state()
    state["tavily"]["decision"] = "configured"
    setup_wizard._save_setup_state(state)  # 파일 존재 상태로

    holder = FileLock(lock_path)
    holder.acquire()
    try:
        # load 경로: Timeout 발생 → _default_state() 반환 (예외 없이)
        loaded = setup_wizard._load_setup_state()
        assert loaded == setup_wizard._default_state()
    finally:
        holder.release()


# ═══════════════════════════════════════════════════════════════════════════
# 16~19. run_factory_cli STAGE 1 gate
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def no_side_effects(monkeypatch):
    """STAGE 1 핸들러가 실제로 subprocess/파이프라인을 건드리지 않도록 싹 mock."""
    import run_factory_cli as rfc
    # dispatch에 등록된 핸들러를 전부 기록용 람다로 교체
    fake_dispatch = {k: mock.MagicMock() for k in rfc._STAGE1_DISPATCH}
    monkeypatch.setattr(rfc, "_STAGE1_DISPATCH", fake_dispatch)
    # setup gate와 기본 launch 경로도 mock
    monkeypatch.setattr(rfc, "_run_setup_gate", mock.MagicMock())
    if hasattr(rfc, "_launch_interactive_mode"):
        monkeypatch.setattr(rfc, "_launch_interactive_mode", mock.MagicMock())
    return rfc, fake_dispatch


def test_setup_gate_skips_setup_subcommand(no_side_effects):
    """argv=['setup'] → STAGE 1 분기, setup gate 호출되지 않음."""
    rfc, fake = no_side_effects
    rfc.main(argv=["setup"])
    assert fake["setup"].called
    assert not rfc._run_setup_gate.called


def test_setup_gate_skips_nlm_internal_subcommand(no_side_effects):
    """argv=['__nlm','auth','status'] → __nlm 즉시 분기."""
    rfc, fake = no_side_effects
    rfc.main(argv=["__nlm", "auth", "status"])
    assert fake["__nlm"].called
    # 전달된 rest가 ['auth','status']인지 확인
    fake["__nlm"].assert_called_once_with(["auth", "status"])
    assert not rfc._run_setup_gate.called


def test_setup_gate_skips_worker_subcommand(no_side_effects):
    """argv=['worker','--task-file','x'] → worker 즉시 분기."""
    rfc, fake = no_side_effects
    rfc.main(argv=["worker", "--task-file", "x"])
    assert fake["worker"].called
    fake["worker"].assert_called_once_with(["--task-file", "x"])
    assert not rfc._run_setup_gate.called


def test_setup_gate_skips_version_flag(no_side_effects, capsys):
    """argv=['--version'] → setup gate 미호출 + 'af <ver>' 출력 (B3 회귀 방지).

    구조: gate가 parse_args() 뒤로 이동했으므로 argparse action='version'이
    SystemExit(0)을 raise하는 시점에 gate는 아직 호출되지 않았다.
    """
    rfc, _fake = no_side_effects
    with pytest.raises(SystemExit) as exc:
        rfc.main(argv=["--version"])
    assert exc.value.code == 0
    assert not rfc._run_setup_gate.called
    # cross-review Q6: stdout에 버전 문자열 출력 단언
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "af " in combined, f"버전 문자열 미출력: {combined!r}"


def test_setup_gate_skips_invalid_flag(no_side_effects):
    """argv=['--invalid-flag'] → argparse SystemExit(2) + gate 미호출.

    cross-review Q1/Q2 ACCEPT 회귀 방지: gate를 parse_args() 뒤로 옮긴 결과
    argparse가 거부하는 모든 unknown 플래그가 자동으로 부작용을 차단한다.
    이전 구조에서는 invalid flag도 STAGE 2 gate 통과 → setup_wizard 실행 →
    NotebookLM 아카이브 부작용이 발생하던 클래스 버그 전체 해소 검증.
    """
    rfc, _fake = no_side_effects
    with pytest.raises(SystemExit) as exc:
        rfc.main(argv=["--invalid-flag"])
    assert exc.value.code == 2
    assert not rfc._run_setup_gate.called


def test_setup_gate_skips_help_flag(no_side_effects):
    """argv=['--help'] → argparse SystemExit(0) + gate 미호출."""
    rfc, _fake = no_side_effects
    with pytest.raises(SystemExit) as exc:
        rfc.main(argv=["--help"])
    assert exc.value.code == 0
    assert not rfc._run_setup_gate.called


def test_is_meta_arg_matches_help_and_version():
    """_is_meta_arg: --help/-h/--version/-V 전부 매칭, 그 외는 False."""
    import run_factory_cli as rfc
    assert rfc._is_meta_arg(["--help"]) is True
    assert rfc._is_meta_arg(["-h"]) is True
    assert rfc._is_meta_arg(["--version"]) is True
    assert rfc._is_meta_arg(["-V"]) is True
    assert rfc._is_meta_arg(["--fsa"]) is False
    assert rfc._is_meta_arg([]) is False
    # _is_help_arg는 version을 포함하지 않아야 한다 (STAGE 1 서브커맨드 가드 분리)
    assert rfc._is_help_arg(["--version"]) is False
    assert rfc._is_help_arg(["--help"]) is True
    # cross-review Q5 (DRY): _META_FLAGS = _HELP_FLAGS + ("--version", "-V")
    assert set(rfc._HELP_FLAGS).issubset(set(rfc._META_FLAGS))


def test_invoke_nlm_app_standalone_mode_false(monkeypatch):
    """_invoke_nlm_app: standalone_mode=False + sys.argv 복원 + SystemExit 차단."""
    import run_factory_cli as rfc

    captured = {}

    def fake_app(args, standalone_mode=True):
        captured["args"] = args
        captured["standalone_mode"] = standalone_mode
        captured["argv_during"] = list(sys.argv)
        # standalone_mode=False라면 SystemExit 대신 int/None 반환 가정
        return 0

    fake_module = mock.MagicMock()
    fake_module.app = fake_app
    monkeypatch.setitem(sys.modules, "nlm", mock.MagicMock())
    monkeypatch.setitem(sys.modules, "nlm.cli", mock.MagicMock())
    monkeypatch.setitem(sys.modules, "nlm.cli.main", fake_module)

    original_argv = list(sys.argv)
    rc = rfc._invoke_nlm_app(["auth", "status"])

    assert rc == 0
    assert captured["standalone_mode"] is False
    assert captured["args"] == ["auth", "status"]
    assert captured["argv_during"] == ["nlm", "auth", "status"]
    # 호출 후 sys.argv 완전 복원
    assert sys.argv == original_argv


# ═══════════════════════════════════════════════════════════════════════════
# 20. _find_or_create_archive_notebook UUID 파싱
# ═══════════════════════════════════════════════════════════════════════════

def test_find_or_create_archive_notebook_parses_uuid(monkeypatch):
    """list=[] → create 호출 → 'ID: <uuid>' 파싱 성공."""
    calls = []
    uuid_str = "03662da6-f29e-43aa-b403-79f41b728cf4"

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if "list" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="[]", stderr="")
        if "create" in cmd:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0,
                stdout=f"✓ Created notebook: Agent Factory Archive\n  ID: {uuid_str}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    nb_id, reason = setup_wizard._find_or_create_archive_notebook(
        profile="default", title="Agent Factory Archive", interactive=False,
    )
    assert nb_id == uuid_str
    assert reason == "created_new"
    # list 먼저 → create 순서 확인
    assert any("list" in c for c in calls[:1])
    assert any("create" in c for c in calls)

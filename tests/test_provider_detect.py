"""tests/test_provider_detect.py — core.provider_detect 단위 테스트 (T01~T12)."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import core.provider_detect as pd
from core.provider_detect import ProviderProbeResult, ProviderState, detect_provider_states


# ──────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """각 테스트마다 캐시를 tmp 디렉토리로 격리."""
    cache_file = tmp_path / ".af" / "provider_cache.json"
    monkeypatch.setenv("AF_HOME", str(tmp_path / ".af"))
    monkeypatch.setenv("AF_PROVIDER_CACHE_TTL", "3600")
    monkeypatch.delenv("AF_SKIP_PROVIDER", raising=False)
    yield cache_file


@pytest.fixture()
def fresh_cache(tmp_path):
    """신선한 캐시 파일을 미리 써두는 픽스처."""
    from datetime import datetime, timezone

    cache_dir = tmp_path / ".af"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "provider_cache.json"
    now = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    data = {
        "version": 1,
        "ts": now,
        "ttl_sec": 3600,
        "states": {
            "claude_cli": {"state": "available", "checked_at": now, "rtt_ms": 100, "stderr_excerpt": ""},
            "codex_cli": {"state": "available", "checked_at": now, "rtt_ms": 200, "stderr_excerpt": ""},
            "gemini_cli": {"state": "not_installed", "checked_at": now, "rtt_ms": 0, "stderr_excerpt": ""},
        },
    }
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    return cache_file


# ──────────────────────────────────────────
# T01: 미설치 → NOT_INSTALLED, ping 없음
# ──────────────────────────────────────────

def test_t01_not_installed_no_ping(monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: [])

    with patch("subprocess.run") as mock_run:
        results = detect_provider_states(
            providers=["codex_cli"],
            use_cache=False,
        )

    assert results["codex_cli"].state == ProviderState.NOT_INSTALLED
    mock_run.assert_not_called()


# ──────────────────────────────────────────
# T02: 설치 + ping exit 0 → AVAILABLE, rtt_ms > 0
# ──────────────────────────────────────────

def test_t02_installed_ping_ok(monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        results = detect_provider_states(providers=["codex_cli"], use_cache=False)

    r = results["codex_cli"]
    assert r.state == ProviderState.AVAILABLE
    assert r.rtt_ms >= 0


# ──────────────────────────────────────────
# T03: 설치 + ping exit 1 + stderr "not authenticated" → AUTH_EXPIRED
# ──────────────────────────────────────────

def test_t03_ping_auth_fail(monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "Error: not authenticated. Run `codex login`."

    with patch("subprocess.run", return_value=mock_proc):
        results = detect_provider_states(providers=["codex_cli"], use_cache=False)

    r = results["codex_cli"]
    assert r.state == ProviderState.AUTH_EXPIRED
    assert "not authenticated" in r.stderr_excerpt


# ──────────────────────────────────────────
# T04: 설치 + ping timeout → AUTH_EXPIRED, "timeout" in stderr_excerpt
# ──────────────────────────────────────────

def test_t04_ping_timeout(monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=5)):
        results = detect_provider_states(providers=["codex_cli"], use_cache=False)

    r = results["codex_cli"]
    assert r.state == ProviderState.AUTH_EXPIRED
    assert "timeout" in r.stderr_excerpt


# ──────────────────────────────────────────
# T05: 신선 캐시 + use_cache=True → ping 없음
# ──────────────────────────────────────────

def test_t05_fresh_cache_no_ping(fresh_cache, monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    with patch("subprocess.run") as mock_run:
        results = detect_provider_states(
            providers=["codex_cli"],
            use_cache=True,
        )

    assert results["codex_cli"].state == ProviderState.AVAILABLE
    mock_run.assert_not_called()


# ──────────────────────────────────────────
# T06: 만료 캐시 → ping 재호출, 캐시 갱신
# ──────────────────────────────────────────

def test_t06_expired_cache_re_ping(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    cache_dir = tmp_path / ".af"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "provider_cache.json"
    old_ts = "2000-01-01T00:00:00+00:00"
    data = {
        "version": 1,
        "ts": old_ts,
        "ttl_sec": 3600,
        "states": {
            "codex_cli": {"state": "available", "checked_at": old_ts, "rtt_ms": 50, "stderr_excerpt": ""},
        },
    }
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        results = detect_provider_states(providers=["codex_cli"], use_cache=True)

    assert results["codex_cli"].state == ProviderState.AVAILABLE
    mock_run.assert_called_once()


# ──────────────────────────────────────────
# T07: force_refresh=True → 신선 캐시여도 ping 호출
# ──────────────────────────────────────────

def test_t07_force_refresh_ignores_fresh_cache(fresh_cache, monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        results = detect_provider_states(
            providers=["codex_cli"],
            force_refresh=True,
        )

    assert results["codex_cli"].state == ProviderState.AVAILABLE
    mock_run.assert_called_once()


# ──────────────────────────────────────────
# T08: AF_SKIP_PROVIDER=codex → codex_cli=NOT_INSTALLED
# ──────────────────────────────────────────

def test_t08_skip_provider_masks_as_not_installed(monkeypatch):
    monkeypatch.setenv("AF_SKIP_PROVIDER", "codex_cli")
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli", "gemini_cli"])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        results = detect_provider_states(
            providers=["codex_cli", "gemini_cli"],
            use_cache=False,
        )

    # codex_cli은 skip → NOT_INSTALLED, gemini_cli은 정상 probe
    assert results["codex_cli"].state == ProviderState.NOT_INSTALLED
    assert results["gemini_cli"].state == ProviderState.AVAILABLE
    # gemini_cli만 ping 호출 (codex_cli는 skip이라 ping 없음)
    assert mock_run.call_count == 1


# ──────────────────────────────────────────
# T08b: AF_SKIP_PROVIDER + use_cache=True → 캐시에 NOT_INSTALLED 오염 없음
# ──────────────────────────────────────────

def test_t08b_skip_does_not_pollute_cache(monkeypatch):
    """skip provider는 캐시에 저장되지 않아야 한다 (§4.3 invariant)."""
    monkeypatch.setenv("AF_SKIP_PROVIDER", "codex_cli")
    # codex_cli가 설치돼 있더라도 skip이므로 probe 안 함
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli", "gemini_cli"])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        results = detect_provider_states(
            providers=["codex_cli", "gemini_cli"],
            use_cache=True,
        )

    # caller 반환: codex_cli는 NOT_INSTALLED (skip 마스킹)
    assert results["codex_cli"].state == ProviderState.NOT_INSTALLED
    # gemini_cli는 정상 AVAILABLE
    assert results["gemini_cli"].state == ProviderState.AVAILABLE

    # 캐시 파일에 codex_cli가 없어야 함 (skip → 캐시 오염 금지)
    cache_file = pd._cache_path()
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_states = data.get("states", {})
        assert "codex_cli" not in cached_states, "skip provider가 캐시에 저장되면 §4.3 위반"
        # gemini_cli는 캐시에 있어야 함
        assert "gemini_cli" in cached_states


# ──────────────────────────────────────────
# T09: AF_SKIP_PROVIDER 별칭 정규화
# ──────────────────────────────────────────

@pytest.mark.parametrize("alias", ["codex", "CODEX", "Codex_CLI", "codex_cli"])
def test_t09_skip_provider_alias_normalization(alias, monkeypatch):
    monkeypatch.setenv("AF_SKIP_PROVIDER", alias)
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    with patch("subprocess.run") as mock_run:
        results = detect_provider_states(providers=["codex_cli"], use_cache=False)

    assert results["codex_cli"].state == ProviderState.NOT_INSTALLED
    mock_run.assert_not_called()


# ──────────────────────────────────────────
# T10: 캐시 파일 손상 → 무시하고 새로 ping + 다시 저장
# ──────────────────────────────────────────

def test_t10_corrupt_cache_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    cache_dir = tmp_path / ".af"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "provider_cache.json"
    cache_file.write_text("NOT_VALID_JSON{{{", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        results = detect_provider_states(providers=["codex_cli"], use_cache=True)

    assert results["codex_cli"].state == ProviderState.AVAILABLE
    mock_run.assert_called_once()
    # 캐시가 갱신됐는지 확인
    updated = json.loads(cache_file.read_text(encoding="utf-8"))
    assert updated["states"]["codex_cli"]["state"] == "available"


# ──────────────────────────────────────────
# T10b: JSON 유효하지만 state 값 손상 → 해당 항목 재probe
# ──────────────────────────────────────────

def test_t10b_partial_corrupt_state_re_probed(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    cache_dir = tmp_path / ".af"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "provider_cache.json"
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    # state 값이 enum에 없는 값으로 손상
    data = {
        "version": 1,
        "ts": now,
        "ttl_sec": 3600,
        "states": {
            "codex_cli": {"state": "INVALID_STATE_VALUE", "checked_at": now, "rtt_ms": 100, "stderr_excerpt": ""},
        },
    }
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        results = detect_provider_states(providers=["codex_cli"], use_cache=True)

    # 손상 항목은 재probe해서 AVAILABLE이어야 함
    assert results["codex_cli"].state == ProviderState.AVAILABLE
    mock_run.assert_called_once()


# ──────────────────────────────────────────
# T11: 캐시 디렉토리 권한 없음 → 메모리 fallback (경고만)
# ──────────────────────────────────────────

def test_t11_cache_write_permission_error(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    # 캐시 파일 쓰기를 OSError로 강제
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    original_write = Path.write_text

    def fail_write(self, *args, **kwargs):
        if "provider_cache" in str(self):
            raise OSError("permission denied (mock)")
        return original_write(self, *args, **kwargs)

    with patch("subprocess.run", return_value=mock_proc):
        with patch.object(Path, "write_text", fail_write):
            # 쓰기 실패해도 detect는 정상 결과를 반환해야 함
            results = detect_provider_states(providers=["codex_cli"], use_cache=True)

    assert results["codex_cli"].state == ProviderState.AVAILABLE


# ──────────────────────────────────────────
# T12: 동시 호출 (2 스레드) → 원자 rename으로 깨지지 않음
# ──────────────────────────────────────────

def test_t12_concurrent_cache_writes(monkeypatch):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    errors: list[Exception] = []
    results_list: list[dict] = []

    # patch는 메인 스레드에서 1회만 적용해야 한다 (worker 안에서 적용하면 스레드 간 경쟁 발생).
    with patch("subprocess.run", return_value=mock_proc):
        def worker():
            try:
                r = detect_provider_states(
                    providers=["codex_cli"],
                    use_cache=True,
                    force_refresh=True,
                )
                results_list.append(r)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

    assert not errors, f"Thread errors: {errors}"
    assert len(results_list) == 2
    # 두 스레드 모두 AVAILABLE 결과를 받아야 함
    for r in results_list:
        assert r["codex_cli"].state == ProviderState.AVAILABLE

    # 캐시 파일이 유효한 JSON이어야 함
    cache_file = pd._cache_path()
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert "codex_cli" in data["states"]


# ──────────────────────────────────────────
# 추가: CLI entry point 기본 동작
# ──────────────────────────────────────────

def test_cli_json_output_fan_out_blocked(monkeypatch, capsys):
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli", "gemini_cli"])

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        if "codex" in cmd[0]:
            m.returncode = 0
            m.stderr = ""
        else:
            # gemini auth 실패
            m.returncode = 1
            m.stderr = "Error: auth expired"
        return m

    with patch("subprocess.run", side_effect=fake_run):
        pd._main(["--json", "--exclude-self", "claude_cli"])

    out = capsys.readouterr().out
    data = json.loads(out)
    assert "codex_cli" in data["fan_out"]
    assert "gemini_cli" in data["blocked"]
    assert "claude_cli" not in data["states"]


# ──────────────────────────────────────────
# AGENT_*_CLI_COMMAND env var override 반영
# ──────────────────────────────────────────

def test_cli_command_env_override_used_in_ping(monkeypatch):
    """AGENT_CODEX_CLI_COMMAND가 설정된 경우 해당 실행파일로 ping한다."""
    monkeypatch.setenv("AGENT_CODEX_CLI_COMMAND", "/custom/path/codex")
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: ["codex_cli"])

    called_cmds: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        called_cmds.append(cmd)
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m

    with patch("subprocess.run", side_effect=fake_run):
        results = detect_provider_states(providers=["codex_cli"], use_cache=False)

    assert results["codex_cli"].state == ProviderState.AVAILABLE
    assert len(called_cmds) == 1
    assert called_cmds[0][0] == "/custom/path/codex"


def test_cli_skip_gives_empty_fan_out(monkeypatch, capsys):
    monkeypatch.setenv("AF_SKIP_PROVIDER", "codex_cli,gemini_cli")
    monkeypatch.setattr(pd, "detect_installed_cli_providers", lambda: [])

    with patch("subprocess.run") as mock_run:
        pd._main(["--json", "--exclude-self", "claude_cli"])

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["fan_out"] == []
    assert data["blocked"] == []
    mock_run.assert_not_called()


# ──────────────────────────────────────────
# T13: installed_set이 ThreadPool 전에 1회만 계산됨을 검증
# ──────────────────────────────────────────

def test_t13_installed_set_computed_once_before_threadpool(monkeypatch):
    """detect_installed_cli_providers()는 ThreadPool 시작 전 main thread에서 1회만 호출된다.

    이것이 BLOCK-prep 버그의 핵심 수정: 이전에는 각 worker thread가
    전역 캐시를 직접 호출해서 race condition이 발생했다.
    """
    # Lock으로 카운터 보호 — 버그 재현 시 worker thread에서 동시에 += 1이 발생하면
    # GIL 비의존 환경이나 read-modify-write 경합으로 count가 낮게 집계될 수 있다.
    call_lock = threading.Lock()
    call_count = {"n": 0}

    def counting_detect():
        with call_lock:
            call_count["n"] += 1
            n = call_count["n"]
        # 두 번째 이후 호출(worker thread 내부)이 있었다면 빈 목록 반환해서 버그 재현
        if n == 1:
            return ["claude_cli", "codex_cli", "gemini_cli"]
        return []

    monkeypatch.setattr(pd, "detect_installed_cli_providers", counting_detect)

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        results = detect_provider_states(
            providers=["claude_cli", "codex_cli", "gemini_cli"],
            use_cache=False,
        )

    # 수정 후: 1회 호출만 발생해야 한다 (pre-computed installed_set)
    assert call_count["n"] == 1, (
        f"detect_installed_cli_providers()가 {call_count['n']}회 호출됨 — "
        "ThreadPool worker 내부에서 재호출되는 race condition이 있다"
    )
    # 모든 provider가 AVAILABLE이어야 한다 (installed_set이 올바르게 전달됨)
    for pid in ["claude_cli", "codex_cli", "gemini_cli"]:
        assert results[pid].state == ProviderState.AVAILABLE, (
            f"{pid}가 AVAILABLE이어야 하지만 {results[pid].state} — "
            "installed_set race condition으로 NOT_INSTALLED 오탐 발생"
        )


# ──────────────────────────────────────────
# T14: 멀티스레드 concurrent detect_provider_states — 결과 일관성 검증
# ──────────────────────────────────────────

def test_t14_concurrent_detect_provider_states(monkeypatch):
    """여러 스레드가 동시에 detect_provider_states()를 호출해도 결과가 일관된다."""
    monkeypatch.setattr(
        pd, "detect_installed_cli_providers", lambda: ["codex_cli", "gemini_cli"]
    )

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        if "codex" in cmd[0]:
            m.returncode = 0
            m.stderr = ""
        else:  # gemini
            m.returncode = 1
            m.stderr = "Error: auth expired"
        return m

    errors: list[Exception] = []
    results_list: list[dict] = []

    # patch는 메인 스레드에서 한 번만 적용해야 한다.
    # 각 worker 안에서 patch하면 스레드 간 패치가 경쟁해서 race condition 발생.
    with patch("subprocess.run", side_effect=fake_run):
        def worker():
            try:
                r = detect_provider_states(
                    providers=["codex_cli", "gemini_cli"],
                    use_cache=False,
                )
                results_list.append(r)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

    assert not errors, f"Thread errors: {errors}"
    assert len(results_list) == 6
    for r in results_list:
        assert r["codex_cli"].state == ProviderState.AVAILABLE
        assert r["gemini_cli"].state == ProviderState.AUTH_EXPIRED

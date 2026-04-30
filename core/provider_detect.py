"""Provider 3-state 감지 + 1h 디스크 캐시 + AF_SKIP_PROVIDER 처리.

CLI entry: python -m core.provider_detect --json [--exclude-self claude_cli]
"""
from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from core.providers.registry import CLI_PROVIDER_IDS, detect_installed_cli_providers

log = logging.getLogger(__name__)

_DEFAULT_TTL_SEC = 3600   # 1 hour
_PING_TIMEOUT_SEC = 30    # codex/gemini는 LLM API 호출이 5~15초 소요
_CACHE_VERSION = 1

# Provider alias → canonical ID
_ALIAS_MAP: dict[str, str] = {
    "claude": "claude_cli",
    "claude_cli": "claude_cli",
    "gemini": "gemini_cli",
    "gemini_cli": "gemini_cli",
    "codex": "codex_cli",
    "codex_cli": "codex_cli",
}

# 기본 실행파일 이름 (AGENT_*_CLI_COMMAND env var로 override 가능)
_PING_EXEC_ENV: dict[str, str] = {
    "claude_cli": "AGENT_CLAUDE_CLI_COMMAND",
    "gemini_cli": "AGENT_GEMINI_CLI_COMMAND",
    "codex_cli": "AGENT_CODEX_CLI_COMMAND",
}
_PING_DEFAULT_EXEC: dict[str, str] = {
    "claude_cli": "claude",
    "gemini_cli": "gemini",
    "codex_cli": "codex",
}
# 실행파일 다음에 오는 auth ping 전용 인자 (실행파일은 _resolve_ping_cmd가 결정)
_PING_SUFFIX: dict[str, list[str]] = {
    "claude_cli": ["-p", "ok", "--output-format", "text"],
    "gemini_cli": ["-p", "ok"],
    "codex_cli": ["exec", "-s", "read-only", "ok"],
}


def _resolve_ping_cmd(provider_id: str) -> list[str] | None:
    """AGENT_*_CLI_COMMAND env var override를 반영한 auth ping 명령 반환."""
    suffix = _PING_SUFFIX.get(provider_id)
    if suffix is None:
        return None
    env_var = _PING_EXEC_ENV.get(provider_id, "")
    override = os.getenv(env_var, "").strip() if env_var else ""
    if override:
        # Windows에서 shlex posix=False는 따옴표를 제거하지 않음.
        # 백슬래시를 2중화 후 posix=True로 파싱하면 따옴표 제거와 이스케이프 처리가 모두 동작.
        # 예: "C:\Program Files\codex.cmd" → C:\Program Files\codex.cmd
        _src = override.replace("\\", "\\\\") if os.name == "nt" else override
        try:
            parts = shlex.split(_src, posix=True)
            executable = parts[0] if parts else ""
        except ValueError:
            executable = override.split()[0]
    else:
        executable = _PING_DEFAULT_EXEC.get(provider_id, provider_id)
    return [executable] + suffix


class ProviderState(str, Enum):
    AVAILABLE     = "available"
    AUTH_EXPIRED  = "auth_expired"
    NOT_INSTALLED = "not_installed"


@dataclass(frozen=True)
class ProviderProbeResult:
    provider_id: str
    state: ProviderState
    checked_at: str         # ISO8601 UTC
    rtt_ms: int = 0
    stderr_excerpt: str = ""


# ──────────────────────────────────────────
# 캐시 유틸
# ──────────────────────────────────────────

_cache_lock = threading.Lock()


def _cache_path() -> Path:
    af_home = os.getenv("AF_HOME", "").strip()
    base = Path(af_home) if af_home else Path.home() / ".af"
    return base / "provider_cache.json"


def _ttl_sec() -> int:
    raw = os.getenv("AF_PROVIDER_CACHE_TTL", "").strip()
    try:
        return max(1, int(raw)) if raw else _DEFAULT_TTL_SEC
    except ValueError:
        return _DEFAULT_TTL_SEC


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _read_cache_raw() -> dict | None:
    try:
        text = _cache_path().read_text(encoding="utf-8")
        data = json.loads(text)
        if data.get("version") != _CACHE_VERSION:
            return None
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_cache_raw(states: dict[str, ProviderProbeResult]) -> None:
    payload = {
        "version": _CACHE_VERSION,
        "ts": _now_iso(),
        "ttl_sec": _ttl_sec(),
        "states": {
            pid: {
                "state": r.state.value,
                "checked_at": r.checked_at,
                "rtt_ms": r.rtt_ms,
                "stderr_excerpt": r.stderr_excerpt,
            }
            for pid, r in states.items()
        },
    }
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("provider_detect: cache write failed (%s) — memory only", exc)


def _cache_fresh(data: dict) -> bool:
    try:
        ts = datetime.fromisoformat(data["ts"])
        ttl = data.get("ttl_sec", _DEFAULT_TTL_SEC)
        return (datetime.now(tz=timezone.utc) - ts).total_seconds() < ttl
    except (KeyError, ValueError, TypeError):
        return False


def _result_from_dict(pid: str, s: dict) -> ProviderProbeResult:
    return ProviderProbeResult(
        provider_id=pid,
        state=ProviderState(s["state"]),
        checked_at=s.get("checked_at", ""),
        rtt_ms=s.get("rtt_ms", 0),
        stderr_excerpt=s.get("stderr_excerpt", ""),
    )


# ──────────────────────────────────────────
# AF_SKIP_PROVIDER 파싱
# ──────────────────────────────────────────

def _parse_skip_providers() -> frozenset[str]:
    raw = os.getenv("AF_SKIP_PROVIDER", "")
    result: set[str] = set()
    for part in raw.split(","):
        part = part.strip().lower()
        if not part:
            continue
        normalized = _ALIAS_MAP.get(part)
        if normalized:
            result.add(normalized)
        else:
            log.warning("provider_detect: unknown AF_SKIP_PROVIDER entry %r — ignored", part)
    return frozenset(result)


# ──────────────────────────────────────────
# 프로브 (설치 확인 → auth ping)
# ──────────────────────────────────────────

def _ping_one(provider_id: str) -> ProviderProbeResult:
    checked_at = _now_iso()
    cmd = _resolve_ping_cmd(provider_id)
    if not cmd:
        return ProviderProbeResult(
            provider_id=provider_id,
            state=ProviderState.NOT_INSTALLED,
            checked_at=checked_at,
        )
    # Windows에서 npm 글로벌 실행파일은 .cmd 배치 스크립트이므로 shell=True 필요.
    # shell=True 시 list 전달은 cmd.exe /c 경유 시 인자 손실 위험 → list2cmdline으로 명시 변환.
    # stdin=DEVNULL: 일부 CLI가 추가 입력을 기다리며 hang하는 것을 방지.
    _resolved = shutil.which(cmd[0]) or ""
    _shell = os.name == "nt" and _resolved.lower().endswith((".cmd", ".bat", ".com"))
    _run_cmd: list[str] | str = subprocess.list2cmdline(cmd) if _shell else cmd
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            _run_cmd,
            capture_output=True,
            text=True,
            timeout=_PING_TIMEOUT_SEC,
            stdin=subprocess.DEVNULL,
            shell=_shell,
        )
        rtt_ms = int((time.monotonic() - t0) * 1000)
        if proc.returncode == 0:
            return ProviderProbeResult(
                provider_id=provider_id,
                state=ProviderState.AVAILABLE,
                checked_at=checked_at,
                rtt_ms=rtt_ms,
            )
        return ProviderProbeResult(
            provider_id=provider_id,
            state=ProviderState.AUTH_EXPIRED,
            checked_at=checked_at,
            stderr_excerpt=(proc.stderr or "")[:1024],
        )
    except subprocess.TimeoutExpired:
        return ProviderProbeResult(
            provider_id=provider_id,
            state=ProviderState.AUTH_EXPIRED,
            checked_at=checked_at,
            stderr_excerpt="timeout",
        )
    except FileNotFoundError:
        return ProviderProbeResult(
            provider_id=provider_id,
            state=ProviderState.NOT_INSTALLED,
            checked_at=checked_at,
        )


def _probe_one(provider_id: str, installed: frozenset[str]) -> ProviderProbeResult:
    """설치 확인 → auth ping. skip 판단은 호출 측이 담당.

    installed는 ThreadPool 시작 전 main thread에서 1회 계산된 frozenset을 받는다.
    ThreadPool worker 안에서 전역 캐시(detect_installed_cli_providers)를 재호출하지 않으므로 race-free.
    """
    checked_at = _now_iso()

    if provider_id not in installed:
        return ProviderProbeResult(
            provider_id=provider_id,
            state=ProviderState.NOT_INSTALLED,
            checked_at=checked_at,
        )

    return _ping_one(provider_id)


# ──────────────────────────────────────────
# Public API
# ──────────────────────────────────────────

def detect_provider_states(
    providers: list[str] | None = None,
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> dict[str, ProviderProbeResult]:
    """3-state로 프로바이더 상태를 감지한다.

    - providers=None → CLI_PROVIDER_IDS 전체
    - use_cache=True + 신선 캐시 → ping 없이 캐시 반환
    - force_refresh=True → 캐시 무시하고 새로 ping
    - AF_SKIP_PROVIDER: 해당 provider를 NOT_INSTALLED로 마스킹 (캐시는 실제 상태 보존)
    """
    target_ids: list[str] = list(providers or CLI_PROVIDER_IDS)
    skip = _parse_skip_providers()
    results: dict[str, ProviderProbeResult] = {}
    to_probe: list[str] = []

    if use_cache and not force_refresh:
        with _cache_lock:
            data = _read_cache_raw()
        if data and _cache_fresh(data):
            cached = data.get("states", {})
            for pid in target_ids:
                if pid in cached:
                    try:
                        r = _result_from_dict(pid, cached[pid])
                    except (KeyError, ValueError):
                        # 부분 손상 항목은 무시하고 새로 probe
                        to_probe.append(pid)
                        continue
                    # skip 마스킹은 캐시 조회 후 적용
                    if pid in skip:
                        r = ProviderProbeResult(
                            provider_id=pid,
                            state=ProviderState.NOT_INSTALLED,
                            checked_at=r.checked_at,
                        )
                    results[pid] = r
                else:
                    to_probe.append(pid)
        else:
            to_probe = list(target_ids)
    else:
        to_probe = list(target_ids)

    if to_probe:
        # skip provider는 probe하지 않고 즉시 NOT_INSTALLED 처리 (캐시에 기록 안 함)
        real_probe = [pid for pid in to_probe if pid not in skip]
        skip_probe = [pid for pid in to_probe if pid in skip]

        # 설치된 provider 목록을 ThreadPool 시작 전 main thread에서 1회 계산.
        # worker 안에서 전역 캐시를 재호출하면 race condition 가능성이 있으므로
        # immutable frozenset으로 만들어 각 worker에 전달한다.
        installed_set = frozenset(detect_installed_cli_providers())

        probed_real: dict[str, ProviderProbeResult] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_probe_one, pid, installed_set): pid for pid in real_probe}
            for fut in as_completed(futures):
                pid = futures[fut]
                try:
                    probed_real[pid] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    log.warning("provider_detect: probe error for %s: %s", pid, exc)
                    probed_real[pid] = ProviderProbeResult(
                        provider_id=pid,
                        state=ProviderState.NOT_INSTALLED,
                        checked_at=_now_iso(),
                    )

        # 캐시에는 실제 상태(skip 제외)만 저장 — skip unset 시 즉시 원상복귀 보장
        if use_cache and probed_real:
            with _cache_lock:
                existing = _read_cache_raw()
                merged: dict[str, ProviderProbeResult] = {}
                if existing and existing.get("states"):
                    for pid, s in existing["states"].items():
                        try:
                            merged[pid] = _result_from_dict(pid, s)
                        except (KeyError, ValueError):
                            pass
                merged.update(probed_real)
                _write_cache_raw(merged)

        # results 병합: 실제 probe 결과 + skip → NOT_INSTALLED
        results.update(probed_real)
        for pid in skip_probe:
            results[pid] = ProviderProbeResult(
                provider_id=pid,
                state=ProviderState.NOT_INSTALLED,
                checked_at=_now_iso(),
            )

    return results


def invalidate_cache(provider_id: str | None = None) -> None:
    """캐시를 강제 무효화한다. provider_id=None이면 전체 삭제."""
    with _cache_lock:
        if provider_id is None:
            try:
                _cache_path().unlink(missing_ok=True)
            except OSError as exc:
                log.warning("provider_detect: cache delete failed: %s", exc)
        else:
            data = _read_cache_raw()
            if data and "states" in data:
                data["states"].pop(provider_id, None)
                # version 미일치 방지: 다시 version 고정
                data["version"] = _CACHE_VERSION
                path = _cache_path()
                try:
                    tmp = path.with_suffix(".json.tmp")
                    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    os.replace(tmp, path)
                except OSError as exc:
                    log.warning("provider_detect: cache invalidate write failed: %s", exc)


# ──────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────

def _main(argv: list[str] | None = None) -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m core.provider_detect")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument(
        "--exclude-self",
        dest="exclude_self",
        metavar="PROVIDER_ID",
        help="자기 자신 프로바이더 제외 (예: claude_cli)",
    )
    parser.add_argument(
        "--invalidate",
        metavar="ID_OR_ALL",
        help="캐시 항목 무효화 (all 또는 provider_id)",
    )
    parser.add_argument("--force-refresh", action="store_true", help="캐시 무시하고 새로 ping")
    args = parser.parse_args(argv)

    if args.invalidate:
        target = None if args.invalidate == "all" else args.invalidate
        invalidate_cache(target)
        print(f"cache invalidated: {args.invalidate}", file=sys.stderr)
        return

    # exclude_self를 target 목록에서 제거
    skip_ids: set[str] = set()
    if args.exclude_self:
        normalized = _ALIAS_MAP.get(args.exclude_self.lower(), args.exclude_self.lower())
        skip_ids.add(normalized)

    target_ids = [pid for pid in CLI_PROVIDER_IDS if pid not in skip_ids]

    states = detect_provider_states(
        providers=target_ids,
        force_refresh=args.force_refresh,
    )

    fan_out = [pid for pid in target_ids if states[pid].state == ProviderState.AVAILABLE]
    blocked = [pid for pid in target_ids if states[pid].state == ProviderState.AUTH_EXPIRED]

    if args.json:
        out = {
            "states": {pid: r.state.value for pid, r in states.items()},
            "fan_out": fan_out,
            "blocked": blocked,
        }
        print(json.dumps(out))
    else:
        for pid, r in states.items():
            print(f"{pid}: {r.state.value}")
        print(f"fan_out: {fan_out}")
        print(f"blocked: {blocked}")


if __name__ == "__main__":
    _main()

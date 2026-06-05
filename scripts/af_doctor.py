"""af doctor — AF 실행 환경 진단 도구.

기존 API 재사용만. 새 판단 엔진 없음.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["ok", "warn", "fail"]


@dataclass
class DoctorResult:
    name: str
    status: Status
    detail: str
    fix_hint: str = ""


# ---------------------------------------------------------------------------
# 개별 체크 함수 (기존 API 재사용 or 단순 OS 호출)
# ---------------------------------------------------------------------------

def check_python() -> DoctorResult:
    v = sys.version.split()[0]
    return DoctorResult("python", "ok", f"Python {v}")


def check_git() -> DoctorResult:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return DoctorResult("git_repo", "ok", "git repo 감지됨")
        return DoctorResult(
            "git_repo", "fail",
            "git repo가 아닌 경로",
            "af doctor는 git repo 안에서 실행하세요",
        )
    except FileNotFoundError:
        return DoctorResult("git_repo", "fail", "git 미설치", "git을 설치하세요")
    except Exception as exc:
        return DoctorResult("git_repo", "fail", str(exc))


def check_git_dirty() -> DoctorResult:
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return DoctorResult("git_dirty", "warn", "git status 실행 실패")
        changed = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if changed:
            return DoctorResult(
                "git_dirty", "warn",
                f"uncommitted changes {len(changed)}개",
                "git add && git commit",
            )
        return DoctorResult("git_dirty", "ok", "working tree clean")
    except Exception as exc:
        return DoctorResult("git_dirty", "warn", str(exc))


def check_providers(*, fast: bool = False, refresh: bool = False) -> list[DoctorResult]:
    """CLI provider 상태 체크.

    fast=True : 설치 여부만 (shutil.which 수준 캐시 사용)
    refresh   : 캐시 무시하고 실제 auth ping
    기본      : detect_provider_states(use_cache=True)
    """
    if fast:
        try:
            from core.providers.registry import detect_installed_cli_providers
            installed = detect_installed_cli_providers()
            if installed:
                return [DoctorResult(
                    "providers_installed", "ok",
                    f"설치된 provider: {', '.join(installed)}",
                )]
            return [DoctorResult(
                "providers_installed", "warn",
                "설치된 provider 없음",
                "claude/codex/gemini 중 하나 이상 설치 필요",
            )]
        except Exception as exc:
            return [DoctorResult("providers_installed", "fail", str(exc))]

    try:
        from core.provider_detect import detect_provider_states, ProviderState
        states = detect_provider_states(force_refresh=refresh)
        results: list[DoctorResult] = []
        for pid, probe in states.items():
            if probe.state == ProviderState.AVAILABLE:
                results.append(DoctorResult(f"provider_{pid}", "ok", f"{pid}: 인증됨"))
            elif probe.state == ProviderState.AUTH_EXPIRED:
                results.append(DoctorResult(
                    f"provider_{pid}", "warn",
                    f"{pid}: 인증 만료",
                    f"{pid} 재인증 필요",
                ))
            else:
                results.append(DoctorResult(f"provider_{pid}", "warn", f"{pid}: 미설치"))
        return results
    except Exception as exc:
        return [DoctorResult("providers", "fail", str(exc))]


def check_hooks() -> DoctorResult:
    # git config core.hooksPath 우선
    try:
        r = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            hp = r.stdout.strip()
            if hp and Path(hp).is_dir():
                return DoctorResult("hooks", "ok", f"hooksPath: {hp}")
    except Exception:
        pass

    if Path(".githooks").is_dir() and any(Path(".githooks").iterdir()):
        return DoctorResult("hooks", "ok", ".githooks 설치됨")

    return DoctorResult(
        "hooks", "warn",
        ".githooks 미설치",
        "git config core.hooksPath .githooks",
    )


def check_pytest() -> DoctorResult:
    path = shutil.which("pytest")
    if path:
        return DoctorResult("pytest", "ok", f"pytest: {path}")
    return DoctorResult("pytest", "warn", "pytest 미설치", "pip install pytest")


def check_dogfood_root() -> DoctorResult:
    custom = os.environ.get("AF_DOGFOOD_ROOT", "")
    try:
        root = Path(custom) if custom else (Path.home() / ".af-dogfood")
    except (RuntimeError, OSError) as exc:
        return DoctorResult("dogfood_root", "warn", f"home 경로 감지 실패: {exc}")
    if root.exists() and root.is_dir():
        try:
            runs = list(root.iterdir())
        except PermissionError:
            return DoctorResult("dogfood_root", "warn", f"{root} 접근 불가 (권한 없음)")
        return DoctorResult("dogfood_root", "ok", f"{root} ({len(runs)} runs)")
    return DoctorResult(
        "dogfood_root", "warn",
        f"{root} 없음",
        "첫 dogfood run 시 자동 생성됩니다",
    )


# ---------------------------------------------------------------------------
# 집계
# ---------------------------------------------------------------------------

def run_checks(*, fast: bool = False, refresh: bool = False) -> list[DoctorResult]:
    checks: list[DoctorResult] = [
        check_python(),
        check_git(),
        check_git_dirty(),
    ]
    checks.extend(check_providers(fast=fast, refresh=refresh))
    checks.extend([
        check_hooks(),
        check_pytest(),
        check_dogfood_root(),
    ])
    return checks


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------

def format_text(checks: list[DoctorResult]) -> str:
    icons: dict[str, str] = {"ok": "✓", "warn": "!", "fail": "✗"}
    lines: list[str] = []
    for c in checks:
        icon = icons[c.status]
        line = f"  [{icon}] {c.name:<30} {c.detail}"
        if c.fix_hint:
            line += f"\n       → {c.fix_hint}"
        lines.append(line)
    fail_n = sum(1 for c in checks if c.status == "fail")
    warn_n = sum(1 for c in checks if c.status == "warn")
    ok_n = len(checks) - fail_n - warn_n
    lines.append("")
    lines.append(f"  {fail_n} fail  {warn_n} warn  {ok_n} ok")
    return "\n".join(lines)


def format_json(checks: list[DoctorResult]) -> str:
    return json.dumps(
        {
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "detail": c.detail,
                    "fix_hint": c.fix_hint,
                }
                for c in checks
            ],
            "ok_count": sum(1 for c in checks if c.status == "ok"),
            "warn_count": sum(1 for c in checks if c.status == "warn"),
            "fail_count": sum(1 for c in checks if c.status == "fail"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _exit_code(checks: list[DoctorResult], *, strict: bool) -> int:
    if any(c.status == "fail" for c in checks):
        return 1
    if strict and any(c.status == "warn" for c in checks):
        return 1
    return 0


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """진단 실행 후 exit code를 반환한다 (sys.exit은 호출부 책임)."""
    parser = argparse.ArgumentParser(
        prog="af doctor",
        description="AF 실행 환경 진단",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--fast", action="store_true",
        help="provider ping 스킵, 설치 여부만 확인",
    )
    mode.add_argument(
        "--refresh", action="store_true",
        help="캐시 무시하고 실제 auth ping 수행",
    )
    parser.add_argument(
        "--json", dest="json_out", action="store_true",
        help="JSON 출력",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="warn도 exit 1로 처리",
    )
    args = parser.parse_args(argv)

    try:
        checks = run_checks(fast=args.fast, refresh=args.refresh)
    except Exception as exc:
        print(f"[af doctor] 실행 오류: {exc}", file=sys.stderr)
        return 2

    if args.json_out:
        print(format_json(checks))
    else:
        print("af doctor")
        print(format_text(checks))

    return _exit_code(checks, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())

"""af provider — CLI 프로바이더 설치·인증 관리.

사용법:
  af provider status          # 설치·인증 상태 확인
  af provider install         # 미설치 프로바이더 전체 npm 설치
  af provider install claude  # 특정 프로바이더만
  af provider auth            # 미인증 프로바이더 순서대로 인증
  af provider auth gemini     # 특정 프로바이더만
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

_PROVIDER_ORDER = ("claude_cli", "gemini_cli", "codex_cli")

_DISPLAY_NAMES = {
    "claude_cli": "Claude Code",
    "gemini_cli": "Gemini CLI",
    "codex_cli":  "Codex CLI",
}

_INSTALL_PACKAGES = {
    "claude_cli": "@anthropic-ai/claude-code",
    "gemini_cli": "@google/gemini-cli",
    "codex_cli":  "@openai/codex",
}

# 각 CLI의 인증 명령 (리스트 형식, subprocess 직접 전달용)
_AUTH_ARGS = {
    "claude_cli": ("auth", "login"),
    "gemini_cli": ("auth", "login"),
    "codex_cli":  ("login",),
}

# 짧은 이름 → provider_id
_ALIASES: dict[str, str] = {
    "claude": "claude_cli",
    "claude_cli": "claude_cli",
    "gemini": "gemini_cli",
    "gemini_cli": "gemini_cli",
    "codex": "codex_cli",
    "codex_cli": "codex_cli",
}


def _resolve_provider(name: str) -> str | None:
    return _ALIASES.get(str(name).lower().strip())


def _npm_install(package: str) -> int:
    npm = shutil.which("npm")
    if not npm:
        print("  [!] npm 미설치. Node.js를 먼저 설치하세요: https://nodejs.org/", file=sys.stderr)
        return 1
    result = subprocess.run([npm, "install", "-g", package], text=True, encoding="utf-8", errors="replace")
    return result.returncode


def cmd_status(args: argparse.Namespace) -> int:
    from core.providers.registry import detect_installed_cli_providers
    installed = set(detect_installed_cli_providers())

    use_states = False
    states: dict = {}
    if not getattr(args, "fast", False):
        try:
            from core.provider_detect import detect_provider_states
            states = detect_provider_states(force_refresh=getattr(args, "refresh", False))
            use_states = True
        except Exception:
            pass

    print()
    print("  프로바이더 상태")
    print("  " + "-" * 44)
    any_issue = False
    for pid in _PROVIDER_ORDER:
        name = _DISPLAY_NAMES[pid]
        pkg = _INSTALL_PACKAGES[pid]
        auth_args = _AUTH_ARGS[pid]
        if pid not in installed:
            print(f"  [✗] {name:<18} 미설치")
            print(f"       설치: npm install -g {pkg}")
            any_issue = True
        elif use_states and pid in states:
            try:
                from core.provider_detect import ProviderState
                probe = states[pid]
                if probe.state == ProviderState.AVAILABLE:
                    print(f"  [✓] {name:<18} 설치됨·인증됨")
                elif probe.state == ProviderState.AUTH_EXPIRED:
                    exe = pid.split("_")[0]  # claude / gemini / codex
                    print(f"  [!] {name:<18} 인증 만료")
                    print(f"       인증: {exe} {' '.join(auth_args)}")
                    any_issue = True
                else:
                    print(f"  [?] {name:<18} 설치됨 (인증 상태 미확인)")
            except Exception:
                print(f"  [?] {name:<18} 설치됨 (상태 조회 실패)")
        else:
            print(f"  [~] {name:<18} 설치됨 (인증 미확인 / 재확인: af provider status --refresh)")
    print()
    if any_issue:
        print("  미설치/만료 항목은 'af provider install' 또는 'af provider auth'로 해결하세요.")
        print()
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    from core.providers.registry import detect_installed_cli_providers, invalidate_installed_cli_cache

    # 대상 결정
    provider_arg = getattr(args, "provider_name", None)
    if provider_arg:
        pid = _resolve_provider(provider_arg)
        if not pid:
            print(f"[!] 알 수 없는 프로바이더: {provider_arg}", file=sys.stderr)
            print("    사용 가능: claude, gemini, codex", file=sys.stderr)
            return 1
        targets = (pid,)
    else:
        targets = _PROVIDER_ORDER

    installed = set(detect_installed_cli_providers())
    force = getattr(args, "force", False)
    installed_any = False

    print()
    for pid in targets:
        name = _DISPLAY_NAMES[pid]
        pkg = _INSTALL_PACKAGES[pid]
        if pid in installed and not force:
            print(f"  [✓] {name} 이미 설치됨  (재설치: --force)")
            continue
        print(f"  ► {name} 설치 중 (npm install -g {pkg})...")
        rc = _npm_install(pkg)
        if rc == 0:
            print(f"  [✓] {name} 설치 완료")
            installed_any = True
        else:
            print(f"  [✗] {name} 설치 실패 (exit {rc})")
    print()

    if installed_any:
        invalidate_installed_cli_cache()
        print("  설치 후 인증이 필요합니다: af provider auth")
        print()
    return 0


def cmd_auth(args: argparse.Namespace) -> int:
    from core.providers.registry import detect_installed_cli_providers

    provider_arg = getattr(args, "provider_name", None)
    if provider_arg:
        pid = _resolve_provider(provider_arg)
        if not pid:
            print(f"[!] 알 수 없는 프로바이더: {provider_arg}", file=sys.stderr)
            print("    사용 가능: claude, gemini, codex", file=sys.stderr)
            return 1
        targets = (pid,)
    else:
        targets = _PROVIDER_ORDER

    installed = set(detect_installed_cli_providers())
    print()
    for pid in targets:
        name = _DISPLAY_NAMES[pid]
        auth_args = _AUTH_ARGS[pid]
        exe = pid.split("_")[0]  # claude / gemini / codex
        exe_path = shutil.which(exe)
        if pid not in installed or not exe_path:
            print(f"  [✗] {name} 미설치 → 먼저: af provider install {exe}")
            continue
        cmd = [exe_path, *auth_args]
        print(f"  [{name}] 인증 시작 ({' '.join(cmd)})...")
        print("  " + "-" * 44)
        try:
            subprocess.run(cmd)
        except FileNotFoundError:
            print(f"  [✗] {exe} 실행 파일 미발견. PATH 확인 필요.")
        except KeyboardInterrupt:
            print(f"\n  [!] {name} 인증 중단")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="af provider",
        description="Claude·Gemini·Codex CLI 프로바이더 설치·인증 관리",
    )
    sub = parser.add_subparsers(dest="subcmd", metavar="<명령>")

    # status
    p_status = sub.add_parser("status", help="설치·인증 상태 확인")
    p_status.add_argument("--refresh", action="store_true", help="캐시 무시하고 auth ping 수행")
    p_status.add_argument("--fast", action="store_true", help="설치 여부만 (auth ping 생략)")

    # install
    p_install = sub.add_parser("install", help="미설치 프로바이더 npm 설치")
    p_install.add_argument(
        "provider_name", nargs="?",
        metavar="<claude|gemini|codex>",
        help="특정 프로바이더 (미지정=미설치 전체)",
    )
    p_install.add_argument("--force", action="store_true", help="이미 설치된 경우도 재설치")

    # auth
    p_auth = sub.add_parser("auth", help="프로바이더 인증 실행")
    p_auth.add_argument(
        "provider_name", nargs="?",
        metavar="<claude|gemini|codex>",
        help="특정 프로바이더 (미지정=미인증 전체)",
    )

    args = parser.parse_args(argv)

    if args.subcmd == "status":
        return cmd_status(args)
    elif args.subcmd == "install":
        return cmd_install(args)
    elif args.subcmd == "auth":
        return cmd_auth(args)
    else:
        parser.print_help()
        return 0

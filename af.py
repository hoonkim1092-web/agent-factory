#!/usr/bin/env python3
"""af — navigate to / run commands inside the agent-factory repo.

Cross-platform replacement for af.cmd.

Usage:
    python af.py              # print resolved path
    python af.py <command>    # run command inside agent-factory root
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_shortcuts import resolve_repo_path

# agent_launcher.py 서브커맨드로 라우팅할 af 명령 목록
_LAUNCHER_SUBCOMMANDS = {"doctor", "project", "symbols", "sandbox"}


def _forward_args(argv_rest: list[str], cwd: Path) -> list[str]:
    """launcher 서브커맨드 인자 전달 — symbols의 상대 path를 호출 cwd 기준 절대경로로 변환.

    launcher subprocess는 cwd=AF_root로 실행되므로, 사용자가 외부 프로젝트에서
    ``af symbols .`` 처럼 넘긴 상대경로가 AF 자신으로 오해석되는 것을 막는다.
    (``cwd / arg`` 는 arg가 절대경로면 arg를 그대로 반환하므로 절대경로 입력은 무변.)
    """
    forwarded = list(argv_rest)
    if (
        forwarded
        and forwarded[0] == "symbols"
        and len(forwarded) >= 2
        and not forwarded[1].startswith("-")
    ):
        forwarded[1] = str((cwd / forwarded[1]).resolve())
    return forwarded


def main() -> None:
    target = resolve_repo_path("agent-factory", Path.cwd())
    if not target:
        print("[af] Could not find 'agent-factory'. "
              "Set HOON_PROJECTS_HOME or move under a matching parent.")
        sys.exit(1)

    if len(sys.argv) == 1:
        print(target)
        return

    # agent_launcher.py 서브커맨드 → sys.executable로 명시 위임
    if sys.argv[1] in _LAUNCHER_SUBCOMMANDS:
        forwarded = _forward_args(sys.argv[1:], Path.cwd())
        result = subprocess.run(
            [sys.executable, str(Path(target) / "agent_launcher.py")] + forwarded,
            cwd=str(target),
        )
        sys.exit(result.returncode)

    result = subprocess.run(sys.argv[1:], cwd=str(target))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

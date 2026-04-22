"""skills/graphify/skill.py

External `graphifyy` (CLI: `graphify`) wrapper for agent-factory.

This skill does NOT install graphify at runtime. Installation is handled by
`install-af.sh --with-graphify` (macOS/Linux) or `install-af.ps1 -WithGraphify`
(Windows). If the CLI is missing, the skill returns a structured error so the
caller can surface install instructions instead of failing opaquely.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


_INSTALL_HINT = (
    "graphify CLI not found. Install via:\n"
    "  macOS/Linux:  bash install-af.sh --with-graphify\n"
    "  Windows:      .\\install-af.ps1 -WithGraphify\n"
    "Or manually:    uv tool install 'graphifyy>=0.4.27,<0.5.0' --python 3.13"
)

# Codex P5 fix + af-critic round 3 fix: extra_args 허용 CLI 플래그.
# graphify CLI가 미래에 위험 옵션을 추가해도 wrapper가 통과시키지 않도록 방어.
# boolean flag와 value flag를 분리 — boolean 뒤에는 positional 허용하지 않음
# (issue #2: --verbose 뒤에 임의 positional 허용 우회 차단).
_ALLOWED_VALUE_FLAGS = (
    "--mode",
    "--depth",
    "--out-dir",
    "--ignore",
    "--include",
    "--budget",
    "--max-files",
)
_ALLOWED_BOOLEAN_FLAGS = (
    "--update",
    "--watch",
    "--wiki",
    "--quiet",
    "--verbose",
)


class GraphifySkill:
    """Wrapper around the external `graphify` CLI binary."""

    __skill_id__ = "graphify"

    def propose(self, ctx: dict, command: str = "build", target: str = ".") -> dict:
        cli = shutil.which("graphify")
        if cli is None:
            return {
                "status": "missing_dependency",
                "ok": False,
                "error": _INSTALL_HINT,
            }
        return {
            "status": "proposed",
            "ok": True,
            "cli": cli,
            "command": command,
            "target": target,
            "supported_commands": ["build", "query", "path", "explain", "add", "update"],
        }

    def apply(
        self,
        ctx: dict,
        command: str = "build",
        target: str = ".",
        extra_args: list[str] | None = None,
        cwd: str | None = None,
        timeout_sec: int = 1800,
    ) -> dict:
        """Execute a graphify CLI command.

        command="build"   → graphify <target>
        command="query"   → graphify query <target>     (target = question)
        command="path"    → graphify path <node_a> <node_b>
        command="explain" → graphify explain <node>
        command="add"     → graphify add <url>
        command="update"  → graphify <target> --update

        Security boundary: `target` and `extra_args` values are passed to graphify
        as-is (subprocess shell=False prevents shell injection). The wrapper does
        NOT validate `target` semantics or `extra_args` value formats — caller is
        responsible for ensuring `target` is a trusted path/question/URL and that
        flag values match graphify's own constraints (e.g. `--depth` integer).
        Allowlist (_ALLOWED_VALUE_FLAGS / _ALLOWED_BOOLEAN_FLAGS) enforces only
        the flag *names*, not their *values*.
        """
        cli = shutil.which("graphify")
        if cli is None:
            return {"status": "missing_dependency", "ok": False, "error": _INSTALL_HINT}

        rejected = self._reject_disallowed_extras(extra_args or [])
        if rejected:
            return {
                "status": "rejected_extra_args",
                "ok": False,
                "error": (
                    f"Unsupported extra_args: {rejected}. "
                    f"Allowed value flags: {_ALLOWED_VALUE_FLAGS}. "
                    f"Allowed boolean flags: {_ALLOWED_BOOLEAN_FLAGS}."
                ),
            }

        argv = self._build_argv(cli, command, target, extra_args or [])
        if argv is None:
            return {
                "status": "invalid_command",
                "ok": False,
                "error": f"Unsupported command: {command}",
            }

        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=cwd,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "ok": False,
                "error": f"graphify timed out after {timeout_sec}s",
                "argv": argv,
            }
        except FileNotFoundError:
            return {"status": "missing_dependency", "ok": False, "error": _INSTALL_HINT}

        succeeded = result.returncode == 0
        return {
            "status": "applied" if succeeded else "failed",
            "ok": succeeded,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "argv": argv,
            # 실패 시 stale graphify-out/이 남아 있으면 호출자가 오래된 결과를 성공으로
            # 오인할 수 있으므로 명시적으로 비움 (af-critic HIGH#3 fix).
            "artifacts": self._infer_artifacts(cwd or os.getcwd()) if succeeded else {},
        }

    def test(self, ctx: dict) -> dict:
        """Verify the CLI is reachable and return its version."""
        cli = shutil.which("graphify")
        if cli is None:
            return {"ok": False, "error": _INSTALL_HINT, "status": "missing_dependency"}
        try:
            result = subprocess.run(
                [cli, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "graphify --version timed out"}
        return {
            "ok": result.returncode == 0,
            "status": "verified" if result.returncode == 0 else "failed",
            "version": result.stdout.strip(),
            "stderr": result.stderr.strip() or None,
        }

    @staticmethod
    def _reject_disallowed_extras(extras: list[str]) -> list[str]:
        """allowlist에 없는 인자만 반환. 빈 리스트면 통과.

        af-critic round 3 fix:
          - issue #1: enumerate로 정확한 위치 추적 (list.index는 첫 위치만 반환)
          - issue #2: boolean flag(--verbose 등) 뒤 positional 허용하지 않음
          - issue #4: bad 발견 후에도 정상 value/flag는 bad에 추가하지 않음
        """
        def _is_value_flag(arg: str) -> bool:
            return any(arg == p or arg.startswith(p + "=") for p in _ALLOWED_VALUE_FLAGS)

        def _is_boolean_flag(arg: str) -> bool:
            return arg in _ALLOWED_BOOLEAN_FLAGS

        bad: list[str] = []
        i = 0
        while i < len(extras):
            arg = extras[i]
            if arg.startswith("--"):
                if _is_value_flag(arg):
                    # `--depth=3` 형태 (값 포함) → 단일 토큰 통과.
                    # `--depth 3` 형태 → 다음 토큰을 값으로 묶어서 통과.
                    if "=" in arg:
                        i += 1
                    else:
                        # 다음 토큰이 있고 값(--로 시작 안 함)이면 묶음 통과.
                        if i + 1 < len(extras) and not extras[i + 1].startswith("--"):
                            i += 2
                        else:
                            # 값이 없으면 flag 자체는 통과 (graphify가 default 값 사용 가정).
                            i += 1
                elif _is_boolean_flag(arg):
                    i += 1
                else:
                    bad.append(arg)
                    i += 1
            else:
                # 단독 positional은 항상 거부.
                bad.append(arg)
                i += 1
        return bad

    @staticmethod
    def _build_argv(cli: str, command: str, target: str, extra: list[str]) -> list[str] | None:
        if command == "build":
            return [cli, target, *extra]
        if command == "update":
            return [cli, target, "--update", *extra]
        if command in {"query", "path", "explain", "add"}:
            return [cli, command, target, *extra]
        return None

    @staticmethod
    def _infer_artifacts(cwd: str) -> dict[str, Any]:
        out_dir = os.path.join(cwd, "graphify-out")
        if not os.path.isdir(out_dir):
            return {}
        return {
            "out_dir": out_dir,
            "graph_html": _exists(out_dir, "graph.html"),
            "graph_json": _exists(out_dir, "graph.json"),
            "report_md": _exists(out_dir, "GRAPH_REPORT.md"),
        }


def _exists(base: str, name: str) -> str | None:
    path = os.path.join(base, name)
    return path if os.path.exists(path) else None

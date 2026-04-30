#!/usr/bin/env python3
"""Diff-based test gap analyzer for af-test-runner.

This checker is deliberately deterministic and cheap. It does not prove that
all tests are sufficient; it catches high-risk changed hunks where a missing
representative edge-case test has repeatedly led to af-critic BLOCK findings.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


_PY_FILE_RE = re.compile(r"\.py$")
_SUBPROCESS_RE = re.compile(
    r"\bsubprocess\.(run|Popen|call|check_call|check_output)\s*\(|"
    r"\bshell\s*=\s*True|"
    r"\bshlex\.split\s*\(",
    re.IGNORECASE,
)
_PLATFORM_RE = re.compile(r"\bsys\.platform\b|\bos\.name\b|\bplatform\.system\s*\(", re.IGNORECASE)
_WINDOWS_QUOTED_PATH_RE = re.compile(
    r"Program Files|C:\\\\|C:/|\"[A-Za-z]:\\\\|[A-Za-z]:\\\\[^'\"]*\s+[^'\"]*",
    re.IGNORECASE,
)
_POSIX_QUOTED_PATH_RE = re.compile(
    r"/Applications/[^'\"]*\s+[^'\"]*|"
    r"/opt/[^'\"]*\s+[^'\"]*|"
    r"/usr/local/[^'\"]*\s+[^'\"]*|"
    r"\"/(Applications|opt|usr/local)/",
    re.IGNORECASE,
)
_SHELL_TRUE_RE = re.compile(r"\bshell\s*=\s*True", re.IGNORECASE)
_SHLEX_RE = re.compile(r"\bshlex\.split\s*\(", re.IGNORECASE)
_PACKAGING_RUNTIME_PATH_RE = re.compile(
    r"\bsys\.executable\b|"
    r"\bsys\._MEIPASS\b|"
    r"\bsys\.frozen\b|"
    r"\b__file__\b|"
    r"\bPath\s*\(\s*__file__\s*\)",
    re.IGNORECASE,
)
_FROZEN_BUILD_TEST_RE = re.compile(
    r"("
    r"(monkeypatch\.setattr|setattr)\s*\(\s*sys\s*,\s*['\"]frozen['\"]|"
    r"(monkeypatch\.setattr|setattr)\s*\(\s*sys\s*,\s*['\"]_MEIPASS['\"]|"
    r"sys\._MEIPASS|"
    r"dist[/\\]af|af\.exe|PyInstaller|frozen build"
    r")",
    re.IGNORECASE,
)


@dataclass
class TestGap:
    risk_id: str
    severity: str
    changed_file: str
    reason: str
    expected_test_evidence: str
    related_tests: list[str] = field(default_factory=list)


@dataclass
class TestGapReport:
    verdict: str
    gaps: list[TestGap] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "gaps": [gap.__dict__ for gap in self.gaps],
            "warnings": self.warnings,
        }


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _is_test_file(path: str) -> bool:
    norm = _norm(path)
    return norm.startswith("tests/") or "/tests/" in norm


def _is_candidate_python_file(path: str) -> bool:
    norm = _norm(path)
    if not norm.endswith(".py"):
        return False
    return (
        "/" not in norm
        or norm.startswith("core/")
        or norm.startswith("scripts/")
        or norm.startswith("skills/")
        or norm.startswith("tests/")
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _git(args: list[str], cwd: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def _is_git_tracked(workspace: str, rel_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel_path],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _is_git_ignored(workspace: str, rel_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", rel_path],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _untracked_python_files_from_fs(workspace: str) -> list[str]:
    root = Path(workspace)
    search_roots = [root / name for name in ("core", "scripts", "skills", "tests")]
    search_roots.append(root)
    skip_dirs = {".git", ".venv", "__pycache__", "dist", "build", "agent_factory.egg-info"}
    files: list[str] = []

    for search_root in search_roots:
        if not search_root.exists():
            continue
        candidates = search_root.glob("*.py") if search_root == root else search_root.rglob("*.py")
        for path in candidates:
            if any(part in skip_dirs for part in path.parts):
                continue
            rel = _norm(str(path.relative_to(root)))
            if rel in files or _is_git_tracked(workspace, rel) or _is_git_ignored(workspace, rel):
                continue
            files.append(rel)
    return files


def changed_files_from_pending(workspace: str, pending_path: str | None = None) -> list[str]:
    pending = Path(pending_path) if pending_path else Path(workspace) / ".af_review_queue" / "pending_agent_review.json"
    if not pending.exists():
        return []
    try:
        data = json.loads(pending.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [str(item) for item in data.get("files", []) if str(item).endswith(".py")]


def changed_files_from_git(workspace: str) -> list[str]:
    files: list[str] = []
    saw_untracked_from_git = False
    for args in (["diff", "--name-only", "HEAD"], ["diff", "--cached", "--name-only"]):
        for line in _git(args, workspace).splitlines():
            rel = _norm(line.strip())
            if _is_candidate_python_file(rel) and rel not in files:
                files.append(rel)

    for line in _git(["ls-files", "--others", "--exclude-standard"], workspace).splitlines():
        rel = _norm(line.strip())
        if _is_candidate_python_file(rel):
            saw_untracked_from_git = True
            if rel not in files:
                files.append(rel)

    if not saw_untracked_from_git:
        for rel in _untracked_python_files_from_fs(workspace):
            if rel not in files:
                files.append(rel)
    return files


def _synthetic_added_diff(workspace: str, rel_path: str) -> str:
    path = Path(workspace) / rel_path
    text = _read_text(path)
    if not text:
        return ""
    lines = [
        f"diff --git a/{rel_path} b/{rel_path}",
        "new file mode 100644",
        "index 0000000..0000000",
        "--- /dev/null",
        f"+++ b/{rel_path}",
        "@@",
    ]
    lines.extend(f"+{line}" for line in text.splitlines())
    return "\n".join(lines) + "\n"


def git_diff(workspace: str, changed_files: list[str]) -> str:
    if not changed_files:
        return _git(["diff", "HEAD"], workspace, timeout=15)
    diff_parts = [_git(["diff", "HEAD", "--", *changed_files], workspace, timeout=15)]
    for rel in [_norm(path) for path in changed_files]:
        if _is_candidate_python_file(rel) and not _is_git_tracked(workspace, rel):
            synthetic = _synthetic_added_diff(workspace, rel)
            if synthetic:
                diff_parts.append(synthetic)
    return "\n".join(part for part in diff_parts if part)


def find_related_tests(workspace: str, changed_file: str) -> list[str]:
    root = Path(workspace)
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return []

    norm = _norm(changed_file)
    stem = Path(norm).stem.lower()
    module_import = norm[:-3].replace("/", ".") if norm.endswith(".py") else norm.replace("/", ".")
    related: list[str] = []

    for test_path in tests_dir.rglob("test*.py"):
        name = test_path.name.lower()
        content = _read_text(test_path)
        if stem in name or module_import in content:
            related.append(str(test_path))

    return sorted(dict.fromkeys(related))


def _combined_related_test_text(paths: list[str]) -> str:
    return "\n".join(_read_text(Path(path)) for path in paths)


def _file_diff_excerpt(diff_text: str, changed_file: str) -> str:
    norm = _norm(changed_file)
    chunks = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    for chunk in chunks:
        if f" b/{norm}" in chunk or f" a/{norm}" in chunk:
            return chunk
    return diff_text


def _is_subprocess_quoting_risk(diff_excerpt: str, file_text: str) -> bool:
    del file_text
    return bool(
        _SUBPROCESS_RE.search(diff_excerpt)
        and (_SHELL_TRUE_RE.search(diff_excerpt) or _SHLEX_RE.search(diff_excerpt))
    )


def _has_cross_platform_quoted_path_tests(test_text: str) -> bool:
    has_windows = bool(_WINDOWS_QUOTED_PATH_RE.search(test_text))
    has_posix = bool(_POSIX_QUOTED_PATH_RE.search(test_text))
    has_quotes = "\"" in test_text or "'" in test_text
    return has_windows and has_posix and has_quotes


def _has_frozen_build_evidence(test_text: str) -> bool:
    return bool(_FROZEN_BUILD_TEST_RE.search(test_text))


def _is_packaging_runtime_path_risk(diff_excerpt: str, file_text: str) -> bool:
    del file_text
    return bool(_PACKAGING_RUNTIME_PATH_RE.search(diff_excerpt))


def analyze_diff(
    *,
    workspace: str,
    changed_files: list[str],
    diff_text: str,
) -> TestGapReport:
    gaps: list[TestGap] = []
    warnings: list[str] = []

    for changed_file in [_norm(f) for f in changed_files if _PY_FILE_RE.search(f)]:
        if _is_test_file(changed_file):
            continue

        abs_path = Path(workspace) / changed_file
        file_text = _read_text(abs_path)
        diff_excerpt = _file_diff_excerpt(diff_text, changed_file)
        related_tests = find_related_tests(workspace, changed_file)
        test_text = _combined_related_test_text(related_tests)

        if _is_subprocess_quoting_risk(diff_excerpt, file_text) and not _has_cross_platform_quoted_path_tests(test_text):
            gaps.append(TestGap(
                risk_id="cross_platform_quoted_path_subprocess",
                severity="FAIL",
                changed_file=changed_file,
                reason=(
                    "subprocess/shell/shlex 계열 변경은 Windows, macOS, Linux의 공백 포함 quoted executable path에서 "
                    "argv와 shell quoting이 깨질 가능성이 있습니다."
                ),
                expected_test_evidence=(
                    "관련 테스트에 Windows '\"C:\\\\Program Files\\\\...\\\\tool.cmd\" --flag'와 "
                    "POSIX '\"/Applications/.../tool\" --flag' 또는 '\"/opt/.../tool\" --flag' 케이스를 모두 추가하세요."
                ),
                related_tests=related_tests,
            ))

        if _is_packaging_runtime_path_risk(diff_excerpt, file_text) and not _has_frozen_build_evidence(test_text):
            gaps.append(TestGap(
                risk_id="frozen_build_parity",
                severity="FAIL",
                changed_file=changed_file,
                reason=(
                    "sys.executable, __file__, Path(__file__), sys._MEIPASS 계열 변경은 source 실행과 "
                    "배포/frozen 빌드에서 경로 기준이 달라질 수 있습니다."
                ),
                expected_test_evidence=(
                    "관련 테스트나 검증 절차에 sys.frozen/_MEIPASS/PyInstaller/dist/af/af.exe 등 "
                    "배포 빌드 경로 동등성 확인 근거를 추가하세요."
                ),
                related_tests=related_tests,
            ))

        if _PLATFORM_RE.search(diff_excerpt) and not re.search(r"win32|Windows|os\.name|sys\.platform", test_text, re.IGNORECASE):
            warnings.append(
                f"{changed_file}: platform 분기 변경이 있지만 관련 테스트에서 Windows/POSIX 분기 입력이 보이지 않습니다."
            )

    return TestGapReport(verdict="FAIL" if gaps else "PASS", gaps=gaps, warnings=warnings)


def _format_text(report: TestGapReport) -> str:
    lines = [f"[af-test-gap] verdict={report.verdict}"]
    for gap in report.gaps:
        lines.extend([
            f"- [{gap.severity}] {gap.risk_id}",
            f"  file: {gap.changed_file}",
            f"  reason: {gap.reason}",
            f"  expected: {gap.expected_test_evidence}",
            f"  related_tests: {', '.join(gap.related_tests) if gap.related_tests else '(none found)'}",
        ])
    for warning in report.warnings:
        lines.append(f"- [WARN] {warning}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect risky diff patterns that need representative tests.")
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("--pending", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    workspace = os.path.abspath(args.workspace)
    changed = changed_files_from_pending(workspace, args.pending or None) or changed_files_from_git(workspace)
    diff_text = git_diff(workspace, changed)
    report = analyze_diff(workspace=workspace, changed_files=changed, diff_text=diff_text)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(_format_text(report))
    return 1 if report.verdict == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())

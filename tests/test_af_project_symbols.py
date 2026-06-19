"""tests/test_af_project_symbols.py — af project symbols 서브커맨드 계약 테스트.

agent_launcher.py 의 `af project symbols [path] [--out DIR]` 디스패치를 검증한다.
내부 AST 추출은 test_codebase_symbols.py 가 이미 커버 — 여기는 CLI 계약만.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "agent_launcher.py")] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# INV-1: stdout 출력 — --out 없이 실행하면 symbols.md 마크다운이 stdout으로 출력된다
# ---------------------------------------------------------------------------

class TestSymbolsStdout:
    def test_stdout_contains_header(self, tmp_path: Path) -> None:
        (tmp_path / "sample.py").write_text("def foo(): pass\nclass Bar: pass\n", encoding="utf-8")
        result = _run(["project", "symbols", str(tmp_path)])
        assert result.returncode == 0
        assert "# Codebase Symbols" in result.stdout

    def test_stdout_contains_function(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text("def my_func(): pass\n", encoding="utf-8")
        result = _run(["project", "symbols", str(tmp_path)])
        assert "my_func" in result.stdout

    def test_stdout_contains_csharp_symbols(self, tmp_path: Path) -> None:
        (tmp_path / "PlayerController.cs").write_text(
            "public class PlayerController {\n"
            "    public void Move() {}\n"
            "}\n",
            encoding="utf-8",
        )
        result = _run(["project", "symbols", str(tmp_path)])
        assert result.returncode == 0
        assert "PlayerController.cs" in result.stdout
        assert "PlayerController" in result.stdout
        assert "Move" in result.stdout

    def test_stdout_current_dir_default(self) -> None:
        """경로 미지정 시 CWD(repo root)를 대상으로 실행된다."""
        result = _run(["project", "symbols"], cwd=str(REPO_ROOT))
        assert result.returncode == 0
        assert "# Codebase Symbols" in result.stdout


# ---------------------------------------------------------------------------
# INV-2: 파일 저장 — --out DIR 지정 시 DIR/symbols.md 파일이 생성된다
# ---------------------------------------------------------------------------

class TestSymbolsOutDir:
    def test_out_creates_symbols_md(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def alpha(): pass\n", encoding="utf-8")
        out_dir = tmp_path / "out"
        result = _run(["project", "symbols", str(src), "--out", str(out_dir)])
        assert result.returncode == 0
        symbols_path = out_dir / "symbols.md"
        assert symbols_path.exists(), "symbols.md 파일이 생성돼야 한다"
        content = symbols_path.read_text(encoding="utf-8")
        assert "alpha" in content

    def test_out_creates_dir_if_missing(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("", encoding="utf-8")
        out_dir = tmp_path / "new" / "nested"
        assert not out_dir.exists()
        result = _run(["project", "symbols", str(src), "--out", str(out_dir)])
        assert result.returncode == 0
        assert (out_dir / "symbols.md").exists()

    def test_out_progress_message_to_stderr(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        out_dir = tmp_path / "out"
        result = _run(["project", "symbols", str(src), "--out", str(out_dir)])
        assert "symbols.md" in result.stderr


# ---------------------------------------------------------------------------
# INV-3: 오류 처리 — 존재하지 않는 경로는 exit 1 + stderr 메시지
# ---------------------------------------------------------------------------

class TestSymbolsErrorHandling:
    def test_nonexistent_path_exits_nonzero(self, tmp_path: Path) -> None:
        result = _run(["project", "symbols", str(tmp_path / "no_such_dir")])
        assert result.returncode != 0

    def test_nonexistent_path_stderr_message(self, tmp_path: Path) -> None:
        result = _run(["project", "symbols", str(tmp_path / "no_such_dir")])
        assert "디렉터리가 아님" in result.stderr or "no_such_dir" in result.stderr

    def test_file_path_exits_nonzero(self, tmp_path: Path) -> None:
        """파일 경로를 지정하면 exit 1 — is_dir() 체크 (Medium advisory 수용)."""
        f = tmp_path / "some.py"
        f.write_text("def foo(): pass\n", encoding="utf-8")
        result = _run(["project", "symbols", str(f)])
        assert result.returncode != 0

    def test_file_path_stderr_message(self, tmp_path: Path) -> None:
        f = tmp_path / "some.py"
        f.write_text("def foo(): pass\n", encoding="utf-8")
        result = _run(["project", "symbols", str(f)])
        assert "디렉터리가 아님" in result.stderr or "some.py" in result.stderr


# ---------------------------------------------------------------------------
# INV-4: 빈 디렉터리 — Python 파일 0개여도 정상 종료, 마크다운 헤더 포함
# ---------------------------------------------------------------------------

class TestSymbolsEmptyDir:
    def test_empty_dir_exits_zero(self, tmp_path: Path) -> None:
        result = _run(["project", "symbols", str(tmp_path)])
        assert result.returncode == 0

    def test_empty_dir_has_header(self, tmp_path: Path) -> None:
        result = _run(["project", "symbols", str(tmp_path)])
        assert "# Codebase Symbols" in result.stdout

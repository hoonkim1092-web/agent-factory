"""tests/test_af_symbols.py — af symbols 서브커맨드 유닛 테스트.

scripts/af_symbols.py는 외부 디렉터리 경로를 받아
scripts/codebase_symbols.build(path) 결과를 <path>/.af_index/symbols.md에 쓴다.
새 AST 파싱 로직 없음 — codebase_symbols.build 재사용만 검증한다.
"""
from pathlib import Path

import pytest

from af import _forward_args
from scripts.af_symbols import build_symbols_index, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_sample_module(directory: Path) -> None:
    """top-level 클래스·함수를 가진 .py 파일을 directory에 만든다."""
    (directory / "sample.py").write_text(
        "class WidgetFactory:\n"
        "    def make(self):\n"
        "        return 1\n"
        "\n"
        "def assemble_widget():\n"
        "    return WidgetFactory()\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# build_symbols_index — 직접 호출
# ---------------------------------------------------------------------------

class TestBuildSymbolsIndex:
    def test_creates_index_file(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        out = build_symbols_index(tmp_path)
        assert out == tmp_path / ".af_index" / "symbols.md"
        assert out.exists()

    def test_creates_af_index_dir_when_missing(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        assert not (tmp_path / ".af_index").exists()
        build_symbols_index(tmp_path)
        assert (tmp_path / ".af_index").is_dir()

    def test_index_contains_symbol_names(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        out = build_symbols_index(tmp_path)
        content = out.read_text(encoding="utf-8")
        assert "WidgetFactory" in content
        assert "assemble_widget" in content

    def test_index_references_source_file(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        content = build_symbols_index(tmp_path).read_text(encoding="utf-8")
        assert "sample.py" in content

    def test_empty_project_still_writes_file(self, tmp_path: Path) -> None:
        out = build_symbols_index(tmp_path)
        assert out.exists()
        # 헤더는 있으나 자기 자신(.af_index)을 심볼로 잡지 않는다
        assert "WidgetFactory" not in out.read_text(encoding="utf-8")

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        out = build_symbols_index(str(tmp_path))
        assert out.exists()


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------

class TestMain:
    def test_writes_index_and_returns_0(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        rc = main([str(tmp_path)])
        assert rc == 0
        assert (tmp_path / ".af_index" / "symbols.md").exists()

    def test_index_has_symbol_names(self, tmp_path: Path) -> None:
        _write_sample_module(tmp_path)
        main([str(tmp_path)])
        content = (tmp_path / ".af_index" / "symbols.md").read_text(encoding="utf-8")
        assert "WidgetFactory" in content
        assert "assemble_widget" in content

    def test_missing_path_returns_1(self) -> None:
        rc = main(["/nonexistent/path/that/does/not/exist"])
        assert rc == 1

    def test_prints_output_location(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _write_sample_module(tmp_path)
        main([str(tmp_path)])
        captured = capsys.readouterr()
        assert "symbols.md" in captured.out


# ---------------------------------------------------------------------------
# af.py _forward_args — 상대경로 오해석 방지 (cross-review BLOCK 회귀)
# ---------------------------------------------------------------------------

class TestForwardArgs:
    """launcher subprocess는 cwd=AF_root로 실행되므로, af symbols의 상대 path는
    호출 cwd 기준 절대경로로 변환돼야 한다 (안 그러면 '.'이 AF 자신으로 오해석)."""

    def test_dot_resolved_against_caller_cwd(self, tmp_path: Path) -> None:
        out = _forward_args(["symbols", "."], cwd=tmp_path)
        assert out[0] == "symbols"
        assert out[1] == str(tmp_path.resolve())

    def test_relative_subdir_resolved(self, tmp_path: Path) -> None:
        out = _forward_args(["symbols", "sub"], cwd=tmp_path)
        assert out[1] == str((tmp_path / "sub").resolve())

    def test_absolute_path_preserved(self, tmp_path: Path) -> None:
        # cwd가 달라도 절대경로 입력은 그대로 유지된다
        out = _forward_args(["symbols", str(tmp_path)], cwd=Path.home())
        assert out[1] == str(tmp_path.resolve())

    def test_flag_arg_untouched(self, tmp_path: Path) -> None:
        out = _forward_args(["symbols", "--help"], cwd=tmp_path)
        assert out == ["symbols", "--help"]

    def test_non_symbols_subcommand_untouched(self, tmp_path: Path) -> None:
        assert _forward_args(["project", "inspect", "."], cwd=tmp_path) == [
            "project", "inspect", str(tmp_path.resolve()),
        ]
        assert _forward_args(["doctor", "--fast"], cwd=tmp_path) == ["doctor", "--fast"]

    def test_project_symbols_path_resolved(self, tmp_path: Path) -> None:
        out = _forward_args(["project", "symbols", "src"], cwd=tmp_path)
        assert out == ["project", "symbols", str((tmp_path / "src").resolve())]

    def test_symbols_without_path_untouched(self, tmp_path: Path) -> None:
        out = _forward_args(["symbols"], cwd=tmp_path)
        assert out == ["symbols"]


# ---------------------------------------------------------------------------
# 배포 빌드 동등성 — af.spec hiddenimports (frozen build parity)
# ---------------------------------------------------------------------------

class TestFrozenBuildParity:
    """af_symbols와 그 전이 의존성이 af.spec hiddenimports에 등록돼 있어야
    frozen 빌드(af.exe)에서 ModuleNotFoundError 없이 import된다."""

    def _spec_text(self) -> str:
        spec = Path(__file__).resolve().parents[1] / "af.spec"
        return spec.read_text(encoding="utf-8")

    def test_af_symbols_in_hiddenimports(self) -> None:
        assert "scripts.af_symbols" in self._spec_text()

    def test_codebase_symbols_in_hiddenimports(self) -> None:
        # af_symbols.py가 직접 import하는 모듈 — 누락 시 frozen 빌드에서 import 실패
        assert "scripts.codebase_symbols" in self._spec_text()

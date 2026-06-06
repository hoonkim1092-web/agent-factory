"""tests/test_af_project_inspect.py — af project inspect 유닛 테스트."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

from scripts.af_project_inspect import (
    _detect_manifests,
    _detect_test_indicators,
    _detect_entrypoint_candidates,
    _detect_docs,
    _build_risks,
    format_markdown,
    inspect_project,
    main as inspect_main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doctor_check(name: str, status: str, detail: str = "") -> dict:
    return {"name": name, "status": status, "detail": detail, "fix_hint": ""}


def _clean_git() -> dict:
    return {"is_repo": True, "branch": "main", "dirty_count": 0}


def _base_docs(readme: str | None = "README.md") -> dict:
    return {"readme": readme, "docs_dir": None, "llm_wiki_dir": None}


# ---------------------------------------------------------------------------
# _detect_manifests
# ---------------------------------------------------------------------------

class TestDetectManifests:
    def test_empty(self, tmp_path: Path) -> None:
        assert _detect_manifests(tmp_path) == []

    def test_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]", encoding="utf-8")
        assert "pyproject.toml" in _detect_manifests(tmp_path)

    def test_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("pytest", encoding="utf-8")
        assert "requirements.txt" in _detect_manifests(tmp_path)

    def test_multiple_manifests(self, tmp_path: Path) -> None:
        for name in ["pyproject.toml", "setup.py", "requirements.txt"]:
            (tmp_path / name).write_text("", encoding="utf-8")
        result = _detect_manifests(tmp_path)
        assert "pyproject.toml" in result
        assert "setup.py" in result
        assert "requirements.txt" in result


# ---------------------------------------------------------------------------
# _detect_test_indicators
# ---------------------------------------------------------------------------

class TestDetectTestIndicators:
    def test_empty(self, tmp_path: Path) -> None:
        assert _detect_test_indicators(tmp_path) == []

    def test_tests_dir(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        assert "tests" in _detect_test_indicators(tmp_path)

    def test_test_dir(self, tmp_path: Path) -> None:
        (tmp_path / "test").mkdir()
        assert "test" in _detect_test_indicators(tmp_path)

    def test_pytest_ini(self, tmp_path: Path) -> None:
        (tmp_path / "pytest.ini").write_text("[pytest]", encoding="utf-8")
        assert "pytest.ini" in _detect_test_indicators(tmp_path)


# ---------------------------------------------------------------------------
# _detect_entrypoint_candidates
# ---------------------------------------------------------------------------

class TestDetectEntrypointCandidates:
    def test_empty(self, tmp_path: Path) -> None:
        assert _detect_entrypoint_candidates(tmp_path) == []

    def test_main_py_file(self, tmp_path: Path) -> None:
        (tmp_path / "__main__.py").write_text("", encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert any(c["kind"] == "__main__.py" for c in result)

    def test_main_guard_double_quote(self, tmp_path: Path) -> None:
        (tmp_path / "run.py").write_text('if __name__ == "__main__":\n    pass\n', encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert any(c["path"] == "run.py" and c["kind"] == "__main__ guard" for c in result)

    def test_main_guard_single_quote(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("if __name__ == '__main__':\n    pass\n", encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert any(c["path"] == "app.py" for c in result)

    def test_pyproject_scripts(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[project.scripts]\nmy-tool = 'pkg:main'\n", encoding="utf-8"
        )
        result = _detect_entrypoint_candidates(tmp_path)
        assert any(c["kind"] == "pyproject.scripts" for c in result)

    def test_all_candidates_are_candidate_confidence(self, tmp_path: Path) -> None:
        (tmp_path / "__main__.py").write_text("", encoding="utf-8")
        (tmp_path / "run.py").write_text('if __name__ == "__main__": pass', encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert all(c["confidence"] == "candidate" for c in result)

    def test_evidence_field_present(self, tmp_path: Path) -> None:
        (tmp_path / "__main__.py").write_text("", encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert all("evidence" in c for c in result)


# ---------------------------------------------------------------------------
# _detect_docs
# ---------------------------------------------------------------------------

class TestDetectDocs:
    def test_no_docs(self, tmp_path: Path) -> None:
        result = _detect_docs(tmp_path)
        assert result["readme"] is None
        assert result["docs_dir"] is None
        assert result["llm_wiki_dir"] is None

    def test_readme_md(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")
        assert _detect_docs(tmp_path)["readme"] == "README.md"

    def test_readme_rst(self, tmp_path: Path) -> None:
        (tmp_path / "README.rst").write_text("Hello", encoding="utf-8")
        assert _detect_docs(tmp_path)["readme"] == "README.rst"

    def test_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        assert _detect_docs(tmp_path)["docs_dir"] == "docs"

    def test_llm_wiki_dir(self, tmp_path: Path) -> None:
        wiki = tmp_path / "docs" / "generated" / "llm_wiki"
        wiki.mkdir(parents=True)
        result = _detect_docs(tmp_path)
        assert result["llm_wiki_dir"] is not None
        assert "llm_wiki" in result["llm_wiki_dir"]


# ---------------------------------------------------------------------------
# _build_risks
# ---------------------------------------------------------------------------

class TestBuildRisks:
    def test_all_ok_no_risks(self) -> None:
        checks = [_doctor_check("python", "ok")]
        risks = _build_risks(checks, _clean_git(), ["tests"], _base_docs())
        assert not any(r["kind"] == "doctor_fail" for r in risks)
        assert not any(r["kind"] == "git_dirty" for r in risks)

    def test_doctor_fail_becomes_fail_risk(self) -> None:
        checks = [_doctor_check("pytest", "fail", "pytest 미설치")]
        risks = _build_risks(checks, _clean_git(), ["tests"], _base_docs())
        assert any(r["kind"] == "doctor_fail" and r["severity"] == "fail" for r in risks)

    def test_git_dirty_comes_from_git_section_not_doctor(self) -> None:
        # doctor의 git_dirty warn과 무관하게 git['dirty_count']로 결정
        checks = []  # doctor에 git_dirty 없어도
        git = {"is_repo": True, "branch": "main", "dirty_count": 3}
        risks = _build_risks(checks, git, ["tests"], _base_docs())
        assert any(r["kind"] == "git_dirty" and r["severity"] == "warn" for r in risks)

    def test_git_dirty_message_includes_count(self) -> None:
        git = {"is_repo": True, "branch": "main", "dirty_count": 7}
        risks = _build_risks([], git, ["tests"], _base_docs())
        dirty = next(r for r in risks if r["kind"] == "git_dirty")
        assert "7" in dirty["message"]

    def test_git_dirty_zero_no_risk(self) -> None:
        risks = _build_risks([], _clean_git(), ["tests"], _base_docs())
        assert not any(r["kind"] == "git_dirty" for r in risks)

    def test_doctor_git_checks_excluded_from_risks(self) -> None:
        # doctor의 git_repo/git_dirty는 risks 생성 제외 (target git 섹션이 담당)
        checks = [
            _doctor_check("git_repo", "fail", "git 미설치"),
            _doctor_check("git_dirty", "warn", "uncommitted 3개"),
        ]
        risks = _build_risks(checks, _clean_git(), ["tests"], _base_docs())
        assert not any(r["kind"] == "doctor_fail" and "git_repo" in r["message"] for r in risks)
        assert not any(r["kind"] == "doctor_warn" and "git_dirty" in r["message"] for r in risks)

    def test_generic_warn_becomes_doctor_warn(self) -> None:
        checks = [_doctor_check("hooks", "warn", ".githooks 미설치")]
        risks = _build_risks(checks, _clean_git(), ["tests"], _base_docs())
        assert any(r["kind"] == "doctor_warn" and r["severity"] == "warn" for r in risks)

    def test_no_tests_adds_warn_risk(self) -> None:
        risks = _build_risks([], _clean_git(), [], _base_docs())
        assert any(r["kind"] == "no_tests" and r["severity"] == "warn" for r in risks)

    def test_no_readme_adds_info_risk(self) -> None:
        risks = _build_risks([], _clean_git(), ["tests"], _base_docs(readme=None))
        assert any(r["kind"] == "no_readme" and r["severity"] == "info" for r in risks)

    def test_risk_source_field_present(self) -> None:
        checks = [_doctor_check("python", "fail", "오류")]
        risks = _build_risks(checks, _clean_git(), ["tests"], _base_docs())
        assert all("source" in r for r in risks)


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------

class TestFormatMarkdown:
    def _ctx(self, risks: list | None = None) -> dict:
        return {
            "schema_version": 1,
            "project": {"root": "/tmp/proj", "name": "proj", "language": "python"},
            "git": {"is_repo": True, "branch": "main", "dirty_count": 0},
            "doctor": {"ok_count": 1, "warn_count": 0, "fail_count": 0, "checks": []},
            "python": {
                "manifests": ["pyproject.toml"],
                "test_indicators": ["tests"],
                "entrypoint_candidates": [],
                "py_file_count": 10,
            },
            "docs": {"readme": "README.md", "docs_dir": "docs", "llm_wiki_dir": None},
            "risks": risks or [],
        }

    def test_clean_project_shows_ready(self) -> None:
        assert "착수 가능" in format_markdown(self._ctx())

    def test_fail_risk_shows_fail(self) -> None:
        ctx = self._ctx([{"kind": "doctor_fail", "severity": "fail", "message": "x", "source": "doctor"}])
        md = format_markdown(ctx)
        assert "fail" in md

    def test_warn_only_shows_warn(self) -> None:
        ctx = self._ctx([{"kind": "no_tests", "severity": "warn", "message": "x", "source": "project"}])
        md = format_markdown(ctx)
        assert "warn" in md

    def test_project_name_in_header(self) -> None:
        md = format_markdown(self._ctx())
        assert "proj" in md

    def test_no_risks_section_says_none(self) -> None:
        md = format_markdown(self._ctx())
        assert "없음" in md


# ---------------------------------------------------------------------------
# inspect_project integration (no git/doctor side-effects)
# ---------------------------------------------------------------------------

class TestInspectProject:
    def test_schema_version_is_1(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        assert ctx["schema_version"] == 1

    def test_required_keys_present(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        for key in ("project", "git", "doctor", "python", "docs", "risks"):
            assert key in ctx, f"missing key: {key}"

    def test_project_name_matches_dir(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        assert ctx["project"]["name"] == tmp_path.name

    def test_no_tests_risk_when_no_test_dir(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        assert any(r["kind"] == "no_tests" for r in ctx["risks"])

    def test_test_dir_suppresses_no_tests_risk(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        ctx = inspect_project(tmp_path)
        assert not any(r["kind"] == "no_tests" for r in ctx["risks"])

    def test_risks_have_required_fields(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        for r in ctx["risks"]:
            assert "kind" in r
            assert "severity" in r
            assert "message" in r
            assert "source" in r

    def test_json_serializable(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        dumped = json.dumps(ctx)
        reloaded = json.loads(dumped)
        assert reloaded["schema_version"] == 1


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------

class TestMain:
    def test_missing_path_returns_1(self) -> None:
        rc = inspect_main(["/nonexistent/path/that/does/not/exist"])
        assert rc == 1

    def test_json_flag_produces_valid_json(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        rc = inspect_main(["--json", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["schema_version"] == 1

    def test_default_output_is_markdown(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        rc = inspect_main([str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "# AF Project Context" in captured.out

    def test_out_flag_writes_files(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        rc = inspect_main([str(tmp_path), "--out", str(out_dir)])
        assert rc == 0
        assert (out_dir / "af_project_context.md").exists()
        assert (out_dir / "af_project_context.json").exists()

    def test_out_flag_json_is_valid(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "output"
        inspect_main([str(tmp_path), "--out", str(out_dir)])
        raw = (out_dir / "af_project_context.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["schema_version"] == 1

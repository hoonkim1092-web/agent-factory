"""tests/test_af_project_inspect.py — af project inspect 유닛 테스트."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

from scripts.af_project_inspect import (
    _DOCTOR_CWD_GIT_CHECKS,
    _detect_manifests,
    _detect_test_indicators,
    _pyproject_has_pytest,
    _find_nested_test_file,
    _detect_entrypoint_candidates,
    _detect_docs,
    _build_risks,
    _recommend_next_steps,
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

    def test_nested_test_prefix_file_detected(self, tmp_path: Path) -> None:
        sub = tmp_path / "pkg" / "mcp"
        sub.mkdir(parents=True)
        (sub / "test_gate.py").write_text("def test_x(): pass", encoding="utf-8")
        result = _detect_test_indicators(tmp_path)
        assert result == ["pkg/mcp/test_gate.py"]

    def test_nested_test_suffix_file_detected(self, tmp_path: Path) -> None:
        sub = tmp_path / "server"
        sub.mkdir()
        (sub / "smoke_test.py").write_text("def test_x(): pass", encoding="utf-8")
        result = _detect_test_indicators(tmp_path)
        assert result == ["server/smoke_test.py"]

    def test_root_indicator_skips_nested_scan(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "test_deep.py").write_text("", encoding="utf-8")
        # 루트 indicator가 있으면 하위 스캔하지 않음 — nested 경로 미포함
        assert _detect_test_indicators(tmp_path) == ["tests"]

    def test_nested_non_test_py_ignored(self, tmp_path: Path) -> None:
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "helper.py").write_text("", encoding="utf-8")
        assert _detect_test_indicators(tmp_path) == []

    def test_pyproject_with_pytest_section_detected(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths = ['t']\n", encoding="utf-8"
        )
        assert "pyproject.toml" in _detect_test_indicators(tmp_path)

    def test_pyproject_build_only_not_a_test_indicator(self, tmp_path: Path) -> None:
        # pytest 섹션 없는 build-only pyproject.toml은 테스트 신호가 아님
        (tmp_path / "pyproject.toml").write_text(
            "[build-system]\nrequires = ['setuptools']\n", encoding="utf-8"
        )
        assert _detect_test_indicators(tmp_path) == []

    def test_pyproject_build_only_falls_through_to_nested_scan(self, tmp_path: Path) -> None:
        # build-only pyproject + 하위 test 파일 → nested scan이 작동해 감지
        (tmp_path / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "test_x.py").write_text("", encoding="utf-8")
        assert _detect_test_indicators(tmp_path) == ["pkg/test_x.py"]


# ---------------------------------------------------------------------------
# _pyproject_has_pytest
# ---------------------------------------------------------------------------

class TestPyprojectHasPytest:
    def test_tool_pytest_section(self, tmp_path: Path) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
        assert _pyproject_has_pytest(p) is True

    def test_bare_pytest_section(self, tmp_path: Path) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text("[pytest]\n", encoding="utf-8")
        assert _pyproject_has_pytest(p) is True

    def test_build_only_returns_false(self, tmp_path: Path) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text("[build-system]\nrequires = []\n", encoding="utf-8")
        assert _pyproject_has_pytest(p) is False


# ---------------------------------------------------------------------------
# _find_nested_test_file
# ---------------------------------------------------------------------------

class TestFindNestedTestFile:
    def test_none_when_no_tests(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("", encoding="utf-8")
        assert _find_nested_test_file(tmp_path) is None

    def test_returns_posix_relative_path(self, tmp_path: Path) -> None:
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "test_thing.py").write_text("", encoding="utf-8")
        assert _find_nested_test_file(tmp_path) == "a/b/test_thing.py"

    def test_excludes_pycache_and_venv(self, tmp_path: Path) -> None:
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "test_cached.py").write_text("", encoding="utf-8")
        assert _find_nested_test_file(tmp_path) is None

    def test_deterministic_dir_order(self, tmp_path: Path) -> None:
        # peer 디렉터리 둘 다 test 파일 보유 → 사전순 첫 디렉터리(a_pkg)가 결정적으로 선택돼야 함
        for d in ["z_pkg", "m_pkg", "a_pkg"]:
            sub = tmp_path / d
            sub.mkdir()
            (sub / "test_mod.py").write_text("", encoding="utf-8")
        assert _find_nested_test_file(tmp_path) == "a_pkg/test_mod.py"


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

    def test_test_prefix_file_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "test_thing.py").write_text('if __name__ == "__main__": pass', encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert not any(c["path"] == "test_thing.py" for c in result)

    def test_test_suffix_file_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "thing_test.py").write_text('if __name__ == "__main__": pass', encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        assert not any(c["path"] == "thing_test.py" for c in result)

    def test_non_test_main_guard_still_detected(self, tmp_path: Path) -> None:
        (tmp_path / "contest.py").write_text('if __name__ == "__main__": pass', encoding="utf-8")
        result = _detect_entrypoint_candidates(tmp_path)
        # "contest" 는 test_ 접두/_test 접미가 아니므로 정상 후보로 잡혀야 함
        assert any(c["path"] == "contest.py" for c in result)


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
# _recommend_next_steps
# ---------------------------------------------------------------------------

_DUMMY_ENTRYPOINT = [{"path": "main.py", "kind": "__main__ guard", "confidence": "candidate", "evidence": "..."}]


def _ctx_for_steps(
    *,
    fail: bool = False,
    dirty: int = 0,
    test_indicators: list | None = None,
    readme: str | None = "README.md",
    entrypoints: list | None = None,
) -> dict:
    risks: list[dict] = []
    if fail:
        risks.append({"kind": "doctor_fail", "severity": "fail", "message": "x", "source": "doctor"})
    if dirty:
        risks.append({"kind": "git_dirty", "severity": "warn", "message": f"{dirty}개", "source": "project"})
    ep = entrypoints if entrypoints is not None else _DUMMY_ENTRYPOINT
    return {
        "project": {"root": "/tmp/proj", "name": "proj", "language": "python"},
        "risks": risks,
        "git": {"is_repo": True, "branch": "main", "dirty_count": dirty},
        "doctor": {"ok_count": 1, "warn_count": 0, "fail_count": 0, "checks": []},
        "python": {
            "manifests": [],
            "test_indicators": test_indicators if test_indicators is not None else ["tests"],
            "entrypoint_candidates": ep,
            "py_file_count": 5,
        },
        "docs": {"readme": readme, "docs_dir": None, "llm_wiki_dir": None},
    }


class TestRecommendNextSteps:
    def test_all_ok_returns_ready(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps())
        assert len(steps) == 1
        assert steps[0]["kind"] == "ready"
        assert steps[0]["priority"] == "p0"

    def test_fail_risk_returns_fix_environment_p0(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(fail=True))
        kinds = [s["kind"] for s in steps]
        assert "fix_environment" in kinds
        fix = next(s for s in steps if s["kind"] == "fix_environment")
        assert fix["priority"] == "p0"

    def test_dirty_worktree_returns_review_worktree_p1(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(dirty=3))
        kinds = [s["kind"] for s in steps]
        assert "review_worktree" in kinds
        step = next(s for s in steps if s["kind"] == "review_worktree")
        assert step["priority"] == "p1"

    def test_no_test_indicators_returns_add_test_entrypoint_p1(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(test_indicators=[]))
        kinds = [s["kind"] for s in steps]
        assert "add_test_entrypoint" in kinds
        step = next(s for s in steps if s["kind"] == "add_test_entrypoint")
        assert step["priority"] == "p1"

    def test_no_readme_returns_add_readme_p2(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(readme=None))
        kinds = [s["kind"] for s in steps]
        assert "add_readme" in kinds
        step = next(s for s in steps if s["kind"] == "add_readme")
        assert step["priority"] == "p2"

    def test_no_entrypoints_returns_confirm_entrypoint_p2(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(entrypoints=[]))
        kinds = [s["kind"] for s in steps]
        assert "confirm_entrypoint" in kinds
        step = next(s for s in steps if s["kind"] == "confirm_entrypoint")
        assert step["priority"] == "p2"

    def test_fail_and_dirty_both_appear(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(fail=True, dirty=2))
        kinds = [s["kind"] for s in steps]
        assert "fix_environment" in kinds
        assert "review_worktree" in kinds

    def test_ready_not_returned_when_issues_exist(self) -> None:
        steps = _recommend_next_steps(_ctx_for_steps(dirty=1))
        kinds = [s["kind"] for s in steps]
        assert "ready" not in kinds

    def test_steps_have_required_fields(self) -> None:
        for ctx in [
            _ctx_for_steps(),
            _ctx_for_steps(fail=True),
            _ctx_for_steps(dirty=1, test_indicators=[], readme=None, entrypoints=[]),
        ]:
            for step in _recommend_next_steps(ctx):
                assert "priority" in step
                assert "kind" in step
                assert "action" in step

    def test_markdown_includes_recommended_section(self) -> None:
        ctx = _ctx_for_steps(dirty=1)
        ctx["recommended_next_steps"] = _recommend_next_steps(ctx)
        md = format_markdown(ctx)
        assert "Recommended next steps" in md
        assert "review_worktree" in md


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
        for key in ("project", "git", "doctor", "python", "docs", "risks", "recommended_next_steps"):
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

    def test_doctor_section_excludes_cwd_git_checks(self, tmp_path: Path) -> None:
        # doctor 섹션은 AF 실행 환경 진단 — cwd-git 항목은 표시에서 제외돼야 함
        # (대상 프로젝트 git은 ctx["git"]이 담당; cwd-git 누수가 사용자를 오도)
        ctx = inspect_project(tmp_path)
        check_names = {c["name"] for c in ctx["doctor"]["checks"]}
        for name in _DOCTOR_CWD_GIT_CHECKS:
            assert name not in check_names

    def test_doctor_counts_match_filtered_checks(self, tmp_path: Path) -> None:
        ctx = inspect_project(tmp_path)
        checks = ctx["doctor"]["checks"]
        assert ctx["doctor"]["ok_count"] == sum(1 for c in checks if c["status"] == "ok")
        assert ctx["doctor"]["warn_count"] == sum(1 for c in checks if c["status"] == "warn")
        assert ctx["doctor"]["fail_count"] == sum(1 for c in checks if c["status"] == "fail")


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

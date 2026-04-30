from __future__ import annotations

import subprocess

from pathlib import Path

from scripts.test_gap_analyzer import analyze_diff, changed_files_from_git, find_related_tests, git_diff


def test_subprocess_shlex_change_requires_cross_platform_quoted_path_cases(tmp_path: Path):
    changed = tmp_path / "core" / "providers"
    changed.mkdir(parents=True)
    (changed / "cli.py").write_text(
        "import shlex\n"
        "import subprocess\n"
        "cmd = shlex.split(raw, posix=False)\n"
        "subprocess.run(cmd, shell=True)\n",
        encoding="utf-8",
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(
        "def test_cli_command_env_override_used_in_ping():\n"
        "    raw = '/custom/path/codex'\n"
        "    assert raw\n",
        encoding="utf-8",
    )

    diff = "\n".join(
        [
            "diff --git a/core/providers/cli.py b/core/providers/cli.py",
            "+import shlex",
            "+cmd = shlex.split(raw, posix=False)",
            "+subprocess.run(cmd, shell=True)",
        ]
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/providers/cli.py"],
        diff_text=diff,
    )

    assert report.verdict == "FAIL"
    assert report.gaps
    assert report.gaps[0].risk_id == "cross_platform_quoted_path_subprocess"


def test_cross_platform_quoted_path_cases_satisfy_subprocess_gap(tmp_path: Path):
    source_dir = tmp_path / "core" / "providers"
    source_dir.mkdir(parents=True)
    (source_dir / "cli.py").write_text("import subprocess\n", encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(
        "def test_cross_platform_paths_with_spaces():\n"
        "    raw = '\"C:\\\\Program Files\\\\Codex\\\\codex.cmd\" --version'\n"
        "    posix_raw = '\"/Applications/Codex CLI/codex\" --version'\n"
        "    linux_raw = '\"/opt/codex cli/codex\" --version'\n"
        "    assert 'Program Files' in raw\n"
        "    assert '/Applications/' in posix_raw\n"
        "    assert '/opt/' in linux_raw\n",
        encoding="utf-8",
    )

    diff = "diff --git a/core/providers/cli.py b/core/providers/cli.py\n+subprocess.run(cmd, shell=True)\n"

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/providers/cli.py"],
        diff_text=diff,
    )

    assert report.verdict == "PASS"
    assert report.gaps == []


def test_cli_packaging_change_requires_frozen_build_evidence(tmp_path: Path):
    (tmp_path / "core" / "providers").mkdir(parents=True)
    (tmp_path / "core" / "providers" / "cli.py").write_text("def x(): pass\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text("def test_cli(): assert True\n", encoding="utf-8")

    diff = "\n".join(
        [
            "diff --git a/core/providers/cli.py b/core/providers/cli.py",
            "+sys.executable",
            "+Path(__file__)",
        ]
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/providers/cli.py"],
        diff_text=diff,
    )

    assert report.verdict == "FAIL"
    assert any(gap.risk_id == "frozen_build_parity" for gap in report.gaps)


def test_frozen_build_evidence_satisfies_packaging_gap(tmp_path: Path):
    (tmp_path / "core" / "providers").mkdir(parents=True)
    (tmp_path / "core" / "providers" / "cli.py").write_text("def x(): pass\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "def test_frozen_build_path():\n"
        "    setattr(sys, 'frozen', True)\n"
        "    setattr(sys, '_MEIPASS', str(Path.cwd()))\n"
        "    assert Path(sys._MEIPASS).exists()\n",
        encoding="utf-8",
    )

    diff = "diff --git a/core/providers/cli.py b/core/providers/cli.py\n+sys.executable\n+Path(__file__)\n"
    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/providers/cli.py"],
        diff_text=diff,
    )

    assert all(gap.risk_id != "frozen_build_parity" for gap in report.gaps)


def test_subprocess_gap_only_triggers_when_risk_is_in_changed_hunk(tmp_path: Path):
    source_dir = tmp_path / "core" / "providers"
    source_dir.mkdir(parents=True)
    (source_dir / "cli.py").write_text(
        "import subprocess\n"
        "def old():\n"
        "    subprocess.run('codex', shell=True)\n"
        "def changed():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text("def test_changed(): assert True\n", encoding="utf-8")

    diff = "\n".join(
        [
            "diff --git a/core/providers/cli.py b/core/providers/cli.py",
            "@@ def changed():",
            "-    return 1",
            "+    return 2",
        ]
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/providers/cli.py"],
        diff_text=diff,
    )

    assert report.verdict == "PASS"
    assert report.gaps == []


def test_subprocess_gap_output_is_readable_korean(tmp_path: Path):
    changed = tmp_path / "core"
    changed.mkdir()
    (changed / "runner.py").write_text("import shlex\ncmd = shlex.split(raw)\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_runner.py").write_text("def test_runner(): assert True\n", encoding="utf-8")

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/runner.py"],
        diff_text="diff --git a/core/runner.py b/core/runner.py\n+cmd = shlex.split(raw)\n",
    )

    assert report.gaps
    assert "계열 변경" in report.gaps[0].reason
    assert "케이스를 모두 추가" in report.gaps[0].expected_test_evidence
    assert "\ufffd" not in report.gaps[0].reason


def test_test_file_changes_do_not_trigger_production_gap_gate(tmp_path: Path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_hook_runner_builtins.py").write_text(
        "import subprocess\n"
        "def test_fake_subprocess(monkeypatch):\n"
        "    subprocess.run('codex', shell=True)\n",
        encoding="utf-8",
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["tests/test_hook_runner_builtins.py"],
        diff_text=(
            "diff --git a/tests/test_hook_runner_builtins.py b/tests/test_hook_runner_builtins.py\n"
            "+subprocess.run('codex', shell=True)\n"
        ),
    )

    assert report.verdict == "PASS"
    assert report.gaps == []


def test_untracked_python_file_is_analyzed_as_added_diff(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "seed", "-q"],
        cwd=tmp_path,
        check=True,
    )

    source_dir = tmp_path / "core"
    source_dir.mkdir()
    (source_dir / "new_cli.py").write_text(
        "import subprocess\n"
        "def run(cmd):\n"
        "    return subprocess.run(cmd, shell=True)\n",
        encoding="utf-8",
    )

    changed = changed_files_from_git(str(tmp_path))
    diff = git_diff(str(tmp_path), changed)
    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=changed,
        diff_text=diff,
    )

    assert "core/new_cli.py" in changed
    assert report.verdict == "FAIL"
    assert any(gap.risk_id == "cross_platform_quoted_path_subprocess" for gap in report.gaps)


def test_frozen_build_evidence_requires_meaningful_parity_check(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "paths.py").write_text("from pathlib import Path\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_paths.py").write_text(
        "import sys\n"
        "def test_mentions_frozen_only():\n"
        "    assert getattr(sys, 'frozen', False) is False or True\n",
        encoding="utf-8",
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/paths.py"],
        diff_text="diff --git a/core/paths.py b/core/paths.py\n+Path(__file__)\n",
    )

    assert report.verdict == "FAIL"
    assert any(gap.risk_id == "frozen_build_parity" for gap in report.gaps)


def test_meaningful_frozen_build_parity_check_satisfies_gap(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "paths.py").write_text("from pathlib import Path\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_paths.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "def test_frozen_build_resource_path_parity(monkeypatch, tmp_path):\n"
        "    monkeypatch.setattr(sys, 'frozen', True, raising=False)\n"
        "    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)\n"
        "    assert Path(sys._MEIPASS).exists()\n",
        encoding="utf-8",
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/paths.py"],
        diff_text="diff --git a/core/paths.py b/core/paths.py\n+Path(__file__)\n",
    )

    assert all(gap.risk_id != "frozen_build_parity" for gap in report.gaps)


def test_find_related_tests_by_module_stem_and_import(tmp_path: Path):
    (tmp_path / "core" / "providers").mkdir(parents=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    direct = tests_dir / "test_cli.py"
    direct.write_text("# direct stem match\n", encoding="utf-8")
    importer = tests_dir / "test_provider_detect.py"
    importer.write_text("from core.providers.cli import Provider\n", encoding="utf-8")

    related = find_related_tests(str(tmp_path), "core/providers/cli.py")

    assert str(direct) in related
    assert str(importer) in related

"""
배선 단선 검증(wiring_parity) 룰 테스트 — §7 테스트 매트릭스.

analyze_diff()의 warnings 채널로 발화 (verdict = PASS 유지, BLOCK 아님).
"""
from __future__ import annotations

from pathlib import Path

from scripts.test_gap_analyzer import analyze_diff


def _make_diff(path: str, removed: str = "", added: str = "") -> str:
    lines = [f"diff --git a/{path} b/{path}"]
    for line in removed.splitlines():
        lines.append(f"-{line}")
    for line in added.splitlines():
        lines.append(f"+{line}")
    return "\n".join(lines)


def _has_wiring_warn(warnings: list[str], sym: str) -> bool:
    return any("[wiring]" in w and sym in w for w in warnings)


# ---------------------------------------------------------------------------
# W-PARAM-DEAD: 기존 함수에 새 파라미터, production caller가 안 넘김 → WARN
# ---------------------------------------------------------------------------
def test_w_param_dead_warns_when_caller_omits_new_param(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "def process(data, timeout=30):\n    return data\n",
        encoding="utf-8",
    )
    # caller does NOT pass timeout
    (tmp_path / "core" / "caller.py").write_text(
        "from core.mymodule import process\nresult = process(data)\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    diff = _make_diff(
        "core/mymodule.py",
        removed="def process(data):",
        added="def process(data, timeout=30):",
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )

    assert report.verdict == "PASS"
    assert _has_wiring_warn(report.warnings, "timeout"), (
        f"'timeout' wiring WARN expected but not found. warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-PARAM-WIRED: 새 파라미터를 caller가 키워드로 넘김 → WARN 없음
# ---------------------------------------------------------------------------
def test_w_param_wired_no_warn_when_caller_passes_param(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "def process(data, timeout=30):\n    return data\n",
        encoding="utf-8",
    )
    # caller passes timeout
    (tmp_path / "core" / "caller.py").write_text(
        "from core.mymodule import process\nresult = process(data, timeout=10)\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    diff = _make_diff(
        "core/mymodule.py",
        removed="def process(data):",
        added="def process(data, timeout=30):",
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )

    assert not _has_wiring_warn(report.warnings, "timeout"), (
        f"Unexpected 'timeout' wiring WARN. warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-NEW-DEAD: 신규 함수, production caller 0 → WARN + deferred 안내
# ---------------------------------------------------------------------------
def test_w_new_dead_warns_and_suggests_deferred(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "def helper(x):\n    return x * 2\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    diff = _make_diff("core/mymodule.py", added="def helper(x):")

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )

    assert report.verdict == "PASS"
    assert _has_wiring_warn(report.warnings, "helper"), (
        f"'helper' wiring WARN expected. warnings={report.warnings}"
    )
    # Should mention deferred marker in the warning
    assert any("wiring: deferred" in w for w in report.warnings), (
        f"deferred marker hint expected. warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-DEFERRED: 신규 함수 + # wiring: deferred 마커 → WARN 없음
# ---------------------------------------------------------------------------
def test_w_deferred_no_warn_when_marker_present(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "# wiring: deferred\n"
        "def helper(x):\n"
        "    return x * 2\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    diff = _make_diff("core/mymodule.py", added="def helper(x):")

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )

    assert not _has_wiring_warn(report.warnings, "helper"), (
        f"Unexpected 'helper' WARN with deferred marker. warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-UTIL-EXEMPT: core/utils.py 신규 함수 → WARN 없음
# ---------------------------------------------------------------------------
def test_w_util_exempt_no_warn_for_utils(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "utils.py").write_text(
        "def my_stat(xs):\n    return sum(xs) / len(xs)\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_utils.py").write_text("def test_x(): pass\n", encoding="utf-8")

    diff = _make_diff("core/utils.py", added="def my_stat(xs):")

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/utils.py"],
        diff_text=diff,
    )

    assert not _has_wiring_warn(report.warnings, "my_stat"), (
        f"Unexpected wiring WARN for utils.py. warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-TESTONLY: production caller 0, test caller만 있음 → WARN
# ---------------------------------------------------------------------------
def test_w_testonly_warns_when_only_test_caller(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "def compute(x):\n    return x\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    # Only test file calls compute()
    (tmp_path / "tests" / "test_mymodule.py").write_text(
        "from core.mymodule import compute\n"
        "def test_compute():\n"
        "    assert compute(1) == 1\n",
        encoding="utf-8",
    )

    diff = _make_diff("core/mymodule.py", added="def compute(x):")

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )

    assert report.verdict == "PASS"
    assert _has_wiring_warn(report.warnings, "compute"), (
        f"'compute' wiring WARN expected (test-only). warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-MULTILINE: 여러 줄 def 파라미터 추가 → parse correctly or skip gracefully
# ---------------------------------------------------------------------------
def test_w_multiline_no_crash(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "def process(\n    data,\n    timeout=30,\n    retries=3,\n):\n    return data\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    # Multiline def — closing ) not on same line as opening
    diff = "\n".join([
        "diff --git a/core/mymodule.py b/core/mymodule.py",
        "-def process(",
        "-    data,",
        "-    timeout=30,",
        "-) :",
        "+def process(",
        "+    data,",
        "+    timeout=30,",
        "+    retries=3,",
        "+):",
    ])

    # Must not crash regardless of parse outcome
    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )
    assert report is not None


# ---------------------------------------------------------------------------
# W-PARSE-FAIL: 파싱 불가 시그니처 → skip(WARN 없음, no crash)
# ---------------------------------------------------------------------------
def test_w_parse_fail_no_crash(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    # Malformed diff — not a proper def line
    diff = "diff --git a/core/mymodule.py b/core/mymodule.py\n+def (broken syntax\n"

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )
    assert report is not None


# ---------------------------------------------------------------------------
# W-HUNK-SPLIT: -def/+def가 다른 hunk에 분산 → crash 없이 처리 (WARN-only)
# ---------------------------------------------------------------------------
def test_w_hunk_split_no_crash(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "mymodule.py").write_text(
        "def process(data, timeout):\n    return data\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymodule.py").write_text("def test_x(): pass\n", encoding="utf-8")

    # -def and +def in separate hunks (hunk-split scenario)
    diff = "\n".join([
        "diff --git a/core/mymodule.py b/core/mymodule.py",
        "@@ -1,1 +0,0 @@",
        "-def process(data):",
        "@@ -5,0 +5,1 @@",
        "+def process(data, timeout):",
    ])

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/mymodule.py"],
        diff_text=diff,
    )
    assert report is not None  # no crash


# ---------------------------------------------------------------------------
# W-INIT-PARAM: __init__ 파라미터 추가 → dead-parameter 오분류하지 않음
# (caller는 ClassName(...) 형태라 __init__( 검색은 0결과)
# ---------------------------------------------------------------------------
def test_w_init_param_skipped_no_false_positive(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "myclass.py").write_text(
        "class MyClass:\n"
        "    def __init__(self, x, y):\n"
        "        self.x = x\n"
        "        self.y = y\n",
        encoding="utf-8",
    )
    # Caller instantiates via MyClass(x=1) — not __init__(x=1)
    (tmp_path / "core" / "factory.py").write_text(
        "from core.myclass import MyClass\nobj = MyClass(x=1)\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_myclass.py").write_text("def test_x(): pass\n", encoding="utf-8")

    diff = _make_diff(
        "core/myclass.py",
        removed="    def __init__(self, x):",
        added="    def __init__(self, x, y):",
    )

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["core/myclass.py"],
        diff_text=diff,
    )

    # __init__ param addition should NOT generate a dead-parameter WARN
    # (callers use ClassName() not __init__(), so grep gives false 0-result)
    assert not _has_wiring_warn(report.warnings, "y"), (
        f"__init__ param 'y' should not trigger dead-parameter WARN. warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# W-EXEMPT-TESTS-DIR: tests/ 자체 변경은 wiring 룰 적용 안 함
# ---------------------------------------------------------------------------
def test_w_test_files_not_checked(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text(
        "def helper(x):\n    return x\n",
        encoding="utf-8",
    )

    diff = _make_diff("tests/test_foo.py", added="def helper(x):")

    report = analyze_diff(
        workspace=str(tmp_path),
        changed_files=["tests/test_foo.py"],
        diff_text=diff,
    )

    assert not _has_wiring_warn(report.warnings, "helper"), (
        f"tests/ file should not trigger wiring WARN. warnings={report.warnings}"
    )

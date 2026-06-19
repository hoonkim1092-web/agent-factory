"""tests/test_review_consensus.py — INV-1/2/5/7 검증.

§9 테스트 매핑:
  INV-1  test_collects_without_llm*
  INV-2  test_no_provider_branch_in_consensus
  INV-5  TestUnverifiedNoFileLine
  INV-7  TestConsensusSidecarAbsent
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import review_consensus as rc


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_py(tmp_path, rel: str, src: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src, encoding="utf-8")
    return p


def _make_findings_json(tmp_path, findings: list, round_: int = 1) -> Path:
    q = tmp_path / ".af_review_queue"
    q.mkdir(parents=True, exist_ok=True)
    p = q / "cr_findings.json"
    p.write_text(json.dumps({"round": round_, "findings": findings}), encoding="utf-8")
    return p


# ─── INV-7: sidecar 부재 → SKIP ───────────────────────────────────────────────

class TestConsensusSidecarAbsent:
    def test_main_skips_when_no_findings_file(self, tmp_path):
        ret = rc.main(str(tmp_path))
        assert ret == 0
        assert not (tmp_path / ".af_review_queue" / "cr_evidence.json").exists()

    def test_main_creates_empty_evidence_for_empty_findings(self, tmp_path):
        _make_findings_json(tmp_path, [])
        ret = rc.main(str(tmp_path))
        assert ret == 0
        ev = json.loads((tmp_path / ".af_review_queue" / "cr_evidence.json").read_text())
        assert ev["evidence"] == []

    def test_main_returns_error_on_invalid_json(self, tmp_path):
        q = tmp_path / ".af_review_queue"
        q.mkdir()
        (q / "cr_findings.json").write_text("{invalid", encoding="utf-8")
        ret = rc.main(str(tmp_path))
        assert ret == 1


# ─── INV-1: LLM 미호출 ────────────────────────────────────────────────────────

class TestCollectEvidenceNoLlm:
    def test_collects_via_code_only(self, tmp_path):
        _make_py(tmp_path, "core/sample.py", "def my_func(x):\n    return x + 1\n")
        findings = [{
            "id": "F1", "label": "ACCEPT", "severity": "High",
            "file": "core/sample.py", "line": 1, "claim": "test",
        }]
        # patch grep-based functions to confirm no LLM is called
        with mock.patch.object(rc, "_find_callers", return_value=[]) as mc, \
             mock.patch.object(rc, "_find_callees", return_value=[]) as mcee, \
             mock.patch.object(rc, "_find_tests", return_value={}) as mt:
            evidence = rc.collect_evidence(str(tmp_path), findings)

        assert len(evidence) == 1
        assert evidence[0]["id"] == "F1"
        assert "surrounding_code" in evidence[0]
        mc.assert_called_once()
        mcee.assert_called_once()
        mt.assert_called_once()

    def test_non_blocking_labels_skipped_without_io(self, tmp_path):
        findings = [
            {"id": "F1", "label": "ACCEPT-ADV", "severity": "Medium", "file": "x.py", "line": 1, "claim": ""},
            {"id": "F2", "label": "REJECTED", "file": None, "line": None, "claim": ""},
            {"id": "F3", "label": "BONUS", "severity": "Low", "file": "y.py", "line": 5, "claim": ""},
        ]
        ev = rc.collect_evidence(str(tmp_path), findings)
        assert len(ev) == 3
        for e in ev:
            assert e.get("skip_reason") == "non-blocking label"
            assert "surrounding_code" not in e
            assert "callers" not in e


# ─── INV-5: file:line 부재 → UNVERIFIED ──────────────────────────────────────

class TestUnverifiedNoFileLine:
    def test_no_file_gives_unverified(self, tmp_path):
        findings = [{"id": "F1", "label": "ACCEPT", "severity": "High", "file": None, "line": 1, "claim": "x"}]
        ev = rc.collect_evidence(str(tmp_path), findings)
        assert ev[0]["consensus"] == "UNVERIFIED"
        assert ev[0].get("skip_reason") == "no file:line"

    def test_no_line_gives_unverified(self, tmp_path):
        findings = [{"id": "F1", "label": "ACCEPT", "severity": "High", "file": "core/x.py", "line": None, "claim": "x"}]
        ev = rc.collect_evidence(str(tmp_path), findings)
        assert ev[0]["consensus"] == "UNVERIFIED"

    def test_missing_file_gives_unverified(self, tmp_path):
        findings = [{"id": "F1", "label": "ACCEPT", "severity": "High", "file": "core/nonexistent.py", "line": 1, "claim": "x"}]
        ev = rc.collect_evidence(str(tmp_path), findings)
        assert ev[0]["consensus"] == "UNVERIFIED"
        assert ev[0].get("skip_reason") == "file not found"

    def test_accept_star_no_file_gives_unverified(self, tmp_path):
        findings = [{"id": "F1", "label": "ACCEPT★", "severity": "High", "file": None, "line": 1, "claim": "x"}]
        ev = rc.collect_evidence(str(tmp_path), findings)
        assert ev[0]["consensus"] == "UNVERIFIED"

    def test_accept_star_no_line_gives_unverified(self, tmp_path):
        findings = [{"id": "F1", "label": "ACCEPT★", "severity": "Critical", "file": "core/x.py", "line": None, "claim": "x"}]
        ev = rc.collect_evidence(str(tmp_path), findings)
        assert ev[0]["consensus"] == "UNVERIFIED"


# ─── INV-2: 프로바이더 분기 없음 ─────────────────────────────────────────────

class TestNoProviderBranch:
    def test_no_provider_import_in_source(self):
        content = (Path(__file__).parent.parent / "scripts" / "review_consensus.py").read_text(encoding="utf-8")
        assert "provider_detect" not in content
        assert "claude_cli" not in content
        assert "codex_cli" not in content
        assert "gemini_cli" not in content


# ─── surrounding code ──────────────────────────────────────────────────────────

class TestSurroundingCode:
    def test_returns_lines_around_target(self, tmp_path):
        f = tmp_path / "x.py"
        lines = [f"line_{i}" for i in range(1, 21)]
        f.write_text("\n".join(lines), encoding="utf-8")
        result = rc._surrounding_code(str(f), 10, ctx=3)
        assert "line_10" in result
        assert "line_7" in result
        assert "line_13" in result

    def test_clamps_at_file_boundaries(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        result = rc._surrounding_code(str(f), 1, ctx=20)
        assert "a" in result
        assert "b" in result

    def test_missing_file_returns_empty(self, tmp_path):
        result = rc._surrounding_code(str(tmp_path / "nonexistent.py"), 1)
        assert result == ""


# ─── enclosing function ────────────────────────────────────────────────────────

class TestEnclosingFunction:
    def test_finds_function_containing_line(self, tmp_path):
        f = _make_py(tmp_path, "x.py", "def foo(x):\n    return x\n\ndef bar():\n    pass\n")
        node = rc._enclosing_function(str(f), 2)
        assert node is not None
        assert node.name == "foo"

    def test_returns_none_for_module_level_line(self, tmp_path):
        f = _make_py(tmp_path, "x.py", "x = 1\n")
        node = rc._enclosing_function(str(f), 1)
        assert node is None

    def test_returns_none_for_missing_file(self, tmp_path):
        node = rc._enclosing_function(str(tmp_path / "no.py"), 1)
        assert node is None

    def test_returns_none_for_syntax_error(self, tmp_path):
        f = _make_py(tmp_path, "bad.py", "def foo(\n")
        node = rc._enclosing_function(str(f), 1)
        assert node is None


# ─── callee collection ─────────────────────────────────────────────────────────

class TestFindCallees:
    def test_finds_non_builtin_callee(self, tmp_path):
        _make_py(tmp_path, "core/helper.py", "def helper_fn(x): return x\n")
        src = _make_py(tmp_path, "core/main.py",
                       "def my_func(x):\n    y = helper_fn(x)\n    return y\n")
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=str(tmp_path / "core" / "helper.py") + ":1:def helper_fn(x):",
                returncode=0,
            )
            callees = rc._find_callees(str(tmp_path), str(src), 1)
        names = [c["callee"] for c in callees]
        assert "helper_fn" in names

    def test_skips_builtins(self, tmp_path):
        src = _make_py(tmp_path, "x.py",
                       "def my_func(items):\n    return list(map(str, items))\n")
        callees = rc._find_callees(str(tmp_path), str(src), 1)
        names = [c["callee"] for c in callees]
        assert "list" not in names
        assert "map" not in names
        assert "str" not in names

    def test_no_function_at_line_returns_empty(self, tmp_path):
        src = _make_py(tmp_path, "x.py", "x = 1\n")
        callees = rc._find_callees(str(tmp_path), str(src), 1)
        assert callees == []

    def test_deduplicates_same_callee(self, tmp_path):
        src = _make_py(tmp_path, "x.py",
                       "def f():\n    helper(1)\n    helper(2)\n    helper(3)\n")
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="", returncode=0)
            callees = rc._find_callees(str(tmp_path), str(src), 1)
        names = [c["callee"] for c in callees]
        assert names.count("helper") == 1


# ─── caller collection ────────────────────────────────────────────────────────

class TestFindCallers:
    def test_finds_caller_of_function(self, tmp_path):
        target = _make_py(tmp_path, "core/target.py", "def target_fn(x):\n    return x\n")
        _make_py(tmp_path, "core/caller.py", "from target import target_fn\nx = target_fn(1)\n")
        # grep 출력은 상대경로 또는 forward-slash 형식 — Windows 드라이브레터 없이 파싱 검증
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout="core/caller.py:2:x = target_fn(1)",
                returncode=0,
            )
            callers = rc._find_callers(str(tmp_path), str(target), 1)
        assert len(callers) >= 1
        assert callers[0]["symbol"] == "target_fn"

    def test_excludes_definition_line(self, tmp_path):
        src = _make_py(tmp_path, "core/x.py", "def my_fn(x): return x\n")
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                stdout=str(src) + ":1:def my_fn(x): return x",
                returncode=0,
            )
            callers = rc._find_callers(str(tmp_path), str(src), 1)
        assert callers == []

    def test_no_function_at_line_returns_empty(self, tmp_path):
        src = _make_py(tmp_path, "x.py", "x = 1\n")
        callers = rc._find_callers(str(tmp_path), str(src), 1)
        assert callers == []


# ─── main() integration ────────────────────────────────────────────────────────

class TestMain:
    def test_writes_cr_evidence_json(self, tmp_path):
        _make_py(tmp_path, "core/sample.py", "def target(x):\n    return x\n")
        findings = [{
            "id": "F1", "label": "ACCEPT", "severity": "High",
            "file": "core/sample.py", "line": 1, "claim": "test",
        }]
        _make_findings_json(tmp_path, findings, round_=2)

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="", returncode=0)
            ret = rc.main(str(tmp_path))

        assert ret == 0
        ev_path = tmp_path / ".af_review_queue" / "cr_evidence.json"
        assert ev_path.exists()
        ev = json.loads(ev_path.read_text())
        assert ev["round"] == 2
        assert len(ev["evidence"]) == 1
        assert ev["evidence"][0]["id"] == "F1"

    def test_mixed_findings_only_accept_gets_evidence(self, tmp_path):
        _make_py(tmp_path, "core/sample.py", "def f(x): return x\n")
        findings = [
            {"id": "F1", "label": "ACCEPT", "severity": "High",
             "file": "core/sample.py", "line": 1, "claim": "c"},
            {"id": "F2", "label": "ACCEPT-ADV", "severity": "Medium",
             "file": "core/sample.py", "line": 1, "claim": "c"},
            {"id": "F3", "label": "REJECTED", "file": None, "line": None, "claim": "c"},
        ]
        _make_findings_json(tmp_path, findings)

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="", returncode=0)
            ret = rc.main(str(tmp_path))

        assert ret == 0
        ev = json.loads((tmp_path / ".af_review_queue" / "cr_evidence.json").read_text())
        assert len(ev["evidence"]) == 3
        accept_ev = [e for e in ev["evidence"] if e["id"] == "F1"]
        adv_ev = [e for e in ev["evidence"] if e["id"] == "F2"]
        assert "surrounding_code" in accept_ev[0]
        assert adv_ev[0]["skip_reason"] == "non-blocking label"

    def test_round_preserved_in_output(self, tmp_path):
        _make_findings_json(tmp_path, [], round_=5)
        rc.main(str(tmp_path))
        ev = json.loads((tmp_path / ".af_review_queue" / "cr_evidence.json").read_text())
        assert ev["round"] == 5

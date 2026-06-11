"""tests/test_provider_instruction_sync.py — INV-1~8 for WI-A provider instruction SSOT."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _hook_text() -> str:
    return (REPO_ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")


def _markers() -> tuple[str, str]:
    from scripts.sync_provider_instructions import MARKER_START, MARKER_END
    return MARKER_START, MARKER_END


def _extract_between_markers(text: str) -> str:
    start_marker, end_marker = _markers()
    start = text.find(start_marker)
    end = text.find(end_marker)
    assert start != -1, "AF-COMMON-START missing"
    assert end != -1, "AF-COMMON-END missing"
    return text[start + len(start_marker) : end].strip("\n")


# ---------------------------------------------------------------------------
# INV-1: 3파일 모두 AF-COMMON-START / AF-COMMON-END 마커 존재
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", ["CLAUDE.md", "GEMINI.md", "AGENTS.md"])
def test_inv1_start_marker_present(filename):
    start_marker, _ = _markers()
    assert start_marker in _read(filename), f"{filename}: AF-COMMON-START marker missing"


@pytest.mark.parametrize("filename", ["CLAUDE.md", "GEMINI.md", "AGENTS.md"])
def test_inv1_end_marker_present(filename):
    _, end_marker = _markers()
    assert end_marker in _read(filename), f"{filename}: AF-COMMON-END marker missing"


# ---------------------------------------------------------------------------
# INV-2: 각 파일 마커 사이 내용 == INSTRUCTIONS.md 공통 블록 (drift 0)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", ["CLAUDE.md", "GEMINI.md", "AGENTS.md"])
def test_inv2_no_drift(filename):
    instructions = _read("INSTRUCTIONS.md").strip("\n")
    block = _extract_between_markers(_read(filename))
    assert block == instructions, (
        f"{filename}: common block drifted from INSTRUCTIONS.md\n"
        f"Run: python scripts/sync_provider_instructions.py"
    )


# ---------------------------------------------------------------------------
# INV-3: sync 멱등 (2회 실행 = 1회 결과)
# ---------------------------------------------------------------------------

def test_inv3_idempotent(tmp_path: Path):
    from scripts.sync_provider_instructions import _inject_common_block, MARKER_START, MARKER_END

    common = "# Section\ncontent line 1\ncontent line 2"
    f = tmp_path / "test.md"
    f.write_text(
        "# Title\n" + MARKER_START + "\nstale content\n" + MARKER_END + "\n## Specific\n",
        encoding="utf-8",
    )

    changed_1st = _inject_common_block(f, common)
    assert changed_1st, "First run should report a change"
    after_1st = f.read_text(encoding="utf-8")

    changed_2nd = _inject_common_block(f, common)
    assert not changed_2nd, "Second run should report no change (idempotent)"
    after_2nd = f.read_text(encoding="utf-8")

    assert after_1st == after_2nd, "Second run must not alter the file"


# ---------------------------------------------------------------------------
# INV-4: AGENTS.md에 에이전트 명단 + 공통 블록 둘 다 존재
# ---------------------------------------------------------------------------

def test_inv4_agents_md_has_roster_section():
    assert "## Agents" in _read("AGENTS.md"), "AGENTS.md: roster section (## Agents) missing"


def test_inv4_agents_md_has_common_block():
    start_marker, _ = _markers()
    assert start_marker in _read("AGENTS.md"), "AGENTS.md: common block marker missing"


def test_inv4_agents_yaml_ids_in_roster():
    text = _read("AGENTS.md")
    agents_dir = REPO_ROOT / "agents"
    yaml_files = list(agents_dir.rglob("*.yaml")) + list(agents_dir.rglob("*.yml"))
    assert yaml_files, "No agent YAML files found in agents/"
    assert any(p.stem in text for p in yaml_files), "No agent IDs appear in AGENTS.md roster"


# ---------------------------------------------------------------------------
# INV-5: 마커 누락 파일에 sync → 명시적 에러 (silent pass 금지)
# ---------------------------------------------------------------------------

def test_inv5_missing_start_marker_raises(tmp_path: Path):
    from scripts.sync_provider_instructions import _inject_common_block, MARKER_END

    f = tmp_path / "no_start.md"
    f.write_text("content\n" + MARKER_END + "\nmore", encoding="utf-8")
    with pytest.raises(ValueError, match="AF-COMMON"):
        _inject_common_block(f, "block")


def test_inv5_missing_end_marker_raises(tmp_path: Path):
    from scripts.sync_provider_instructions import _inject_common_block, MARKER_START

    f = tmp_path / "no_end.md"
    f.write_text(MARKER_START + "\ncontent without end", encoding="utf-8")
    with pytest.raises(ValueError, match="AF-COMMON"):
        _inject_common_block(f, "block")


def test_inv5_no_instructions_file_returns_error(tmp_path: Path):
    from scripts.sync_provider_instructions import sync

    # No INSTRUCTIONS.md in tmp_path — sync must fail with non-zero exit
    result = sync(workspace=str(tmp_path))
    assert result != 0, "sync must fail when INSTRUCTIONS.md is missing"


# ---------------------------------------------------------------------------
# INV-6: AgentRecord / collect_records 재선언 0 (import only)
# ---------------------------------------------------------------------------

def test_inv6_no_redeclare_agent_record():
    text = (REPO_ROOT / "scripts" / "sync_provider_instructions.py").read_text(encoding="utf-8")
    assert "class AgentRecord" not in text, "sync_provider_instructions must not redeclare AgentRecord"


def test_inv6_no_redeclare_collect_records():
    text = (REPO_ROOT / "scripts" / "sync_provider_instructions.py").read_text(encoding="utf-8")
    assert "def collect_records" not in text, "sync_provider_instructions must not redeclare collect_records"


def test_inv6_sync_imports_from_generate_agents_md():
    text = (REPO_ROOT / "scripts" / "sync_provider_instructions.py").read_text(encoding="utf-8")
    assert "generate_agents_md" in text, "sync must reference generate_agents_md (import source)"


# ---------------------------------------------------------------------------
# INV-7: pre-commit 트리거 + 실패 시 차단 (|| true 부재)
# ---------------------------------------------------------------------------

def test_inv7_precommit_calls_sync_script():
    assert "sync_provider_instructions.py" in _hook_text()


def test_inv7_precommit_triggers_on_instructions_md():
    hook = _hook_text()
    assert "INSTRUCTIONS" in hook, "pre-commit must trigger on INSTRUCTIONS.md changes"


def test_inv7_precommit_triggers_on_agents_yaml():
    hook = _hook_text()
    assert "agents/" in hook and ("yaml" in hook.lower() or "yml" in hook.lower())


def test_inv7_no_or_true_on_sync_call():
    hook = _hook_text()
    for line in hook.splitlines():
        if "sync_provider_instructions.py" in line:
            assert "|| true" not in line, (
                f"sync call must not suppress failure with '|| true': {line}"
            )


def test_inv7_exit_1_path_exists_after_sync_failure():
    hook = _hook_text()
    # The hook must contain a conditional exit 1 after the sync call
    assert "SYNC_EXIT" in hook or ("sync_provider_instructions" in hook and "exit 1" in hook)


# ---------------------------------------------------------------------------
# INV-8: generate_agents_md.py → roster 라이브러리화, main() 직접 write 금지
# ---------------------------------------------------------------------------

def test_inv8_render_roster_function_exists():
    text = (REPO_ROOT / "scripts" / "generate_agents_md.py").read_text(encoding="utf-8")
    assert "def render_roster" in text, "generate_agents_md.py missing render_roster() function"


def test_inv8_render_roster_no_markers():
    from scripts.generate_agents_md import render_roster, AgentRecord

    records = [
        AgentRecord(
            kind="file", agent_id="test_agent", name="Test Agent",
            role="Dev", role_type="Dev", emoji="☠️",
            source="agents/test_agent.yaml",
        )
    ]
    result = render_roster(records, agents_dir_label="agents")
    assert "test_agent" in result, "render_roster must include agent ID"
    assert "AF-COMMON-START" not in result, "render_roster must not include AF-COMMON markers"
    assert "AF-COMMON-END" not in result, "render_roster must not include AF-COMMON markers"


def test_inv8_main_does_not_write_agents_md_directly():
    text = (REPO_ROOT / "scripts" / "generate_agents_md.py").read_text(encoding="utf-8")
    # Find the main() function body
    main_match = re.search(r"\ndef main\(\)[^\n]*\n(.*?)(?=\n(?:def |\Z))", text, re.DOTALL)
    if main_match:
        main_body = main_match.group(1)
        assert "write_text" not in main_body, (
            "generate_agents_md.main() must not call write_text directly — "
            "AGENTS.md write responsibility belongs to sync_provider_instructions"
        )

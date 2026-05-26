"""Regression tests for scripts.blueprint_updater."""
from __future__ import annotations

from pathlib import Path

from scripts import blueprint_updater as bu


def _minimal_blueprint() -> str:
    return """# Master Blueprint

## §3 핵심 서브시스템

### §3.1 Existing

Existing prose.

---

## §4 Other

---

## §12 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
"""


def test_update_blueprint_writes_section3_auto_summary(tmp_path, monkeypatch):
    workspace = tmp_path
    core_dir = workspace / "core"
    core_dir.mkdir()
    (core_dir / "example.py").write_text(
        '"""Example subsystem contract."""\n\n'
        "class ExampleState:\n"
        "    pass\n\n"
        "def run_example():\n"
        "    return True\n",
        encoding="utf-8",
    )
    blueprint = workspace / "Master_Blueprint.md"
    blueprint.write_text(_minimal_blueprint(), encoding="utf-8")

    monkeypatch.setattr(bu, "_changed_files", lambda _workspace: ["core/example.py"])
    monkeypatch.setattr(bu, "_short_commit", lambda _workspace: "abc1234")
    monkeypatch.setattr(bu, "_read_version", lambda _workspace: "v1.2.3")

    updated = bu.update_blueprint(str(workspace), "test update", no_llm=True)

    text = blueprint.read_text(encoding="utf-8")
    assert updated is True
    assert bu.SECTION3_AUTO_START in text
    assert "### §3.12 자동 Core 변경 요약" in text
    assert "`core/example.py`" in text
    assert "Example subsystem contract." in text
    assert "`ExampleState`" in text
    assert "`run_example()`" in text

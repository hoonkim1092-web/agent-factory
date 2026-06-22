from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRE_COMMIT = REPO_ROOT / ".githooks" / "pre-commit"


def _hook_text() -> str:
    return PRE_COMMIT.read_text(encoding="utf-8")


def test_precommit_regenerates_llm_wiki_for_source_docs():
    hook = _hook_text()

    assert "scripts/build_llm_wiki.py" in hook
    assert "Master_Blueprint\\.md" in hook
    assert "docs/code_review/code-review\\.md" in hook
    assert "NEXT_STEPS\\.md" in hook


def test_precommit_regenerates_llm_wiki_for_python_symbol_changes():
    hook = _hook_text()

    assert "WIKI_TRIGGER=" in hook
    assert "\\.py$" in hook
    assert "git add docs/wiki/code/" in hook
    assert "git add docs/wiki/" in hook

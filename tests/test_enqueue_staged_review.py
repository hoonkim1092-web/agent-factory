import json
import subprocess
import sys
from pathlib import Path


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def test_enqueue_staged_review_targets_staged_python_without_provider_hooks(tmp_path):
    from scripts.enqueue_staged_review import enqueue_staged

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    target = scripts_dir / "tool.py"
    target.write_text("def first():\n    return 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")

    target.write_text("def second():\n    return 2\n", encoding="utf-8")
    _git(repo, "add", "scripts/tool.py")

    enqueued = enqueue_staged(str(repo))

    assert enqueued == ["scripts/tool.py"]
    pending = repo / ".af_review_queue" / "pending_agent_review.json"
    data = json.loads(pending.read_text(encoding="utf-8"))
    assert data["files"] == ["scripts/tool.py"]


def test_precommit_invokes_provider_neutral_staged_enqueue():
    hook = Path(".githooks/pre-commit").read_text(encoding="utf-8")

    assert "scripts/enqueue_staged_review.py" in hook
    assert "scripts/review_gate.py\" --check" in hook
    assert hook.index("scripts/enqueue_staged_review.py") < hook.index("scripts/review_gate.py\" --check")


def test_enqueue_staged_review_uses_module_path_under_pyinstaller_frozen_build(monkeypatch, tmp_path):
    import scripts.enqueue_staged_review as m

    # PyInstaller frozen build parity: sys.executable may point at dist/af/af.exe
    # and sys._MEIPASS may point at an unpack directory, but the helper must still
    # resolve the repo script directory from the module __file__ path.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_MEIPASS"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "dist" / "af" / "af.exe"))

    assert m._script_dir() == Path(m.__file__).resolve().parent


def test_enqueue_staged_review_does_not_make_completed_reviews_stale(tmp_path):
    from scripts.enqueue_staged_review import enqueue_staged
    from scripts.review_gate import is_gate_blocked, record_review_done

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    target = scripts_dir / "tool.py"
    target.write_text("def first():\n    return 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")

    target.write_text("def second():\n    return 2\n", encoding="utf-8")
    _git(repo, "add", "scripts/tool.py")

    enqueue_staged(str(repo))
    files = ["scripts/tool.py"]
    record_review_done(str(repo), "af-test-runner", 1, "pass", files)
    record_review_done(str(repo), "af-critic", 2, "pass", files, t3_required="unknown")
    record_review_done(str(repo), "af-cross-review", 3, "pass", files)

    assert is_gate_blocked(str(repo), staged_py=files) == (False, "all-tiers-passed")

    enqueue_staged(str(repo))

    assert is_gate_blocked(str(repo), staged_py=files) == (False, "all-tiers-passed")

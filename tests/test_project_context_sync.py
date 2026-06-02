from pathlib import Path

from scripts.project_context_sync import (
    _normalize_newlines,
    collect_snapshot,
    read_text,
    resolve_project_root,
    write_text,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_snapshot_excludes_docs_task_by_default(tmp_path: Path):
    _write(tmp_path / "docs" / "task.md", "should_be_excluded")
    _write(tmp_path / "docs" / "keep.md", "should_remain")

    payload = collect_snapshot(tmp_path, "agent_factory", None, 10)
    files = payload.get("files", {})

    assert "docs/task.md" not in files
    assert "docs/keep.md" in files


def test_collect_snapshot_excludes_docs_archive_by_default(tmp_path: Path):
    _write(tmp_path / "docs" / "archive" / "old-design.md", "should_be_excluded")
    _write(tmp_path / "docs" / "keep.md", "should_remain")

    payload = collect_snapshot(tmp_path, "agent_factory", None, 10)
    files = payload.get("files", {})

    assert "docs/archive/old-design.md" not in files
    assert "docs/keep.md" in files


def test_collect_snapshot_applies_env_excludes(tmp_path: Path, monkeypatch):
    _write(tmp_path / "docs" / "keep.md", "exclude_me")
    monkeypatch.setenv("CONTEXT_SYNC_EXCLUDE", "docs/keep.md")

    payload = collect_snapshot(tmp_path, "agent_factory", None, 10)
    files = payload.get("files", {})

    assert "docs/keep.md" not in files


def test_collect_snapshot_applies_env_exclude_glob(tmp_path: Path, monkeypatch):
    _write(tmp_path / "docs" / "tmp.plan.md", "exclude_glob")
    _write(tmp_path / "docs" / "guide.md", "keep")
    monkeypatch.setenv("CONTEXT_SYNC_EXCLUDE", "docs/*.plan.md")

    payload = collect_snapshot(tmp_path, "agent_factory", None, 10)
    files = payload.get("files", {})

    assert "docs/tmp.plan.md" not in files
    assert "docs/guide.md" in files


def test_resolve_project_root_prefers_local_project_when_repo_name_collides(tmp_path: Path):
    repo_root = tmp_path / "agent-factory"
    local_project = repo_root / "projects" / "agent_factory"
    local_project.mkdir(parents=True, exist_ok=True)

    sync_id, resolved = resolve_project_root(repo_root, "agent-factory")

    assert sync_id == "project_agent_factory"
    assert resolved == local_project


def test_resolve_project_root_supports_explicit_repo_alias(tmp_path: Path):
    repo_root = tmp_path / "agent-factory"
    (repo_root / "projects" / "agent_factory").mkdir(parents=True, exist_ok=True)

    sync_id, resolved = resolve_project_root(repo_root, "@repo")

    assert sync_id == "agent_factory"
    assert resolved == repo_root


def test_resolve_project_root_supports_powershell_safe_repo_alias(tmp_path: Path):
    repo_root = tmp_path / "agent-factory"
    (repo_root / "projects" / "agent_factory").mkdir(parents=True, exist_ok=True)

    sync_id, resolved = resolve_project_root(repo_root, "repo")

    assert sync_id == "agent_factory"
    assert resolved == repo_root


def test_resolve_project_root_normalizes_project_path_to_collision_safe_sync_id(tmp_path: Path):
    repo_root = tmp_path / "agent-factory"
    local_project = repo_root / "projects" / "agent_factory"
    local_project.mkdir(parents=True, exist_ok=True)

    sync_id, resolved = resolve_project_root(repo_root, "projects/agent_factory")

    assert sync_id == "project_agent_factory"
    assert resolved == local_project


# --- 줄바꿈 정규화 (CRLF 누적 버그 fix 회귀) ---------------------------------


def test_normalize_newlines_variants():
    # CRLF / 다중 CR / triple CR / lone CR / LF / mixed 모두 LF로 수렴
    assert _normalize_newlines("a\r\nb") == "a\nb"
    assert _normalize_newlines("a\r\r\nb") == "a\nb"      # 다중 CR → 빈 줄 아님
    assert _normalize_newlines("a\r\r\r\nb") == "a\nb"
    assert _normalize_newlines("a\rb") == "a\nb"          # lone CR
    assert _normalize_newlines("a\nb") == "a\nb"          # LF 보존
    assert _normalize_newlines("a\r\nb\r\r\nc\rd") == "a\nb\nc\nd"


def test_normalize_newlines_does_not_duplicate_lines():
    # 다중 CR이 빈 줄(\n\n)로 폭증하지 않아야 한다 (회귀: 250 insertions 버그)
    assert _normalize_newlines("x\r\r\ny").count("\n") == 1


def test_write_text_emits_lf_only(tmp_path: Path):
    # write_text는 OS와 무관하게 LF만 기록 (Windows text mode \n→\r\n 차단)
    p = tmp_path / "out.yaml"
    write_text(p, "a\nb\nc\n")
    assert b"\r" not in p.read_bytes()
    assert p.read_bytes() == b"a\nb\nc\n"


def test_write_text_normalizes_crlf_input(tmp_path: Path):
    # CRLF/다중 CR content를 받아도 디스크에는 LF만 기록
    p = tmp_path / "out.yaml"
    write_text(p, "a\r\nb\r\r\nc")
    assert b"\r" not in p.read_bytes()
    assert p.read_bytes() == b"a\nb\nc"


def test_read_write_round_trip_is_stable(tmp_path: Path):
    # round-trip이 CR을 누적하지 않아야 한다 (sync 반복 시 \r\n→\r\r\n 방지)
    p = tmp_path / "rt.yaml"
    write_text(p, "line1\r\nline2\r\r\nline3")
    first = read_text(p)
    write_text(p, first)
    second = read_text(p)
    assert first == second == "line1\nline2\nline3"
    assert b"\r" not in p.read_bytes()

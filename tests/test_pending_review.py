"""tests/test_pending_review.py — check_pending_review + enqueue_agent_review 단위 테스트."""
import importlib
import json
import os
import sys
import time


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_marker(tmp_path, data: dict):
    q = tmp_path / ".af_review_queue"
    q.mkdir(exist_ok=True)
    (q / "pending_agent_review.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


def _read_marker(tmp_path) -> dict | None:
    p = tmp_path / ".af_review_queue" / "pending_agent_review.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _check_main(tmp_path, monkeypatch):
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    m.main()


def _enqueue_main(tmp_path, monkeypatch, relpath: str):
    """relpath는 'core/foo.py' 형식의 workspace 상대경로. 절대경로로 변환해 전달."""
    import scripts.enqueue_agent_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    abs_fp = str(tmp_path / relpath.replace("/", os.sep))
    monkeypatch.setattr(sys, "argv", ["enqueue_agent_review.py", abs_fp])
    m.main()


# ── check_pending_review tests ────────────────────────────────────────────────

def test_no_marker_silent(tmp_path, monkeypatch, capsys):
    _check_main(tmp_path, monkeypatch)
    assert capsys.readouterr().out == ""


def test_first_fire_suppressed_within_batch_interval(tmp_path, monkeypatch, capsys):
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": time.time(),  # just now
        "updated_at": time.time(),
    })
    _check_main(tmp_path, monkeypatch)
    assert "[af-review-pending]" not in capsys.readouterr().out


def test_first_fire_triggers_after_interval(tmp_path, monkeypatch, capsys):
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
    })
    m.main()
    assert "[af-review-pending]" in capsys.readouterr().out


def test_first_fire_writes_fired_at(tmp_path, monkeypatch, capsys):
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
    })
    m.main()
    data = _read_marker(tmp_path)
    assert data is not None
    assert "fired_at" in data
    assert data["fired_at"] > 0


def test_refires_when_updated_at_newer_than_fired_at(tmp_path, monkeypatch, capsys):
    t_fired = time.time() - 100
    t_updated = time.time() - 50  # newer than fired
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": t_fired - 200,
        "updated_at": t_updated,
        "fired_at": t_fired,
    })
    m.main()
    assert "[af-review-pending]" in capsys.readouterr().out


def test_no_refire_when_updated_at_older_than_fired_at(tmp_path, monkeypatch, capsys):
    t_fired = time.time()
    t_updated = t_fired - 100  # older than fired
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": t_updated - 200,
        "updated_at": t_updated,
        "fired_at": t_fired,
    })
    m.main()
    assert capsys.readouterr().out == ""


def test_empty_files_list_silent(tmp_path, monkeypatch, capsys):
    _write_marker(tmp_path, {"files": [], "created_at": time.time() - 400})
    _check_main(tmp_path, monkeypatch)
    assert capsys.readouterr().out == ""


def test_marker_kept_after_fire(tmp_path, monkeypatch, capsys):
    """마커는 삭제되지 않고 fired_at이 기록된 채 유지된다."""
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
    })
    m.main()
    assert _read_marker(tmp_path) is not None


# ── enqueue_agent_review tests ────────────────────────────────────────────────

def test_enqueue_creates_marker_for_core_py(tmp_path, monkeypatch):
    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")
    data = _read_marker(tmp_path)
    assert data is not None
    assert "core/foo.py" in data["files"]
    assert "updated_at" in data


def test_enqueue_skips_non_review_file(tmp_path, monkeypatch):
    _enqueue_main(tmp_path, monkeypatch, "docs/readme.md")
    assert _read_marker(tmp_path) is None


def test_enqueue_always_refreshes_updated_at_for_existing_file(tmp_path, monkeypatch):
    """이미 큐에 있는 파일을 재편집해도 updated_at이 갱신된다 (재발화 가능 조건)."""
    t_before = time.time() - 50
    _write_marker(tmp_path, {
        "files": ["core/foo.py"],
        "created_at": t_before,
        "updated_at": t_before,
        "fired_at": t_before + 10,  # 이미 발화된 상태
    })
    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")
    data = _read_marker(tmp_path)
    # updated_at이 fired_at보다 커야 재발화 가능
    assert data["updated_at"] > data["fired_at"]


def test_enqueue_deduplicates_file_list(tmp_path, monkeypatch):
    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")
    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")
    data = _read_marker(tmp_path)
    assert data["files"].count("core/foo.py") == 1


def test_enqueue_accumulates_multiple_files(tmp_path, monkeypatch):
    _enqueue_main(tmp_path, monkeypatch, "core/a.py")
    _enqueue_main(tmp_path, monkeypatch, "core/b.py")
    data = _read_marker(tmp_path)
    assert set(data["files"]) == {"core/a.py", "core/b.py"}


def test_enqueue_atomic_write_produces_valid_json(tmp_path, monkeypatch):
    _enqueue_main(tmp_path, monkeypatch, "core/x.py")
    p = tmp_path / ".af_review_queue" / "pending_agent_review.json"
    assert p.exists()
    parsed = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(parsed["files"], list)

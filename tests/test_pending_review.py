"""tests/test_pending_review.py — check_pending_review + enqueue_agent_review 단위 테스트."""
import importlib
import json
import os
import sys
import time
import types


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


def test_first_fire_t3_skip_prints_two_agents(tmp_path, monkeypatch, capsys):
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["core/cosmetic.py"],
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
        "blast_tier": 2,
        "t3_required": False,
        "t3_decision": {
            "decision": "skip_t3",
            "reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": ["core/cosmetic.py"],
            "diff_summary": {"added": 1, "deleted": 1},
        },
    })
    m.main()
    out = capsys.readouterr().out
    assert "af-test-runner" in out
    assert "af-critic" in out
    assert "af-cross-review" not in out


def test_first_fire_t3_skip_ignored_for_blast_tier3_guidance(tmp_path, monkeypatch, capsys):
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    _write_marker(tmp_path, {
        "files": ["scripts/t3_classifier.py"],
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
        "blast_tier": 3,
        "t3_required": False,
        "t3_decision": {
            "decision": "skip_t3",
            "reason": "cosmetic-only-python-ast",
            "classifier_version": "t3-deterministic-v1",
            "files": ["scripts/t3_classifier.py"],
            "diff_summary": {"added": 1, "deleted": 1},
        },
    })
    m.main()
    out = capsys.readouterr().out
    assert "af-cross-review" in out


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


def test_first_fire_debounced_by_recent_reedit(tmp_path, monkeypatch, capsys):
    """회귀: created_at 오래됐어도 updated_at이 최근이면 첫 발화 억제 (debounce 의도 부합).

    이전 버그: elapsed = now - created_at → created_at 기준이라 오래된 마커 +
    최근 재편집 시 즉시 발화. 수정 후: elapsed = now - updated_at.
    """
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 90)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    now = time.time()
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": now - 500,   # 오래됨 (이전 버그 재현 조건)
        "updated_at": now - 5,     # 방금 재편집
    })
    m.main()
    assert "[af-review-pending]" not in capsys.readouterr().out


def test_first_fire_uses_updated_at_not_created_at(tmp_path, monkeypatch, capsys):
    """updated_at 기준으로 발화 조건이 계산되는지 확인 (created_at 기준 버그 회귀 방지)."""
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 30)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    now = time.time()
    # updated_at이 충분히 오래됐으면 created_at이 더 최근이어도 발화해야 함
    # (현실에선 발생 안 하지만, 기준 필드 검증용)
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "created_at": now - 10,
        "updated_at": now - 100,  # 이건 실제론 불가능하지만 기준 필드 확인 목적
    })
    m.main()
    assert "[af-review-pending]" in capsys.readouterr().out


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


# ── rate_limited skip tests ───────────────────────────────────────────────────

def test_t3_skipped_when_all_external_rate_limited(tmp_path, monkeypatch, capsys):
    """외부 프로바이더 전부 rate_limited → af-cross-review 없이 af-critic → af-test-runner만 발화."""
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_all_external_providers_rate_limited", lambda: True)
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "blast_tier": 2,
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
    })
    m.main()
    out = capsys.readouterr().out
    assert "[af-review-pending]" in out
    # 에이전트 목록 라인에만 af-cross-review가 없어야 한다 (instruction에 "스킵" 언급은 허용)
    agent_line = next(l for l in out.splitlines() if "실행 에이전트:" in l)
    assert "af-cross-review" not in agent_line
    assert "af-critic" in agent_line
    assert "af-test-runner" in agent_line
    assert "rate_limited" in out


def test_t3_included_when_no_rate_limit(tmp_path, monkeypatch, capsys):
    """외부 프로바이더 정상이면 af-cross-review 포함 발화."""
    import scripts.check_pending_review as m
    importlib.reload(m)
    monkeypatch.setattr(m, "MIN_BATCH_INTERVAL_SEC", 0)
    monkeypatch.setattr(m, "_detect_workspace", lambda: str(tmp_path))
    monkeypatch.setattr(m, "_all_external_providers_rate_limited", lambda: False)
    _write_marker(tmp_path, {
        "files": ["core/x.py"],
        "blast_tier": 2,
        "created_at": time.time() - 400,
        "updated_at": time.time() - 400,
    })
    m.main()
    out = capsys.readouterr().out
    assert "af-cross-review" in out


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


def test_enqueue_t3_classifier_stale_file_set_fails_closed(tmp_path, monkeypatch):
    class FakeDecision:
        t3_required = False
        classifier_version = "test"
        files = ["core/new.py"]
        diff_summary = {"added": 1, "deleted": 1}

        def to_state(self):
            return {
                "decision": "skip_t3",
                "reason": "cosmetic-only-python-ast",
                "classifier_version": self.classifier_version,
                "files": self.files,
                "diff_summary": self.diff_summary,
            }

    fake = types.SimpleNamespace(
        CLASSIFIER_VERSION="test",
        classify_t3_requirement=lambda workspace, files: FakeDecision(),
        record_skip_telemetry=lambda workspace, decision: None,
    )
    monkeypatch.setitem(sys.modules, "t3_classifier", fake)
    _write_marker(tmp_path, {
        "files": ["core/existing.py"],
        "created_at": time.time() - 10,
        "updated_at": time.time() - 10,
    })

    _enqueue_main(tmp_path, monkeypatch, "core/new.py")

    data = _read_marker(tmp_path)
    assert data["t3_required"] is True
    assert data["t3_decision"]["reason"] == "classifier-stale-file-set"


def test_enqueue_telemetry_failure_does_not_drop_marker(tmp_path, monkeypatch):
    class FakeDecision:
        t3_required = False
        classifier_version = "test"
        files = ["core/foo.py"]
        diff_summary = {"added": 1, "deleted": 1}

        def to_state(self):
            return {
                "decision": "skip_t3",
                "reason": "cosmetic-only-python-ast",
                "classifier_version": "t3-deterministic-v1",
                "files": self.files,
                "diff_summary": self.diff_summary,
            }

    fake = types.SimpleNamespace(
        CLASSIFIER_VERSION="test",
        classify_t3_requirement=lambda workspace, files: FakeDecision(),
        record_skip_telemetry=lambda workspace, decision: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setitem(sys.modules, "t3_classifier", fake)

    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")

    data = _read_marker(tmp_path)
    assert data is not None
    assert data["files"] == ["core/foo.py"]
    assert data["t3_required"] is False


def test_enqueue_classifier_unavailable_fails_closed_over_stale_skip(tmp_path, monkeypatch):
    fake = types.SimpleNamespace(
        classify_t3_requirement=lambda workspace, files: (_ for _ in ()).throw(RuntimeError("boom")),
        record_skip_telemetry=lambda workspace, decision: None,
    )
    monkeypatch.setitem(sys.modules, "t3_classifier", fake)
    _write_marker(tmp_path, {
        "files": ["core/foo.py"],
        "created_at": time.time() - 10,
        "updated_at": time.time() - 10,
        "t3_required": False,
        "t3_decision": {"decision": "skip_t3", "reason": "old"},
    })

    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")

    data = _read_marker(tmp_path)
    assert data["t3_required"] is True
    assert data["t3_decision"]["reason"] == "classifier-unavailable"


# ── Phase 4: enqueue telemetry skip 배선 ───────────────────────────────────────

def _seed_clean_metrics(tmp_path, n=12, span_days=8.0):
    """telemetry skip=True를 유도하는 깨끗한 T3 메트릭 n개 커밋 기록."""
    import datetime as _dt
    q = tmp_path / ".af_review_queue"
    q.mkdir(exist_ok=True)
    base = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
    step = span_days / (n - 1)
    lines = []
    for i in range(n):
        ts = (base + _dt.timedelta(days=i * step)).isoformat()
        for tier, agent in ((2, "af-critic"), (3, "af-cross-review")):
            lines.append(json.dumps({
                "ts": ts, "commit_sha": f"sha{i + 1:03d}", "tier": tier,
                "agent": agent, "verdict": "pass", "findings_count": 0,
            }))
    (q / "review_metrics.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_enqueue_stores_telemetry_skip_and_logs_once(tmp_path, monkeypatch):
    """비위험 파일 + telemetry skip=True → marker에 결정 동결 + skip_audit 1회 기록."""
    _seed_clean_metrics(tmp_path)
    _enqueue_main(tmp_path, monkeypatch, "core/foo.py")

    data = _read_marker(tmp_path)
    decision = data.get("t3_telemetry_skip")
    assert isinstance(decision, dict)
    assert decision["skip"] is True
    assert decision["reason"] == "t3-redundant"
    assert data.get("blast_tier") == 2

    audit_path = tmp_path / ".af_review_queue" / "skip_audit.jsonl"
    assert audit_path.exists()
    recs = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(recs) == 1
    assert recs[0]["skipped_tier"] == 3
    assert recs[0]["reason"] == "t3-redundant"

    # 같은 라운드 재편집 → skip_audit 중복 기록 없음 (라운드당 1회 멱등)
    _enqueue_main(tmp_path, monkeypatch, "core/bar.py")
    recs2 = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(recs2) == 1


def test_enqueue_risk_file_no_telemetry_skip_log(tmp_path, monkeypatch):
    """위험군 파일은 telemetry skip 결정이 있어도 발효 안 됨 → skip_audit 미기록."""
    _seed_clean_metrics(tmp_path)
    _enqueue_main(tmp_path, monkeypatch, "scripts/review_gate.py")

    data = _read_marker(tmp_path)
    # 결정 자체는 동결되나 (forensic), 발효되지 않으므로 audit 미기록
    assert data.get("t3_telemetry_skip", {}).get("skip") is True
    audit_path = tmp_path / ".af_review_queue" / "skip_audit.jsonl"
    assert not audit_path.exists()

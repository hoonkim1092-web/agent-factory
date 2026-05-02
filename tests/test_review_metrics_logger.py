"""tests/test_review_metrics_logger.py — Phase 3.5 메트릭 수집 단위 테스트."""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def metrics_mod():
    import scripts.review_metrics_logger as m
    importlib.reload(m)
    return m


@pytest.fixture()
def ws(tmp_path):
    """임시 workspace + .af_review_queue 디렉토리."""
    q = tmp_path / ".af_review_queue"
    q.mkdir()
    return str(tmp_path)


# ── parse_findings_count ──────────────────────────────────────────────────────

def test_findings_count_empty(metrics_mod):
    assert metrics_mod.parse_findings_count("") == 0


def test_findings_count_single_accept_star(metrics_mod):
    assert metrics_mod.parse_findings_count("verdict: [ACCEPT★] 좋음") == 1


def test_findings_count_warn(metrics_mod):
    assert metrics_mod.parse_findings_count("이슈: [WARN] 경고") == 1


def test_findings_count_block(metrics_mod):
    assert metrics_mod.parse_findings_count("[BLOCK] critical") == 1


def test_findings_count_multiple(metrics_mod):
    content = "[ACCEPT★] 좋음\n[WARN] 경고\n[BLOCK] 위험"
    assert metrics_mod.parse_findings_count(content) == 3


def test_findings_count_no_false_positive(metrics_mod):
    content = "일반 텍스트에 ACCEPT 키워드가 있어도 마커 없으면 카운트 안 됨"
    assert metrics_mod.parse_findings_count(content) == 0


def test_findings_count_rejected(metrics_mod):
    assert metrics_mod.parse_findings_count("[REJECTED] 기각") == 1


def test_findings_count_case_insensitive(metrics_mod):
    assert metrics_mod.parse_findings_count("[warn] lower case") == 1


# ── parse_extension_log_count ─────────────────────────────────────────────────

def test_ext_log_none_korean(metrics_mod):
    assert metrics_mod.parse_extension_log_count("Extension Log: 없음") == 0


def test_ext_log_none_english(metrics_mod):
    assert metrics_mod.parse_extension_log_count("Extension Log: None") == 0


def test_ext_log_scope_creep(metrics_mod):
    assert metrics_mod.parse_extension_log_count("Verdict: WARN [scope-creep]") == 6


def test_ext_log_items(metrics_mod):
    content = "Extension Log:\n- Read: core/foo.py\n- Read: core/bar.py\n\n다음 섹션"
    assert metrics_mod.parse_extension_log_count(content) == 2


def test_ext_log_single_item(metrics_mod):
    content = "Extension Log:\n- Read: scripts/test.py"
    assert metrics_mod.parse_extension_log_count(content) == 1


def test_ext_log_absent(metrics_mod):
    assert metrics_mod.parse_extension_log_count("본문 내용만 있음") == 0


def test_ext_log_colon_variants(metrics_mod):
    content = "Extension Log：없음"  # fullwidth colon
    assert metrics_mod.parse_extension_log_count(content) == 0


# ── append_metric ─────────────────────────────────────────────────────────────

def test_append_metric_creates_file(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-test-runner", 1, "pass")
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    assert os.path.exists(path)


def test_append_metric_valid_json(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-critic", 2, "warn", findings_count=1)
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    with open(path) as f:
        record = json.loads(f.readline())
    assert record["tier"] == 2
    assert record["agent"] == "af-critic"
    assert record["verdict"] == "warn"
    assert record["findings_count"] == 1


def test_append_metric_multiple_records(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-test-runner", 1, "pass")
    metrics_mod.append_metric(ws, "af-critic", 2, "warn")
    metrics_mod.append_metric(ws, "af-cross-review", 3, "block", findings_count=2)
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    lines = [l for l in Path(path).read_text().splitlines() if l]
    assert len(lines) == 3


def test_append_metric_required_fields(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-cross-review", 3, "pass")
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    record = json.loads(Path(path).read_text().strip())
    for field in ["ts", "commit_sha", "tier", "agent", "verdict",
                  "findings_count", "extension_log_count", "duration_ms", "tokens", "tool_calls",
                  "evidence_present", "evidence_items", "evidence_cited"]:
        assert field in record, f"missing field: {field}"


def test_append_metric_evidence_defaults(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-test-runner", 1, "pass")
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    record = json.loads(Path(path).read_text().strip())
    assert record["evidence_present"] is False
    assert record["evidence_items"] == 0
    assert record["evidence_cited"] == 0


def test_append_metric_evidence_values(metrics_mod, ws):
    metrics_mod.append_metric(
        ws, "af-critic", 2, "warn",
        evidence_present=True, evidence_items=3, evidence_cited=2,
    )
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    record = json.loads(Path(path).read_text().strip())
    assert record["evidence_present"] is True
    assert record["evidence_items"] == 3
    assert record["evidence_cited"] == 2


def test_append_metric_extension_log(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-critic", 2, "warn", extension_log_count=3)
    path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    record = json.loads(Path(path).read_text().strip())
    assert record["extension_log_count"] == 3


def test_append_skip_audit(metrics_mod, ws):
    metrics_mod.append_skip_audit(ws, skipped_tier=3, reason="tier-1-only", subsequent_block=False)
    path = os.path.join(ws, ".af_review_queue", "skip_audit.jsonl")
    assert os.path.exists(path)
    record = json.loads(Path(path).read_text().strip())
    assert record["skipped_tier"] == 3
    assert record["subsequent_block"] is False


# ── compute_report ────────────────────────────────────────────────────────────

def test_compute_report_empty(metrics_mod, ws):
    report = metrics_mod.compute_report(ws)
    assert "비어 있음" in report or "없음" in report


def test_compute_report_single_t3_block_only(metrics_mod, ws):
    """T3 BLOCK-only 커밋 감지: T1/T2 pass, T3 block."""
    metrics_mod.append_metric(ws, "af-test-runner", 1, "pass", findings_count=0)
    metrics_mod.append_metric(ws, "af-critic", 2, "pass", findings_count=0)
    metrics_mod.append_metric(ws, "af-cross-review", 3, "block", findings_count=1)
    report = metrics_mod.compute_report(ws)
    assert "T3 BLOCK-only 커밋: 1" in report


def test_compute_report_t3_rate_zero(metrics_mod, ws):
    """T2만 finding → T3-only rate 0%."""
    metrics_mod.append_metric(ws, "af-critic", 2, "warn", findings_count=3)
    metrics_mod.append_metric(ws, "af-cross-review", 3, "pass", findings_count=0)
    report = metrics_mod.compute_report(ws)
    assert "0.0%" in report


def test_compute_report_t3_rate_100(metrics_mod, ws):
    """T3만 finding → T3-only rate 100%."""
    metrics_mod.append_metric(ws, "af-cross-review", 3, "warn", findings_count=2)
    report = metrics_mod.compute_report(ws)
    assert "100.0%" in report


def test_compute_report_verdict_distribution(metrics_mod, ws):
    metrics_mod.append_metric(ws, "af-test-runner", 1, "pass")
    metrics_mod.append_metric(ws, "af-test-runner", 1, "fail")
    report = metrics_mod.compute_report(ws)
    assert "af-test-runner" in report
    assert "pass" in report or "fail" in report


def test_compute_report_phase4_guidance_low(metrics_mod, ws):
    """<10%: 공격적 skip 가능 안내 포함."""
    metrics_mod.append_metric(ws, "af-critic", 2, "warn", findings_count=20)
    metrics_mod.append_metric(ws, "af-cross-review", 3, "pass", findings_count=1)
    report = metrics_mod.compute_report(ws)
    assert "skip" in report.lower()


# ── hook_runner integration ───────────────────────────────────────────────────

def test_post_agent_record_writes_metric(tmp_path, monkeypatch):
    """_post_agent_record가 metrics logger를 호출함을 확인."""
    written = []

    import scripts.review_metrics_logger as rml
    monkeypatch.setattr(rml, "append_metric", lambda *a, **kw: written.append(kw))

    import scripts.hook_runner as hr
    importlib.reload(hr)
    monkeypatch.setattr(hr, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(hr, "_detect_workspace", lambda: str(tmp_path))

    # create .af_review_queue + pending JSON
    q = tmp_path / ".af_review_queue"
    q.mkdir()
    import json as _json
    (q / "pending_agent_review.json").write_text(_json.dumps({"files": [], "blast_tier": 1}))

    # Stub out review_gate imports
    import types
    fake_rg = types.ModuleType("scripts.review_gate")
    import re
    fake_rg._VERDICT_RE = re.compile(r"Verdict:\s*(\w+)", re.IGNORECASE)
    fake_rg._VERDICT_HEADER_RE = re.compile(r"## Verdict\s*\n\s*(\w+)", re.IGNORECASE)
    fake_rg.record_review_done = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "scripts.review_gate", fake_rg)

    # Stub test_gap_analyzer
    import types as _types
    fake_tga = _types.ModuleType("scripts.test_gap_analyzer")

    class _FakeReport:
        verdict = "PASS"
        gaps = []
    fake_tga.changed_files_from_pending = lambda ws: []
    fake_tga.changed_files_from_git = lambda ws: []
    fake_tga.git_diff = lambda *a, **kw: ""
    fake_tga.analyze_diff = lambda **kw: _FakeReport()
    monkeypatch.setitem(sys.modules, "scripts.test_gap_analyzer", fake_tga)

    # Stub metrics logger in sys.modules so monkeypatch takes effect
    monkeypatch.setitem(sys.modules, "scripts.review_metrics_logger", rml)

    payload = {
        "tool_input": {"subagent_type": "af-critic"},
        "tool_response": {"content": "Verdict: warn\n[WARN] 경고 1건\nExtension Log: 없음"},
    }
    hr._post_agent_record(payload)

    assert len(written) == 1
    kw = written[0]
    assert kw["agent"] == "af-critic"
    assert kw["tier"] == 2
    assert kw["verdict"] == "warn"
    assert kw["findings_count"] == 1
    assert kw["extension_log_count"] == 0

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


# Phase 2 v7 §5.6: 신규 라벨 매칭 케이스
def test_findings_count_accept_adv(metrics_mod):
    """`[ACCEPT-ADV]` Medium 3건 → findings_count = 3."""
    content = (
        "#### 1. [ACCEPT-ADV] [Medium] item 1\n"
        "#### 2. [ACCEPT-ADV] [Medium] item 2\n"
        "#### 3. [ACCEPT-ADV] [Medium] item 3\n"
    )
    assert metrics_mod.parse_findings_count(content) == 3


def test_findings_count_bonus(metrics_mod):
    """`[BONUS]` Critical 2건 → findings_count = 2."""
    content = (
        "#### 1. [BONUS] [Critical] off-scope item 1\n"
        "#### 2. [BONUS] [Critical] off-scope item 2\n"
    )
    assert metrics_mod.parse_findings_count(content) == 2


def test_findings_count_mixed_labels(metrics_mod):
    """혼합 (`[ACCEPT★]`, `[ACCEPT-ADV]`, `[REJECTED]`, `[BONUS]`) → 모두 카운트."""
    content = (
        "#### 1. [ACCEPT★] [High] item\n"
        "#### 2. [ACCEPT-ADV] [Medium] item\n"
        "#### 3. [REJECTED] item\n"
        "#### 4. [BONUS] [Critical] item\n"
    )
    assert metrics_mod.parse_findings_count(content) == 4


def test_findings_count_legacy_labels_still_match(metrics_mod):
    """회귀 보호: 기존 `[ACCEPT]` / `[WARN]` / `[BLOCK]` / `[REJECTED]` 4종 매칭 유지."""
    content = "[ACCEPT] a\n[WARN] b\n[BLOCK] c\n[REJECTED] d\n"
    assert metrics_mod.parse_findings_count(content) == 4


# Phase 2 v7 §7.6: false-positive 회귀 (Critic #8 보강 — 정책: 모두 카운트, 단순성 우선)
def test_findings_count_false_positive_in_markdown_fence(metrics_mod):
    """markdown 코드 fence 내부 라벨도 카운트 (단순성 우선 정책 — Phase 2 v5 §7.6 시나리오 5)."""
    content = (
        "여기는 정책 설명 블록입니다.\n"
        "```\n"
        "예시: 라벨 [ACCEPT-ADV] Medium은 advisory를 의미합니다.\n"
        "```\n"
    )
    # 정책 (v7): fence 내부/외부 분리 비용이 단순 grep을 깨트림 — 모두 카운트.
    assert metrics_mod.parse_findings_count(content) == 1


def test_findings_count_false_positive_in_prose_quote(metrics_mod):
    """prose 인용도 카운트 (단순성 우선 정책 — Phase 2 v5 §7.6 시나리오 6)."""
    content = '"라벨 [BONUS]를 새로 도입한다는 의미로 본문에 인용한 케이스"'
    assert metrics_mod.parse_findings_count(content) == 1


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
    """commits_with_t3 < 10 → Phase 4 판단 불가 (샘플 게이트)."""
    metrics_mod.append_metric(ws, "af-critic", 2, "warn", findings_count=20)
    metrics_mod.append_metric(ws, "af-cross-review", 3, "pass", findings_count=1)
    report = metrics_mod.compute_report(ws)
    assert "Phase 4 판단 불가" in report


def test_compute_report_phase4_guidance_sufficient(metrics_mod, ws):
    """commits_with_t3 >= 10이고 기간 >= 7일이면 t3_block_only 기반 guidance 출력."""
    # Write 10 pairs of T2+T3 records directly with timestamps spanning 8 days
    # so span_days >= 7 and commits_with_t3 == 10
    import datetime as _dt
    metrics_path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    base = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
    with open(metrics_path, "w", encoding="utf-8") as f:
        for i in range(10):
            sha = f"sha{i + 1:03d}"
            ts = (base + _dt.timedelta(days=i * 0.9)).isoformat()
            # T2 record: findings_count=2, verdict=warn
            f.write(json.dumps({
                "ts": ts, "commit_sha": sha, "tier": 2, "agent": "af-critic",
                "verdict": "warn", "findings_count": 2, "extension_log_count": 0,
                "duration_ms": None, "tokens": None, "tool_calls": None,
                "evidence_present": False, "evidence_items": 0, "evidence_cited": 0,
            }) + "\n")
            # T3 record: findings_count=0, verdict=pass (same commit)
            f.write(json.dumps({
                "ts": ts, "commit_sha": sha, "tier": 3, "agent": "af-cross-review",
                "verdict": "pass", "findings_count": 0, "extension_log_count": 0,
                "duration_ms": None, "tokens": None, "tool_calls": None,
                "evidence_present": False, "evidence_items": 0, "evidence_cited": 0,
            }) + "\n")

    report = metrics_mod.compute_report(ws)
    # 10 commits with T3, spanning > 7 days, no skip subsequent_block → guidance should appear
    assert "Phase 4 판단 불가" not in report
    assert "skip" in report.lower()
    # Verify per-commit grouping: 10 pairs → 10 distinct commits, commits_with_t3=10
    assert "T3 BLOCK-only 커밋: 0 / 10" in report


def test_compute_report_phase4_skip_suppresses_guidance(metrics_mod, ws):
    """skip_audit에 subsequent_block=True가 있으면 충분 데이터여도 guidance 억제 (Finding R1-2)."""
    import datetime as _dt
    metrics_path = os.path.join(ws, ".af_review_queue", "review_metrics.jsonl")
    base = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
    # 10 commits spanning 8 days → 데이터 게이트(commits>=10 AND span>=7일)는 통과하는 상태
    with open(metrics_path, "w", encoding="utf-8") as f:
        for i in range(10):
            sha = f"sha{i + 1:03d}"
            ts = (base + _dt.timedelta(days=i * 0.9)).isoformat()
            f.write(json.dumps({
                "ts": ts, "commit_sha": sha, "tier": 2, "agent": "af-critic",
                "verdict": "warn", "findings_count": 2, "extension_log_count": 0,
                "duration_ms": None, "tokens": None, "tool_calls": None,
                "evidence_present": False, "evidence_items": 0, "evidence_cited": 0,
            }) + "\n")
            f.write(json.dumps({
                "ts": ts, "commit_sha": sha, "tier": 3, "agent": "af-cross-review",
                "verdict": "pass", "findings_count": 0, "extension_log_count": 0,
                "duration_ms": None, "tokens": None, "tool_calls": None,
                "evidence_present": False, "evidence_items": 0, "evidence_cited": 0,
            }) + "\n")

    # skip 후 BLOCK이 발견된 사례 1건 기록
    metrics_mod.append_skip_audit(ws, skipped_tier=3, reason="tier-1-only", subsequent_block=True)

    report = metrics_mod.compute_report(ws)
    # 충분 데이터지만 skip-후-BLOCK 때문에 guidance가 억제돼야 함
    assert "Phase 4 판단 불가" in report
    assert "skip 후 BLOCK 발견" in report
    # 정상 guidance 문구는 나오면 안 됨 (억제가 데이터 게이트를 실제로 override함을 검증)
    assert "skip 보수적 유지" not in report
    assert "선택적 skip 검토" not in report
    assert "공격적 skip" not in report


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
    # Phase 2 v7 §5.3: hook_runner는 이제 `_extract_verdict_from_content` wrapper만 호출
    # → 직접 _VERDICT_RE/_VERDICT_HEADER_RE access는 무관, wrapper stub 필요.
    import types
    fake_rg = types.ModuleType("scripts.review_gate")
    import re
    fake_rg._VERDICT_RE = re.compile(r"Verdict:\s*(\w+)", re.IGNORECASE)
    fake_rg._VERDICT_HEADER_RE = re.compile(r"## Verdict\s*\n\s*(\w+)", re.IGNORECASE)

    def _fake_extract(content: str):
        m = fake_rg._VERDICT_RE.search(content)
        if m:
            return m.group(1).lower()
        hm = fake_rg._VERDICT_HEADER_RE.search(content)
        return hm.group(1).lower() if hm else None
    fake_rg._extract_verdict_from_content = _fake_extract
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


def _stub_hook_env(tmp_path, monkeypatch):
    """공통 hook_runner + review_gate stub 설정."""
    import scripts.review_metrics_logger as rml
    import scripts.hook_runner as hr
    importlib.reload(hr)
    monkeypatch.setattr(hr, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(hr, "_detect_workspace", lambda: str(tmp_path))

    q = tmp_path / ".af_review_queue"
    q.mkdir(exist_ok=True)
    (q / "pending_agent_review.json").write_text(
        json.dumps({"files": [], "blast_tier": 2})
    )

    import types
    fake_rg = types.ModuleType("scripts.review_gate")
    fake_rg._extract_verdict_from_content = lambda c: "pass"
    fake_rg.record_review_done = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "scripts.review_gate", fake_rg)
    monkeypatch.setitem(sys.modules, "scripts.review_metrics_logger", rml)
    return hr, rml


def test_post_agent_record_duration_ms_passed(tmp_path, monkeypatch):
    """payload의 duration_ms가 append_metric(duration_ms=...)에 전달된다."""
    received = []
    hr, rml = _stub_hook_env(tmp_path, monkeypatch)
    monkeypatch.setattr(rml, "append_metric", lambda *a, **kw: received.append(kw))

    hr._post_agent_record({
        "tool_input": {"subagent_type": "af-critic"},
        "tool_response": {"content": "Verdict: pass"},
        "duration_ms": 12345,
    })

    assert received, "append_metric 미호출"
    assert received[0].get("duration_ms") == 12345


def test_post_agent_record_duration_ms_absent(tmp_path, monkeypatch):
    """payload에 duration_ms 없으면 None 전달 — 크래시 없음."""
    received = []
    hr, rml = _stub_hook_env(tmp_path, monkeypatch)
    monkeypatch.setattr(rml, "append_metric", lambda *a, **kw: received.append(kw))

    hr._post_agent_record({
        "tool_input": {"subagent_type": "af-critic"},
        "tool_response": {"content": "Verdict: pass"},
    })

    assert received, "append_metric 미호출"
    assert received[0].get("duration_ms") is None

"""tests/test_block_learning.py — Phase 1 BLOCK Learning capture 단위 테스트.

커버리지:
  (a) _normalize_pattern_key — 7개 known family 매핑
  (b) _normalize_pattern_key — 미매칭 → unknown:<sha256_8char>
  (c) capture_block_finding — JSONL 파일 생성 + append
  (d) capture_block_finding — 레코드 필드 정합성
  (e) list_patterns — 빈 파일 → 빈 목록
  (f) list_patterns — 집계 정확성 + 정렬
  (g) list_patterns — unknown:* 제외
"""
from __future__ import annotations

import json
import os

import pytest

from scripts.review_gate import (
    _normalize_pattern_key,
    capture_block_finding,
    _BLOCK_PATTERNS_RELPATH,
)
from scripts.af_evolution import list_patterns


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def ws(tmp_path):
    """임시 워크스페이스."""
    return str(tmp_path)


def _read_patterns(ws: str) -> list[dict]:
    path = os.path.join(ws, _BLOCK_PATTERNS_RELPATH)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ── (a) _normalize_pattern_key — 7개 known family ────────────────────────────

@pytest.mark.parametrize("text,expected_key", [
    ("af.spec hiddenimport missing for new core file", "hiddenimport"),
    ("hidden import not added to frozen build", "hiddenimport"),
    ("New parameter not wired to production caller", "production_caller_wiring"),
    ("caller배선 누락", "production_caller_wiring"),
    ("Master_Blueprint §3 not updated", "blueprint_update"),
    ("Blueprint update missing", "blueprint_update"),
    ("hardcoded absolute path in open() call", "absolute_path"),
    ("절대경로 사용 금지 위반", "absolute_path"),
    ("tests cover fixture only, not production path", "fixture_only"),
    ("픽스처만 테스트", "fixture_only"),
    ("pre-commit bypass detected", "pre_commit_bypass"),
    ("AF_SKIP_REVIEW_GATE used without justification", "pre_commit_bypass"),
    ("INSTRUCTIONS.md not synced after provider instruction change", "provider_instruction_drift"),
    ("provider instruction drift: CLAUDE.md missing rule", "provider_instruction_drift"),
    ("GEMINI.md not updated", "provider_instruction_drift"),
])
def test_normalize_known_patterns(text, expected_key):
    assert _normalize_pattern_key(text) == expected_key


# ── (b) _normalize_pattern_key — 미매칭 ─────────────────────────────────────

def test_normalize_unknown_returns_hash():
    key = _normalize_pattern_key("completely unrelated finding text xyz")
    assert key.startswith("unknown:")
    suffix = key[len("unknown:"):]
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_normalize_unknown_deterministic():
    text = "some novel finding"
    assert _normalize_pattern_key(text) == _normalize_pattern_key(text)


def test_normalize_unknown_different_texts_different_hash():
    k1 = _normalize_pattern_key("finding A unique content")
    k2 = _normalize_pattern_key("finding B different content")
    assert k1 != k2


# ── (c) capture_block_finding — JSONL 생성 및 append ─────────────────────────

def test_capture_creates_jsonl(ws):
    capture_block_finding(ws, "af-cross-review", "af.spec hiddenimport missing")
    path = os.path.join(ws, _BLOCK_PATTERNS_RELPATH)
    assert os.path.exists(path)


def test_capture_appends_multiple(ws):
    capture_block_finding(ws, "af-cross-review", "af.spec hiddenimport missing")
    capture_block_finding(ws, "af-critic", "production caller wiring missing")
    records = _read_patterns(ws)
    assert len(records) == 2


def test_capture_creates_data_dir(tmp_path):
    ws = str(tmp_path / "newws")
    os.makedirs(ws)
    capture_block_finding(ws, "af-cross-review", "blueprint not updated")
    path = os.path.join(ws, _BLOCK_PATTERNS_RELPATH)
    assert os.path.exists(path)


# ── (d) capture_block_finding — 레코드 필드 정합성 ────────────────────────────

def test_capture_record_fields(ws):
    capture_block_finding(ws, "af-cross-review", "hiddenimport missing", source_report="docs/reviews/2026-06-21-review.md")
    records = _read_patterns(ws)
    assert len(records) == 1
    r = records[0]
    assert r["pattern_key"] == "hiddenimport"
    assert r["review_agent"] == "af-cross-review"
    assert r["source_report"] == "docs/reviews/2026-06-21-review.md"
    assert "created_at" in r
    assert "finding_excerpt" in r
    assert "changed_files" in r
    assert r["severity"] == "high"


def test_capture_excerpt_truncated(ws):
    long_text = "X" * 1000
    capture_block_finding(ws, "af-critic", long_text)
    records = _read_patterns(ws)
    assert len(records[0]["finding_excerpt"]) <= 500


def test_capture_unknown_pattern_stored(ws):
    capture_block_finding(ws, "af-cross-review", "some completely unknown finding")
    records = _read_patterns(ws)
    assert records[0]["pattern_key"].startswith("unknown:")


# ── (e) list_patterns — 빈 파일 ──────────────────────────────────────────────

def test_list_patterns_empty_ws(ws):
    assert list_patterns(ws) == []


def test_list_patterns_no_file(ws):
    assert list_patterns(ws) == []


# ── (f) list_patterns — 집계 정확성 + 정렬 ──────────────────────────────────

def test_list_patterns_counts(ws):
    for _ in range(3):
        capture_block_finding(ws, "af-cross-review", "hiddenimport missing")
    for _ in range(2):
        capture_block_finding(ws, "af-critic", "blueprint not updated")
    capture_block_finding(ws, "af-critic", "hardcoded absolute path")

    patterns = list_patterns(ws)
    keys = [p["pattern_key"] for p in patterns]
    counts = {p["pattern_key"]: p["count"] for p in patterns}

    assert counts["hiddenimport"] == 3
    assert counts["blueprint_update"] == 2
    assert counts["absolute_path"] == 1
    # 정렬: count 내림차순
    assert keys[0] == "hiddenimport"
    assert keys[1] == "blueprint_update"


# ── (g) list_patterns — unknown:* 집계 제외 ──────────────────────────────────

def test_list_patterns_excludes_unknown(ws):
    capture_block_finding(ws, "af-cross-review", "completely novel finding abc123")
    patterns = list_patterns(ws)
    for p in patterns:
        assert not p["pattern_key"].startswith("unknown:")


def test_list_patterns_mixed_unknown_excluded(ws):
    capture_block_finding(ws, "af-cross-review", "af.spec hiddenimport")
    capture_block_finding(ws, "af-cross-review", "novel finding that does not match")
    patterns = list_patterns(ws)
    assert len(patterns) == 1
    assert patterns[0]["pattern_key"] == "hiddenimport"

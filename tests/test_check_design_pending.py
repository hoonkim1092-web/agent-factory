"""tests/test_check_design_pending.py

check_design_pending.py — 라운드 캡(S1) + 진동 감지(S2) 단위 테스트.
INV-3: round_count >= MAX_DESIGN_ROUNDS → 자동발화 중단.
S2: oscillation_detected=True → 즉시 중단 + 플래그 리셋.
"""
from __future__ import annotations

import json
import os
import sys
import time
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import check_design_pending as mod


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_queue_entry(ws: str, fname: str, file_path: str, ts: float | None = None) -> None:
    """큐 디렉터리에 설계문서 enqueue 항목을 만든다."""
    qdir = os.path.join(ws, mod.DESIGN_QUEUE_DIR)
    os.makedirs(qdir, exist_ok=True)
    data = {
        "file_path": file_path,
        "timestamp": ts if ts is not None else time.time() - mod.MIN_BATCH_INTERVAL_SEC - 5,
    }
    with open(os.path.join(qdir, fname), "w", encoding="utf-8") as f:
        json.dump(data, f)


def _write_fired(ws: str, data: dict) -> None:
    fired_path = os.path.join(ws, mod.FIRED_MARKER)
    os.makedirs(os.path.dirname(fired_path), exist_ok=True)
    with open(fired_path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _read_fired(ws: str) -> dict:
    path = os.path.join(ws, mod.FIRED_MARKER)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _run_main(ws: str) -> str:
    """main()을 실행하고 stdout 출력을 반환한다."""
    buf = StringIO()
    with patch.object(mod, "_detect_workspace", return_value=ws), \
         patch("sys.stdout", buf):
        mod.main()
    return buf.getvalue()


# ── _normalize_entry ──────────────────────────────────────────────────────────

class TestNormalizeEntry:
    def test_float_legacy(self):
        """기존 float 포맷 → 정규화."""
        e = mod._normalize_entry(1700000000.0)
        assert e["fired_at"] == 1700000000.0
        assert e["round_count"] == 0
        assert e["last_verdict"] == ""
        assert e["capped_notified_at"] == 0.0

    def test_zero_float(self):
        e = mod._normalize_entry(0)
        assert e["fired_at"] == 0.0
        assert e["round_count"] == 0

    def test_dict_full(self):
        d = {"fired_at": 100.0, "round_count": 2, "last_verdict": "block", "capped_notified_at": 200.0}
        e = mod._normalize_entry(d)
        assert e["fired_at"] == 100.0
        assert e["round_count"] == 2
        assert e["last_verdict"] == "block"
        assert e["capped_notified_at"] == 200.0

    def test_dict_partial(self):
        """round_count 없는 dict → 0."""
        e = mod._normalize_entry({"fired_at": 50.0})
        assert e["round_count"] == 0
        assert e["last_verdict"] == ""

    def test_dict_round_count_negative(self):
        """음수 round_count → 0으로 클램프."""
        e = mod._normalize_entry({"round_count": -1})
        assert e["round_count"] == 0

    def test_none_value(self):
        """None → fired_at=0, round_count=0."""
        e = mod._normalize_entry(None)
        assert e["fired_at"] == 0.0
        assert e["round_count"] == 0


# ── 라운드 캡 (INV-3) ─────────────────────────────────────────────────────────

class TestRoundCap:
    def test_cap_blocks_fire(self, tmp_path):
        """round_count >= MAX_DESIGN_ROUNDS → 발화 없음."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {"fired_at": 0.0, "round_count": mod.MAX_DESIGN_ROUNDS, "last_verdict": "", "capped_notified_at": 0.0}
        })

        out = _run_main(ws)
        assert "[af-design-review-pending]" not in out
        assert "[af-design-review-capped]" in out

    def test_cap_prints_capped_message(self, tmp_path):
        """캡 도달 시 [af-design-review-capped] 메시지 출력."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {"fired_at": 0.0, "round_count": mod.MAX_DESIGN_ROUNDS, "last_verdict": "", "capped_notified_at": 0.0}
        })

        out = _run_main(ws)
        assert "af-design-review-capped" in out
        assert str(mod.MAX_DESIGN_ROUNDS) in out

    def test_cap_notified_once(self, tmp_path):
        """capped_notified_at 이미 설정 → 두 번째 호출은 메시지 없음."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {
                "fired_at": 0.0,
                "round_count": mod.MAX_DESIGN_ROUNDS,
                "last_verdict": "",
                "capped_notified_at": time.time() - 1,  # 이미 알림 보냄
            }
        })

        out = _run_main(ws)
        assert "[af-design-review-capped]" not in out
        assert "[af-design-review-pending]" not in out

    def test_cap_saves_capped_notified_at(self, tmp_path):
        """캡 알림 후 capped_notified_at 기록."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {"fired_at": 0.0, "round_count": mod.MAX_DESIGN_ROUNDS, "last_verdict": "", "capped_notified_at": 0.0}
        })

        _run_main(ws)

        saved = _read_fired(ws)
        assert fname in saved
        entry = saved[fname]
        assert isinstance(entry, dict)
        assert entry["capped_notified_at"] > 0

    def test_below_cap_fires(self, tmp_path):
        """round_count < MAX_DESIGN_ROUNDS → 정상 발화."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {"fired_at": 0.0, "round_count": mod.MAX_DESIGN_ROUNDS - 1, "last_verdict": "", "capped_notified_at": 0.0}
        })

        out = _run_main(ws)
        assert "[af-design-review-pending]" in out
        assert "[af-design-review-capped]" not in out

    def test_zero_round_count_fires(self, tmp_path):
        """첫 발화 (round_count=0) → 정상 발화."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        # fired 마커 없음 (처음)

        out = _run_main(ws)
        assert "[af-design-review-pending]" in out


# ── round_count 증가 ──────────────────────────────────────────────────────────

class TestRoundCountIncrement:
    def test_first_fire_sets_round_count_1(self, tmp_path):
        """첫 발화 → round_count=1로 저장."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")

        _run_main(ws)

        saved = _read_fired(ws)
        assert fname in saved
        entry = saved[fname]
        assert isinstance(entry, dict)
        assert entry["round_count"] == 1

    def test_second_fire_sets_round_count_2(self, tmp_path):
        """두 번째 발화 → round_count=2."""
        ws = str(tmp_path)
        fname = "q1.json"
        ts = time.time() - mod.MIN_BATCH_INTERVAL_SEC - 5
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md", ts=ts)

        past_fired = ts - 10  # 발화 기록이 있지만 ts보다 오래됨
        _write_fired(ws, {
            fname: {"fired_at": past_fired, "round_count": 1, "last_verdict": "", "capped_notified_at": 0.0}
        })

        _run_main(ws)

        saved = _read_fired(ws)
        assert saved[fname]["round_count"] == 2

    def test_fires_exactly_max_rounds_then_caps(self, tmp_path):
        """MAX_DESIGN_ROUNDS 발화 후 캡 — round_count 추이 검증."""
        ws = str(tmp_path)
        fname = "q1.json"

        for expected_round in range(1, mod.MAX_DESIGN_ROUNDS + 1):
            ts = time.time() - mod.MIN_BATCH_INTERVAL_SEC - 5
            _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md", ts=ts)
            prev = _read_fired(ws)
            prev_count = prev.get(fname, {}).get("round_count", 0) if isinstance(prev.get(fname), dict) else 0

            out = _run_main(ws)
            assert "[af-design-review-pending]" in out

            saved = _read_fired(ws)
            assert saved[fname]["round_count"] == expected_round

            # 다음 발화를 위해 fired_at을 과거로 조정 (새 편집 시뮬레이션)
            saved[fname]["fired_at"] = ts - 20
            _write_fired(ws, saved)

        # MAX_DESIGN_ROUNDS+1 번째: 캡
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        out = _run_main(ws)
        assert "[af-design-review-pending]" not in out
        assert "[af-design-review-capped]" in out


# ── 레거시 float 마이그레이션 ─────────────────────────────────────────────────

class TestLegacyFloatMigration:
    def test_legacy_float_fires_and_upgrades(self, tmp_path):
        """기존 float 포맷 → 발화 후 dict 포맷으로 업그레이드."""
        ws = str(tmp_path)
        fname = "q1.json"
        ts = time.time() - mod.MIN_BATCH_INTERVAL_SEC - 5
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md", ts=ts)
        # 구버전: float만 저장 (fired_at만, 발화는 ts보다 오래됨)
        _write_fired(ws, {fname: ts - 20})

        out = _run_main(ws)
        assert "[af-design-review-pending]" in out

        saved = _read_fired(ws)
        entry = saved[fname]
        assert isinstance(entry, dict)
        assert entry["round_count"] == 1

    def test_legacy_float_no_prior_fire_fires(self, tmp_path):
        """구버전 float=0 → 처음 발화처럼 동작."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {fname: 0.0})

        out = _run_main(ws)
        assert "[af-design-review-pending]" in out


# ── last_verdict 보존 ─────────────────────────────────────────────────────────

class TestLastVerdictPreserved:
    def test_last_verdict_preserved_on_fire(self, tmp_path):
        """발화 시 last_verdict 기존 값을 유지한다."""
        ws = str(tmp_path)
        fname = "q1.json"
        ts = time.time() - mod.MIN_BATCH_INTERVAL_SEC - 5
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md", ts=ts)
        _write_fired(ws, {
            fname: {"fired_at": ts - 20, "round_count": 1, "last_verdict": "block", "capped_notified_at": 0.0}
        })

        _run_main(ws)

        saved = _read_fired(ws)
        assert saved[fname]["last_verdict"] == "block"


# ── 진동 감지 (S2, INV-3 §4.2) ───────────────────────────────────────────────

class TestOscillationDetection:
    def test_oscillation_blocks_fire(self, tmp_path):
        """oscillation_detected=True → 발화 없음, oscillation 메시지 출력."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {
                "fired_at": 0.0,
                "round_count": 1,
                "last_verdict": "BLOCK",
                "last_block_sections": ["§3", "§4.1"],
                "oscillation_detected": True,
                "capped_notified_at": 0.0,
            }
        })

        out = _run_main(ws)
        assert "[af-design-review-pending]" not in out
        assert "[af-design-review-oscillation]" in out

    def test_oscillation_resets_flag_after_warning(self, tmp_path):
        """oscillation 경고 후 oscillation_detected 플래그가 False로 리셋된다."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {
                "fired_at": 0.0,
                "round_count": 1,
                "last_verdict": "BLOCK",
                "last_block_sections": ["§3"],
                "oscillation_detected": True,
                "capped_notified_at": 0.0,
            }
        })

        _run_main(ws)

        saved = _read_fired(ws)
        assert saved[fname]["oscillation_detected"] is False

    def test_oscillation_false_fires_normally(self, tmp_path):
        """oscillation_detected=False → 정상 발화."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")
        _write_fired(ws, {
            fname: {
                "fired_at": 0.0,
                "round_count": 1,
                "last_verdict": "BLOCK",
                "last_block_sections": ["§3"],
                "oscillation_detected": False,
                "capped_notified_at": 0.0,
            }
        })

        out = _run_main(ws)
        assert "[af-design-review-pending]" in out
        assert "[af-design-review-oscillation]" not in out

    def test_fire_saves_last_block_sections(self, tmp_path):
        """발화 기록에 last_block_sections가 포함된다."""
        ws = str(tmp_path)
        fname = "q1.json"
        ts = time.time() - mod.MIN_BATCH_INTERVAL_SEC - 5
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md", ts=ts)
        _write_fired(ws, {
            fname: {
                "fired_at": ts - 20,
                "round_count": 0,
                "last_verdict": "",
                "last_block_sections": ["§2", "§5"],
                "oscillation_detected": False,
                "capped_notified_at": 0.0,
            }
        })

        _run_main(ws)

        saved = _read_fired(ws)
        entry = saved[fname]
        assert "last_block_sections" in entry
        assert entry["last_block_sections"] == ["§2", "§5"]  # 기존 값 보존

    def test_fire_saves_oscillation_detected_false(self, tmp_path):
        """발화 기록 시 oscillation_detected=False로 저장된다."""
        ws = str(tmp_path)
        fname = "q1.json"
        _make_queue_entry(ws, fname, "docs/2026-06-19-foo-design.md")

        _run_main(ws)

        saved = _read_fired(ws)
        assert saved[fname]["oscillation_detected"] is False

    def test_normalize_entry_s2_fields_default(self):
        """_normalize_entry: float 레거시 → S2 필드 기본값."""
        e = mod._normalize_entry(123.0)
        assert e["last_block_sections"] == []
        assert e["oscillation_detected"] is False

    def test_normalize_entry_s2_fields_from_dict(self):
        """_normalize_entry: dict에 S2 필드 있으면 보존."""
        e = mod._normalize_entry({
            "fired_at": 100.0,
            "round_count": 2,
            "last_verdict": "BLOCK",
            "last_block_sections": ["§1", "§2.3"],
            "oscillation_detected": True,
            "capped_notified_at": 0.0,
        })
        assert e["last_block_sections"] == ["§1", "§2.3"]
        assert e["oscillation_detected"] is True

    def test_normalize_entry_bad_sections_type(self):
        """last_block_sections가 str 등 비정상 타입 → 빈 리스트."""
        e = mod._normalize_entry({"last_block_sections": "§3"})
        assert e["last_block_sections"] == []

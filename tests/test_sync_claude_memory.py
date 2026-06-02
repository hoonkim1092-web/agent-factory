from pathlib import Path

from scripts.sync_claude_memory import _normalize_newlines, _write_atomic


# --- 줄바꿈 정규화 (CRLF 누적 버그 fix 회귀) ---------------------------------


def test_normalize_newlines_variants():
    assert _normalize_newlines("a\r\nb") == "a\nb"
    assert _normalize_newlines("a\r\r\nb") == "a\nb"      # 다중 CR → 빈 줄 아님
    assert _normalize_newlines("a\r\r\r\nb") == "a\nb"
    assert _normalize_newlines("a\rb") == "a\nb"          # lone CR
    assert _normalize_newlines("a\nb") == "a\nb"          # LF 보존


def test_write_atomic_emits_lf_only(tmp_path: Path):
    # _write_atomic은 OS와 무관하게 LF만 기록 (Windows text mode \n→\r\n 차단)
    p = tmp_path / "m.md"
    _write_atomic(p, "a\nb\nc\n")
    assert b"\r" not in p.read_bytes()
    assert p.read_bytes() == b"a\nb\nc\n"


def test_write_atomic_normalizes_crlf_and_multi_cr(tmp_path: Path):
    # CRLF/다중 CR content를 받아도 디스크에는 LF만 (재유입 차단)
    p = tmp_path / "m.md"
    _write_atomic(p, "a\r\nb\r\r\nc")
    assert b"\r" not in p.read_bytes()
    assert p.read_bytes() == b"a\nb\nc"

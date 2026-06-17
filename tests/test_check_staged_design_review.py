"""tests/test_check_staged_design_review.py

surface 단절 해소 게이트(scripts/check_staged_design_review.py) 단위 테스트.
watcher BLOCK 판정이 커밋 전 surface 되는지(d1022ecd 재발 방지) 검증한다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import check_staged_design_review as mod


def _write_review(ws: str, fname: str, source: str, verdict: str, *, bold: bool = False) -> None:
    reviews = os.path.join(ws, "docs", "reviews")
    os.makedirs(reviews, exist_ok=True)
    verdict_line = f"### Verdict: **{verdict}**\n" if bold else f"### Verdict: {verdict}\n"
    body = (
        f"# Design Review: {source}\n\n"
        f"> Source: {source}\n"
        f"> Type: design\n\n"
        f"---\n\n"
        f"## Final Design Review\n\n"
        f"{verdict_line}"
    )
    with open(os.path.join(reviews, fname), "w", encoding="utf-8") as f:
        f.write(body)


# ── load_latest_design_verdicts ────────────────────────────────────────────

class TestLoadLatestVerdicts:
    def test_no_reviews_dir_empty(self, tmp_path):
        assert mod.load_latest_design_verdicts(str(tmp_path)) == {}

    def test_single_block(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK")
        out = mod.load_latest_design_verdicts(ws)
        assert out[src][0] == "BLOCK"
        assert out[src][1] == "docs/reviews/2026-06-18-015950-foo-design-design-review.md"

    def test_newer_pass_overrides_older_block(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK")
        _write_review(ws, "2026-06-18-093000-foo-design-design-review.md", src, "PASS")
        out = mod.load_latest_design_verdicts(ws)
        # 더 큰 ts(093000 > 015950)가 최신 → PASS 가 BLOCK 을 덮는다.
        assert out[src][0] == "PASS"

    def test_older_pass_does_not_override_newer_block(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-010000-foo-design-design-review.md", src, "PASS")
        _write_review(ws, "2026-06-18-020000-foo-design-design-review.md", src, "BLOCK")
        out = mod.load_latest_design_verdicts(ws)
        assert out[src][0] == "BLOCK"

    def test_non_design_review_files_ignored(self, tmp_path):
        ws = str(tmp_path)
        reviews = os.path.join(ws, "docs", "reviews")
        os.makedirs(reviews, exist_ok=True)
        # code-review 파일은 -design-review.md 접미사가 아니라 무시돼야 한다.
        with open(os.path.join(reviews, "2026-06-18-010000-bar-code-review.md"), "w", encoding="utf-8") as f:
            f.write("> Source: core/bar.py\n\n### Verdict: BLOCK\n")
        assert mod.load_latest_design_verdicts(ws) == {}

    def test_bold_verdict_format_parsed(self, tmp_path):
        # 실측 19개 리뷰가 `### Verdict: **BLOCK**` 볼드체 사용 → 반드시 흡수돼야 함.
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK", bold=True)
        out = mod.load_latest_design_verdicts(ws)
        assert out[src][0] == "BLOCK"

    def test_missing_source_or_verdict_skipped(self, tmp_path):
        ws = str(tmp_path)
        reviews = os.path.join(ws, "docs", "reviews")
        os.makedirs(reviews, exist_ok=True)
        with open(os.path.join(reviews, "2026-06-18-010000-x-design-review.md"), "w", encoding="utf-8") as f:
            f.write("# no source, no verdict\n")
        assert mod.load_latest_design_verdicts(ws) == {}


# ── find_blocked (실제 is_design_doc 사용) ─────────────────────────────────

class TestFindBlocked:
    def test_staged_design_doc_block_returned(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK")
        blocked = mod.find_blocked(ws, [src])
        assert blocked == [(src, "docs/reviews/2026-06-18-015950-foo-design-design-review.md")]

    def test_staged_design_doc_bold_block_returned(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK", bold=True)
        blocked = mod.find_blocked(ws, [src])
        assert blocked == [(src, "docs/reviews/2026-06-18-015950-foo-design-design-review.md")]

    def test_staged_design_doc_pass_not_returned(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "PASS")
        assert mod.find_blocked(ws, [src]) == []

    def test_staged_design_doc_warn_not_returned(self, tmp_path):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "WARN")
        assert mod.find_blocked(ws, [src]) == []

    def test_staged_design_doc_no_review_not_returned(self, tmp_path):
        ws = str(tmp_path)
        assert mod.find_blocked(ws, ["docs/2026-06-17-foo-design.md"]) == []

    def test_non_design_staged_ignored_even_with_block(self, tmp_path):
        ws = str(tmp_path)
        # core/x.py 는 설계문서가 아니다 → BLOCK 리뷰가 있어도 무시.
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK")
        assert mod.find_blocked(ws, ["core/x.py"]) == []

    def test_review_dir_excluded_from_design_docs(self, tmp_path):
        ws = str(tmp_path)
        # docs/reviews/*.md 자체는 EXCLUDE → 설계문서로 취급 안 됨.
        review_rel = "docs/reviews/2026-06-18-015950-foo-design-design-review.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md",
                      "docs/2026-06-17-foo-design.md", "BLOCK")
        assert mod.find_blocked(ws, [review_rel]) == []


# ── main (exit code) ───────────────────────────────────────────────────────

class TestMain:
    def test_block_returns_1(self, tmp_path, monkeypatch):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "BLOCK")
        monkeypatch.setattr(mod, "_staged_files", lambda w: [src])
        assert mod.main(["--workspace", ws]) == 1

    def test_clean_returns_0(self, tmp_path, monkeypatch):
        ws = str(tmp_path)
        src = "docs/2026-06-17-foo-design.md"
        _write_review(ws, "2026-06-18-015950-foo-design-design-review.md", src, "PASS")
        monkeypatch.setattr(mod, "_staged_files", lambda w: [src])
        assert mod.main(["--workspace", ws]) == 0

    def test_no_staged_returns_0(self, tmp_path, monkeypatch):
        ws = str(tmp_path)
        monkeypatch.setattr(mod, "_staged_files", lambda w: [])
        assert mod.main(["--workspace", ws]) == 0

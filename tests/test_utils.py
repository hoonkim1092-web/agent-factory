"""core.utils 단위 테스트."""
from __future__ import annotations

import os
os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")

import pytest
from core.utils import truncate_text
from core.utils import test_file_for as _test_file_for


class TestTruncateText:
    def test_짧은_문자열은_그대로_반환(self):
        assert truncate_text("hello", 10) == "hello"

    def test_정확히_max_len이면_그대로_반환(self):
        assert truncate_text("hello", 5) == "hello"

    def test_초과_시_suffix_붙임(self):
        result = truncate_text("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_커스텀_suffix(self):
        result = truncate_text("hello world", 7, suffix="--")
        assert result == "hello--"
        assert len(result) == 7

    def test_빈_문자열(self):
        assert truncate_text("", 5) == ""

    def test_none_처리(self):
        assert truncate_text(None, 5) == ""  # type: ignore[arg-type]

    def test_max_len이_suffix보다_작으면_suffix_없이_자름(self):
        result = truncate_text("abcdef", 2)
        assert result == "ab"
        assert len(result) == 2

    def test_max_len_0(self):
        assert truncate_text("abc", 0) == ""

    def test_유니코드_문자(self):
        s = "안녕하세요세계"
        result = truncate_text(s, 5)
        assert len(result) == 5
        assert result == "안녕..."


class TestTestFileFor:
    def test_core_모듈(self):
        assert _test_file_for("core/dogfood.py") == "tests/test_dogfood.py"

    def test_scripts_모듈(self):
        assert _test_file_for("scripts/review_gate.py") == "tests/test_review_gate.py"

    def test_비파이썬_파일은_None(self):
        assert _test_file_for("docs/README.md") is None

    def test_루트_py는_None(self):
        assert _test_file_for("run_factory_cli.py") is None

    def test_중첩_경로는_None(self):
        assert _test_file_for("core/sub/foo.py") is None

    def test_백슬래시_경로(self):
        assert _test_file_for("core\\utils.py") == "tests/test_utils.py"

    def test_세미콜론_stem은_None(self):
        assert _test_file_for("core/evil;cmd.py") is None

    def test_파이프_stem은_None(self):
        assert _test_file_for("core/a|b.py") is None

    def test_달러_stem은_None(self):
        assert _test_file_for("core/$var.py") is None

    def test_대시와_점_포함_stem은_허용(self):
        assert _test_file_for("core/my-module.v2.py") == "tests/test_my-module.v2.py"

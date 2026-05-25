"""core.utils.truncate_text 단위 테스트."""
from __future__ import annotations

import os
os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")

import pytest
from core.utils import truncate_text


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

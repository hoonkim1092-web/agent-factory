"""core.utils 단위 테스트."""
from __future__ import annotations

import os
os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")

import pytest
from core.utils import truncate_text, clamp, median, chunks
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


class TestClamp:
    def test_범위_내_값은_그대로(self):
        assert clamp(5, 0, 10) == 5

    def test_min_미만은_min_반환(self):
        assert clamp(-1, 0, 10) == 0

    def test_max_초과는_max_반환(self):
        assert clamp(11, 0, 10) == 10

    def test_min과_동일(self):
        assert clamp(0, 0, 10) == 0

    def test_max와_동일(self):
        assert clamp(10, 0, 10) == 10

    def test_부동소수점(self):
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_잘못된_범위는_ValueError(self):
        with pytest.raises(ValueError):
            clamp(5, 10, 0)


class TestMedian:
    def test_단일_요소(self):
        assert median([5]) == 5.0

    def test_홀수_개_정렬됨(self):
        assert median([1, 3, 5]) == 3.0

    def test_홀수_개_비정렬(self):
        assert median([5, 1, 3]) == 3.0

    def test_짝수_개(self):
        assert median([1, 2, 3, 4]) == 2.5

    def test_음수_포함(self):
        assert median([-3, -1, 1, 3]) == 0.0

    def test_부동소수점(self):
        assert median([1.5, 2.5, 3.5]) == 2.5

    def test_빈_리스트는_ValueError(self):
        with pytest.raises(ValueError):
            median([])

    def test_중복_값(self):
        assert median([2, 2, 2]) == 2.0


class TestChunks:
    def test_빈_리스트(self):
        assert chunks([], 3) == []

    def test_균등_분할(self):
        assert chunks([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_나머지_발생(self):
        assert chunks([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_n이_리스트보다_크면_단일_청크(self):
        assert chunks([1, 2], 10) == [[1, 2]]

    def test_n_1이면_ValueError(self):
        with pytest.raises(ValueError):
            chunks([1, 2, 3], 0)


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

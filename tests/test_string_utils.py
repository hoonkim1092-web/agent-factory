import pytest
from core.string_utils import truncate


class TestTruncate:
    def test_short_string_unchanged(self):
        assert truncate("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert truncate("hello", 5) == "hello"

    def test_truncation_with_default_suffix(self):
        assert truncate("hello world", 8) == "hello..."

    def test_truncation_with_custom_suffix(self):
        assert truncate("hello world", 7, suffix="--") == "hello--"

    def test_empty_suffix(self):
        assert truncate("hello world", 5, suffix="") == "hello"

    def test_raises_when_max_len_lt_suffix(self):
        with pytest.raises(ValueError):
            truncate("hello", 2, suffix="...")

    def test_empty_string(self):
        assert truncate("", 5) == ""

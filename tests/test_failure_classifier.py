"""
tests/test_failure_classifier.py — classify_failure INFRA/IMPLEMENTATION 분류 검증
"""
from __future__ import annotations

import pytest

from core.failure_classifier import FailureCategory, classify_failure


@pytest.mark.parametrize("reason", [
    "worker_timeout",
    "worker_exited_code_1",
    "worker_result_corrupt",
    "missing_api_key",
    "cli_timeout",
    "quota_exceeded",
    "rate_limit",
    "auth_required",
])
def test_infra_patterns_classified_as_infra(reason):
    assert classify_failure(reason) == FailureCategory.INFRA


@pytest.mark.parametrize("reason", [
    "syntax_error",
    "assertion_failed",
    "empty_result",
    "worker_exception",
    "",
    None,
])
def test_implementation_patterns(reason):
    assert classify_failure(reason) == FailureCategory.IMPLEMENTATION

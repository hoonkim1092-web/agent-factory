from __future__ import annotations

import os
os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")

import pytest
from core.utils import safe_id, safe_optional_id as u_soi
from core.external_skill_source_ids import safe_optional_id as e_soi


# ── 핵심 계약: 빈/None/공백 → "" ────────────────────────────────────────────

@pytest.mark.parametrize("fn", [u_soi, e_soi])
@pytest.mark.parametrize("empty", ["", None, "   "])
def test_empty_returns_empty(fn, empty):
    assert fn(empty) == ""


# ── safe_id 대비 차이: 빈 값에서만 다름 ───────────────────────────────────

def test_differs_from_safe_id_on_empty():
    assert safe_id("") == "skill"
    assert u_soi("") == ""


# ── 비-빈 입력은 safe_id 와 동일 출력 ─────────────────────────────────────

@pytest.mark.parametrize("fn", [u_soi, e_soi])
@pytest.mark.parametrize("text, expected", [
    ("Foo Bar", "foo_bar"),
    ("a@@b", "a_b"),
    ("HELLO", "hello"),
    ("hello", "hello"),
    ("hello_world", "hello_world"),
])
def test_non_empty_normalizes(fn, text, expected):
    assert fn(text) == expected


# ── utils 버전과 external_skill_source_ids 버전: 비-빈 입력에서 동일 ────────

def test_both_versions_match_on_short_inputs():
    for s in ["foo", "Hello World", "a_b_c", "12345", "skill"]:
        assert u_soi(s) == e_soi(s), f"mismatch on {s!r}"


# ── utils 버전만: [:60] 절단 ──────────────────────────────────────────────

def test_utils_truncates_at_60():
    assert len(u_soi("a" * 70)) <= 60


def test_ext_no_truncation():
    assert e_soi("a" * 70) == "a" * 70

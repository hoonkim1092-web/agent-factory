"""
Regression tests for Domain Gate Phase A logic.

F3-(a): approve() stores domain_review_version hash in snapshot.
F4-(b): verdict parser supports `- verdict:` first, checkbox fallback.
F5:     blast_radius != system_wide → domain gate skipped.
F6:     AF_SKIP_DOMAIN_REVIEW=1 → domain gate bypassed.
"""
from __future__ import annotations

import os

import pytest

from core.approval_gate import GATE_FILENAME, ApprovalGate, _DOMAIN_REVIEW_FILE, _read_domain_review_verdict


# ---------------------------------------------------------------------------
# _read_domain_review_verdict unit tests
# ---------------------------------------------------------------------------

def _write(tmp_path, content: str) -> str:
    p = tmp_path / "domain-review.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_verdict_explicit_pass(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- verdict: PASS\n")
    assert _read_domain_review_verdict(path) == "PASS"


def test_verdict_explicit_block(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- verdict: BLOCK\n")
    assert _read_domain_review_verdict(path) == "BLOCK"


def test_verdict_explicit_needs_adr(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- verdict: NEEDS_ADR\n")
    assert _read_domain_review_verdict(path) == "NEEDS_ADR"


def test_verdict_checkbox_fallback(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- [ ] BLOCK\n- [x] PASS\n")
    assert _read_domain_review_verdict(path) == "PASS"


def test_verdict_multiple_explicit(tmp_path):
    path = _write(tmp_path, "- verdict: PASS\n- verdict: BLOCK\n")
    assert _read_domain_review_verdict(path) == "MULTIPLE"


def test_verdict_multiple_checkbox(tmp_path):
    path = _write(tmp_path, "- [x] PASS\n- [x] BLOCK\n")
    assert _read_domain_review_verdict(path) == "MULTIPLE"


def test_verdict_missing(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\nNo verdict here.\n")
    assert _read_domain_review_verdict(path) == ""


def test_verdict_file_not_found(tmp_path):
    assert _read_domain_review_verdict(str(tmp_path / "nonexistent.md")) == ""


# ---------------------------------------------------------------------------
# ApprovalGate domain gate integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def gate_system_wide(tmp_path):
    """blast_radius=system_wide 게이트 픽스처."""
    g = ApprovalGate(str(tmp_path), "dg-test")
    g.initialize(work_item_id="WI-DG", work_kind="feature_update", blast_radius="system_wide")
    return g


@pytest.fixture
def gate_module(tmp_path):
    """blast_radius=module 게이트 픽스처 (도메인 게이트 불필요)."""
    g = ApprovalGate(str(tmp_path), "dg-module")
    g.initialize(work_item_id="WI-MOD", work_kind="bugfix", blast_radius="module")
    return g


def _write_domain_review(gate: ApprovalGate, content: str) -> None:
    path = os.path.join(gate.work_item_dir, "domain-review.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class TestDomainGateSystemWide:
    def test_blocks_when_domain_review_missing(self, gate_system_wide):
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "missing_domain_frontmatter"

    def test_blocks_when_verdict_missing(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "# Domain Review\n\nNo verdict.\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "missing_verdict"

    def test_blocks_when_verdict_block(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: BLOCK\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "domain_review_blocked"

    def test_blocks_when_multiple_verdicts(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n- verdict: BLOCK\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "multiple_verdicts"

    def test_passes_with_pass_verdict(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        result = gate_system_wide.approve(approver="user")
        assert result is True
        assert gate_system_wide.last_block_reason == ""

    def test_passes_with_needs_adr_verdict(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: NEEDS_ADR\n")
        result = gate_system_wide.approve(approver="user")
        assert result is True

    def test_stores_domain_review_version_on_approve(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        parsed = gate_system_wide._parse()
        snapshots = parsed.get("snapshots", {})
        assert snapshots.get("domain_review"), "domain_review_version must be stored"

    def test_domain_review_version_changes_when_file_changes(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        v1 = gate_system_wide._parse().get("snapshots", {}).get("domain_review")

        # Invalidate and re-approve with changed content
        gate_system_wide.invalidate(reason="test")
        _write_domain_review(gate_system_wide, "- verdict: PASS\n\nAdditional content.\n")
        gate_system_wide.approve(approver="user")
        v2 = gate_system_wide._parse().get("snapshots", {}).get("domain_review")

        assert v1 != v2


class TestDomainGateNonSystemWide:
    def test_skips_domain_gate_for_module_blast_radius(self, gate_module):
        # no domain-review.md present — should still pass
        result = gate_module.approve(approver="user")
        assert result is True

    def test_no_domain_review_version_stored_for_module(self, gate_module):
        gate_module.approve(approver="user")
        snapshots = gate_module._parse().get("snapshots", {})
        assert not snapshots.get("domain_review")


class TestDomainGateCheckValidity:
    def test_domain_review_change_invalidates_gate(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        assert gate_system_wide.is_execution_open()

        # Modify domain-review.md after approval
        _write_domain_review(gate_system_wide, "- verdict: BLOCK\n")
        assert not gate_system_wide.is_execution_open()

    def test_domain_review_unchanged_stays_valid(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        assert gate_system_wide.is_execution_open()

    def test_no_domain_review_version_no_dr_check(self, gate_module):
        gate_module.approve(approver="user")
        valid, changed = gate_module.check_validity()
        assert valid
        assert _DOMAIN_REVIEW_FILE not in changed


class TestDomainGateSkipEnv:
    def test_skip_env_bypasses_domain_gate(self, gate_system_wide, monkeypatch):
        monkeypatch.setenv("AF_SKIP_DOMAIN_REVIEW", "1")
        # no domain-review.md present
        result = gate_system_wide.approve(approver="user")
        assert result is True

    def test_skip_env_no_version_stored(self, gate_system_wide, monkeypatch):
        monkeypatch.setenv("AF_SKIP_DOMAIN_REVIEW", "1")
        gate_system_wide.approve(approver="user")
        snapshots = gate_system_wide._parse().get("snapshots", {})
        assert not snapshots.get("domain_review")

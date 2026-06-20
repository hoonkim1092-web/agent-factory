"""S2 가짜성공 가드 단위 테스트.

설계: docs/2026-06-20-dogfood-false-success-spin-fix-design.md §3
+ af-cross-review BLOCK 수정(F1 max→sum, F2 provider별 baseline, bounded-workspace gate).

- _workspace_mutation_signature: 실제 production 함수 직접 검증.
- 가드 판정표: agent_runner.py CLI 루프의 강등 술어를 미러링
  (test_agent_runner_force_provider.py 선례 — run()은 너무 무거워 직접 호출 대신
  술어 재현). 미러 대상 production 술어:
  `guard_workspace and rc is not None and rc != 0 and (sig_after == sig_before)`.
"""
from __future__ import annotations

import os

from core.agent_runner import _workspace_mutation_signature


class TestWorkspaceMutationSignature:
    def test_missing_path_returns_zero(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        assert _workspace_mutation_signature(str(missing)) == (0, 0)

    def test_empty_dir_returns_zero(self, tmp_path):
        assert _workspace_mutation_signature(str(tmp_path)) == (0, 0)

    def test_adding_file_changes_signature(self, tmp_path):
        before = _workspace_mutation_signature(str(tmp_path))
        (tmp_path / "out.txt").write_text("hello", encoding="utf-8")
        after = _workspace_mutation_signature(str(tmp_path))
        assert after != before
        assert after[0] == before[0] + 1  # 파일 수 증가

    def test_modifying_mtime_changes_signature(self, tmp_path):
        f = tmp_path / "out.txt"
        f.write_text("v1", encoding="utf-8")
        before = _workspace_mutation_signature(str(tmp_path))
        # mtime을 미래로 밀어 mtime_ns 총합 변화 유발 (파일 수는 동일)
        future = os.path.getmtime(f) + 100.0
        os.utime(f, (future, future))
        after = _workspace_mutation_signature(str(tmp_path))
        assert after[0] == before[0]  # 파일 수 동일
        assert after[1] > before[1]  # mtime_ns 총합 증가
        assert after != before

    def test_modify_older_file_detected_despite_future_sibling(self, tmp_path):
        # F1 회귀(cross-review BLOCK): 미래 mtime 형제 파일이 있어도 더 오래된
        # 파일 수정을 놓치지 않는다. max였다면 newer에 가려 놓침 — sum이라 감지.
        newer = tmp_path / "newer.log"
        newer.write_text("x", encoding="utf-8")
        older = tmp_path / "older.py"
        older.write_text("v1", encoding="utf-8")
        base = os.path.getmtime(older)
        os.utime(newer, (base + 1000, base + 1000))  # 미래 형제(최대 mtime 점유)
        os.utime(older, (base - 1000, base - 1000))  # 오래된 대상
        before = _workspace_mutation_signature(str(tmp_path))
        os.utime(older, (base, base))  # older를 '지금'으로 수정 — 여전히 newer보다 과거
        after = _workspace_mutation_signature(str(tmp_path))
        assert after != before  # 총합이 변해 감지됨

    def test_excluded_dirs_ignored(self, tmp_path):
        baseline = _workspace_mutation_signature(str(tmp_path))
        for excluded in (".git", "__pycache__", "node_modules", ".af-dogfood", ".venv", "venv"):
            sub = tmp_path / excluded
            sub.mkdir()
            (sub / "noise.txt").write_text("noise", encoding="utf-8")
        after = _workspace_mutation_signature(str(tmp_path))
        assert after == baseline  # 제외 디렉터리 변경은 시그니처 불변

    def test_real_file_outside_excluded_still_counted(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "ignored").write_text("x", encoding="utf-8")
        before = _workspace_mutation_signature(str(tmp_path))
        (tmp_path / "real.py").write_text("print(1)", encoding="utf-8")
        after = _workspace_mutation_signature(str(tmp_path))
        assert after[0] == before[0] + 1


def _should_demote(ok, returncode, changed, guard_active=True):
    """agent_runner.py CLI 루프 강등 술어 재현 (production SSOT 미러).

    production: `if cli_result.get("ok"):` 안에서
        if guard_workspace and rc is not None and rc != 0 and sig_after == sig_before:
            → 강등(cli_failures 적재 + continue)
    `changed` = (sig_after != sig_before) = 산출물 변경 여부.
    """
    if not guard_active:
        return False
    if not ok:
        return False
    if returncode is None or returncode == 0:
        return False
    return not changed


class TestFalseSuccessGuardDecision:
    def test_abnormal_exit_no_change_demotes(self):
        # ok=True + returncode=1 + 변경0 → 가짜성공 강등 (이 run의 死因)
        assert _should_demote(ok=True, returncode=1, changed=False) is True

    def test_abnormal_exit_with_change_passes(self):
        # ok=True + returncode=1 + 변경有 → 강등 안 함 (부분완료, 후속 게이트 판정) INV-S2b
        assert _should_demote(ok=True, returncode=1, changed=True) is False

    def test_clean_exit_never_demotes(self):
        # ok=True + returncode=0 → 분기 미진입 (INV-S2a)
        assert _should_demote(ok=True, returncode=0, changed=False) is False

    def test_missing_returncode_never_demotes(self):
        # returncode=None (preflight 조기반환 등) → 보수적으로 강등 안 함
        assert _should_demote(ok=True, returncode=None, changed=False) is False

    def test_not_ok_irrelevant(self):
        # ok=False는 애초에 가드 분기에 도달 안 함
        assert _should_demote(ok=False, returncode=1, changed=False) is False

    def test_unbounded_workspace_skips_guard(self):
        # F2 비용 수정: target_workspace==PROJECT_ROOT면 guard 비활성 → 강등 안 함
        assert _should_demote(ok=True, returncode=1, changed=False, guard_active=False) is False

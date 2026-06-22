"""
tests/test_output_paths.py
==========================
ad-hoc 새 제품/수정 작업의 출력 격리(output isolation) 단위 테스트.

설계: docs/2026-06-18-product-output-isolation-design.md (in-place 복원 개정 2026-06-22)
- INV-O2: cwd가 BASE_DIR(AF repo) 하위 → <base_dir>/projects/<slug> 로 graceful 리다이렉트
- INV-O3: repo 밖 cwd → cwd 그대로 in-place (기존 프로젝트 수정/분석 의도 보존)
- INV-O5: explicit_out(--workspace) 지정 시 최우선
"""
import os
import sys
from pathlib import Path

import pytest

from core.output_paths import (
    resolve_product_output_dir,
    _is_within,
    _norm,
)


# ── INV-O3: 일반 폴더 in-place ───────────────────────────────────────────────

def test_general_folder_resolves_in_place(tmp_path):
    """repo 밖 cwd → cwd 그대로 (slug 하위폴더 강제 금지 — 기존 프로젝트 in-place)."""
    base = tmp_path / "af_repo"
    base.mkdir()
    cwd = tmp_path / "user_work"
    cwd.mkdir()

    result = resolve_product_output_dir("Todo App", str(cwd), None, base_dir=str(base))

    # 하위폴더가 아니라 cwd 자기 자신이어야 한다
    assert _norm(result) == _norm(str(cwd))


def test_deployed_user_creates_in_cwd(tmp_path):
    """배포 사용자(repo 밖) → cwd in-place (현재 위치 기준 동작 유지)."""
    base = tmp_path / "install" / "af"
    base.mkdir(parents=True)
    cwd = tmp_path / "home" / "projects"
    cwd.mkdir(parents=True)

    result = resolve_product_output_dir("My Cool App", str(cwd), None, base_dir=str(base))

    assert _norm(result) == _norm(str(cwd))
    # cwd가 base 밖이므로 리다이렉트는 발동하지 않는다
    assert not _is_within(str(cwd), _norm(str(base)))


# ── INV-O2: AF-repo 안 → projects/<slug> graceful 리다이렉트 ─────────────────

def test_inside_af_repo_redirects_to_projects(tmp_path):
    """cwd == BASE_DIR → <base_dir>/projects/<slug> 로 리다이렉트 (에러 X)."""
    base = tmp_path / "af_repo"
    base.mkdir()

    result = resolve_product_output_dir("Todo App", str(base), None, base_dir=str(base))

    assert _norm(result) == _norm(str(base / "projects" / "todo_app"))


def test_inside_af_repo_subdir_redirects(tmp_path):
    """cwd = BASE_DIR/하위폴더 → projects/<slug> 리다이렉트 (단순 abspath 비교가 못 잡던 갭)."""
    base = tmp_path / "af_repo"
    sub = base / "scripts" / "nested"
    sub.mkdir(parents=True)

    result = resolve_product_output_dir("Todo App", str(sub), None, base_dir=str(base))

    assert _norm(result) == _norm(str(base / "projects" / "todo_app"))
    # 산출물이 AF 소스(scripts/) 안에 떨어지지 않음을 확인
    assert not _is_within(result, _norm(str(sub)))


def test_inside_projects_dir_resolves_in_place(tmp_path):
    """cwd가 이미 projects/<app> 안이면 in-place (cross-review F1).

    projects/ 는 격리 sink라 그 안에서의 실행은 "기존 앱 수정" 의도 →
    새 projects/<slug> 로 리다이렉트하지 않고 cwd 그대로 써야 한다.
    """
    base = tmp_path / "af_repo"
    app = base / "projects" / "todo_app"
    app.mkdir(parents=True)

    result = resolve_product_output_dir("Fix the bug", str(app), None, base_dir=str(base))

    assert _norm(result) == _norm(str(app))


# ── INV-O5: explicit_out 우선 ────────────────────────────────────────────────

def test_explicit_out_overrides_redirect(tmp_path):
    """explicit_out 지정 시 AF-repo 안이어도 그대로 사용(명시 의도 존중)."""
    base = tmp_path / "af_repo"
    base.mkdir()
    out = tmp_path / "explicit_target"

    result = resolve_product_output_dir("X", str(base), str(out), base_dir=str(base))
    assert _norm(result) == _norm(str(out))


def test_explicit_out_expands_user(tmp_path, monkeypatch):
    """explicit_out의 ~ 확장 + abspath 정규화."""
    base = tmp_path / "af_repo"
    base.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    result = resolve_product_output_dir("X", str(base), "~/target", base_dir=str(base))
    assert _norm(result) == _norm(str(tmp_path / "target"))


# ── slug 생성 (리다이렉트 경로에만 적용) ──────────────────────────────────────

def test_slug_from_task_input(tmp_path):
    """AF-repo 안 task_input → 안전한 slug (소문자, 비영숫자→_)."""
    base = tmp_path / "af_repo"
    base.mkdir()

    result = resolve_product_output_dir("Build A Todo-App! v2", str(base), None, base_dir=str(base))
    assert os.path.basename(_norm(result)) == "build_a_todo_app_v2"


def test_slug_length_capped(tmp_path):
    """긴 자연어 task → slug 길이 cap (Windows MAX_PATH 방어, 설계리뷰 #5)."""
    from core.output_paths import _MAX_SLUG_LEN

    base = tmp_path / "af_repo"
    base.mkdir()
    long_task = "Build a comprehensive enterprise grade real time analytics dashboard with auth"

    result = resolve_product_output_dir(long_task, str(base), None, base_dir=str(base))
    slug = os.path.basename(_norm(result))
    assert len(slug) <= _MAX_SLUG_LEN
    assert not slug.endswith("_")  # 잘린 끝 '_' 제거 확인


def test_empty_task_input_falls_back_to_default(tmp_path):
    """AF-repo 안 빈 task_input → 'default' slug (_boot_safe_id 계약)."""
    base = tmp_path / "af_repo"
    base.mkdir()

    result = resolve_product_output_dir("", str(base), None, base_dir=str(base))
    assert os.path.basename(_norm(result)) == "default"


# ── _is_within 헬퍼 (Windows 케이스 비민감성) ────────────────────────────────

def test_is_within_exact_match(tmp_path):
    base_n = _norm(str(tmp_path))
    assert _is_within(str(tmp_path), base_n)


def test_is_within_subdir(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    base_n = _norm(str(tmp_path))
    assert _is_within(str(sub), base_n)


def test_is_within_sibling_not_matched(tmp_path):
    base = tmp_path / "afroot"
    sibling = tmp_path / "afroot_other"  # prefix 유사하나 별개 디렉터리
    base.mkdir()
    sibling.mkdir()
    base_n = _norm(str(base))
    assert not _is_within(str(sibling), base_n)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 케이스 비민감 가드 전용")
def test_redirect_case_insensitive_on_windows(tmp_path):
    """Windows: 대소문자 다른 경로도 같은 repo로 인식해 리다이렉트 발동."""
    base = tmp_path / "AF_Repo"
    base.mkdir()
    cwd_variant = str(base).lower()  # 케이스만 다른 동일 경로

    result = resolve_product_output_dir("X", cwd_variant, None, base_dir=str(base))
    # in-place(cwd)가 아니라 projects/ 하위로 리다이렉트돼야 한다
    assert "projects" in _norm(result).split(os.sep)


# ── INV-O4: dogfood 경로 불변 ────────────────────────────────────────────────

def test_dogfood_path_unaffected():
    """INV-O4: dogfood는 ad-hoc resolve를 안 타고 worktree 모델(cwd_for_execution)을 쓴다."""
    import core.dogfood as dogfood_mod

    src = Path(dogfood_mod.__file__).read_text(encoding="utf-8")
    assert "resolve_product_output_dir" not in src
    assert "_resolve_ad_hoc_workspace" not in src
    assert "worktree_workspace" in src

"""
core/output_paths.py
=====================
ad-hoc 새 제품 생성 경로의 출력 디렉터리 결정 + AF-repo 오염 격리.

설계: docs/2026-06-18-product-output-isolation-design.md (in-place 복원 개정 2026-06-22)

배경: AF에는 제품 생성 경로가 둘이다.
  - dogfood: ~/.af-dogfood/<run_id>/worktree (격리됨, 본 모듈 대상 아님)
  - ad-hoc("~만들어줘"/"~수정해줘"): 사용자 cwd에서 그 프로젝트를 in-place로
    분석·수정·스캐폴딩한다.

이 모듈의 유일한 책임: ad-hoc 산출물이 **AF 소스 레포(core/scripts/tests)**를
오염시키지 않게 하는 것. 그래서 cwd가 AF 레포 안일 때만 projects/ 하위로 리다이렉트하고,
그 외 일반 폴더에서는 cwd를 그대로 써서 "기존 프로젝트 in-place 수정" 의도를 보존한다.
"""
from __future__ import annotations

import os

from typing import Final

from core.config_paths import BASE_DIR, _boot_safe_id

# slug 길이 cap — task_input이 전체 자연어 문장일 수 있어, cap 없으면
# projects/<slug>/agents/... 가 Windows MAX_PATH(260) 초과 가능 (설계리뷰 #5).
_MAX_SLUG_LEN: Final = 40


def _norm(p: str) -> str:
    """경로 정규화 — Windows 케이스 비민감성/심볼릭링크 대응.

    security_guard.py:95 runner 템플릿 안의 동일 _norm 패턴과 같으나,
    그쪽은 f-string 템플릿 내부(subprocess runner 코드-as-텍스트)라 import 불가.
    """
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def _is_within(path: str, root_norm: str) -> bool:
    """path가 정규화된 root_norm과 같거나 그 하위인지 판정."""
    p = _norm(path)
    return p == root_norm or p.startswith(root_norm + os.sep)


def resolve_product_output_dir(
    task_input: str,
    cwd: str,
    explicit_out: str | None,
    base_dir: str = BASE_DIR,
) -> str:
    """ad-hoc 새 제품/수정 작업의 산출물 디렉터리를 결정한다.

    ① explicit_out(--workspace/-w) 지정 시 최우선 (INV-O5)
    ② cwd가 base_dir(AF repo) 하위면 <base_dir>/projects/<slug> 로 graceful 리다이렉트
       (INV-O2: AF 소스 오염 방지 — 에러를 던지지 않고 격리 위치로 보낸다)
    ③ 그 외(배포 사용자/기존 프로젝트): cwd 그대로 in-place
       (INV-O3: "기존 프로젝트 안에서 수정·분석" 사용자 의도 보존)

    ②는 fail-closed(에러)가 아니라 리다이렉트다 — 사용자가 AF 레포 안에서 무심코
    실행해도 core/scripts/tests를 더럽히지 않고 projects/ 하위로 격리만 한다.
    projects/ 는 .gitignore 정책상 외부 앱 작업공간 영역이라 AF 소스와 분리된다.

    explicit_out은 빈 문자열("")을 None(미지정)과 동일 취급한다 —
    빈 값이 in-place 판정을 우회하지 않도록 falsy 체크를 의도적으로 사용한다.
    """
    if explicit_out:
        return os.path.abspath(os.path.expanduser(explicit_out))

    projects_dir = os.path.join(os.path.abspath(base_dir), "projects")
    # 가드의 목적은 AF **소스**(core/scripts/tests 등) 오염 방지뿐이다.
    # projects/ 는 이미 격리 sink(외부 앱 작업공간)이므로, 그 안에서의 실행은
    # "기존 앱 in-place 수정" 의도로 보고 리다이렉트하지 않는다(cross-review F1).
    if _is_within(cwd, _norm(base_dir)) and not _is_within(cwd, _norm(projects_dir)):
        # cap 후 잘린 끝의 '_' 제거; 전부 잘려 빈 값이면 _boot_safe_id 계약대로 "default"
        slug = _boot_safe_id(task_input)[:_MAX_SLUG_LEN].rstrip("_") or "default"
        return os.path.join(projects_dir, slug)

    return os.path.abspath(os.path.expanduser(cwd))

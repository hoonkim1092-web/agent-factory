"""
core/research_engine.py — 사서(Librarian) 모듈 + NotebookLM 통합 엔진

v3 (2026-04-13): notebooklm_tools → nlm, 하드코딩 UUID 제거, state 기반 로드.
설계 문서: docs/features/2026-04-10-setup-wizard-tavily-notebooklm-integration.md §4.7
"""
import sys
import os
import subprocess
import json
import time
from enum import Enum
from typing import Optional

# NOTE: DEFAULT_ARCHIVE_NOTEBOOK_ID 상수는 v3에서 제거되었다.
# 사용자별 archive 노트북 UUID는 .af_setup_state.json에 저장되며,
# _get_archive_notebook_id()가 core.setup_wizard._load_setup_state()를 통해 로드한다.

# archive 노트북 미설정 시 stderr 경고를 프로세스당 1회만 출력하기 위한 플래그
# (WARN-2 대응: frozen + 미설정 사용자가 실행마다 경고를 반복해서 보지 않도록)
_ARCHIVE_SKIP_LOGGED = False


class ResearchMode(Enum):
    FAST = "fast"
    DEEP = "deep"


# ═══════════════════════════════════════════════════════════════════════════
# NotebookLM CLI 래퍼 인프라 (frozen-aware)
# ═══════════════════════════════════════════════════════════════════════════

def _get_archive_notebook_id() -> Optional[str]:
    """BLOCK-C 해소: state 파일에서 사용자별 archive_notebook_id를 로드.

    setup_wizard가 저장한 `.af_setup_state.json`의 `notebooklm.archive_notebook_id`를
    반환한다. 파일이 없거나 설정되지 않은 경우 None → 호출자가 쿼리를 스킵하거나
    wizard 재실행을 유도해야 한다.
    """
    try:
        from core.setup_wizard import _load_setup_state
        state = _load_setup_state()
        return state.get("notebooklm", {}).get("archive_notebook_id")
    except Exception:
        return None


def _nlm_cmd_base() -> list[str]:
    """frozen vs 개발 환경에 따라 nlm 호출 prefix 반환.

    - PyInstaller frozen: af 자체의 `__nlm` 숨은 서브커맨드 사용 (nlm 재귀 import 회피)
    - 개발 환경: 시스템 PATH의 `nlm` CLI 사용 (notebooklm-cli 패키지)
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "__nlm"]
    return ["nlm"]


def _nlm_env() -> dict:
    """NotebookLM CLI 실행을 위한 환경변수를 준비한다."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _is_auth_error(text: str) -> bool:
    t = (text or "").lower()
    return any(
        f in t
        for f in (
            "authentication expired",
            "authentication failed",
            "profile not found",
            "not authenticated",
            "clientauthenticationerror",
            "rpc error 16",
            "run 'nlm login'",
        )
    )


def _reauth_notebooklm() -> bool:
    cmd = _nlm_cmd_base() + ["login"]
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_nlm_env(),
            timeout=300,
        )
        combined = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0 and not _is_auth_error(combined)
    except Exception:
        return False


def _nlm_cli(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    """NotebookLM CLI 래퍼. 인증 만료 감지 시 1회 자동 재인증 후 재시도."""
    cmd = _nlm_cmd_base() + list(args)
    env = _nlm_env()
    p = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", env=env, timeout=timeout
    )
    combined = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 and _is_auth_error(combined):
        print("[RESEARCH] 인증 만료 감지 → 자동 재인증 시도...")
        if _reauth_notebooklm():
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=timeout,
            )
    return p


# ═══════════════════════════════════════════════════════════════════════════
# 0. 리서치 복잡도 판정기 (Autonomous Depth Classifier)
# ═══════════════════════════════════════════════════════════════════════════

def classify_research_depth(query: str, missing_skills_count: int = 0) -> ResearchMode:
    """쿼리의 복잡도와 상황을 분석하여 Fast 또는 Deep 모드를 결정한다."""
    q = query.lower()

    deep_keywords = [
        "architecture", "아키텍처", "설계", "strategy", "전략", "심층", "deep",
        "analysis", "분석", "비교", "compare", "benchmark", "벤치마크",
        "recipe", "playbook", "레시피", "플레이북", "구조", "structure",
    ]
    fast_keywords = [
        "check", "확인", "정의", "뜻", "what is", "단순", "simple", "quick",
    ]

    if any(k in q for k in deep_keywords) or len(query) > 200:
        return ResearchMode.DEEP
    if missing_skills_count >= 3:
        return ResearchMode.DEEP
    if any(k in q for k in fast_keywords):
        return ResearchMode.FAST
    return ResearchMode.FAST


# ═══════════════════════════════════════════════════════════════════════════
# 1. NotebookLM 쿼리 (archive 기본값은 state 기반)
# ═══════════════════════════════════════════════════════════════════════════

def query_notebooklm(
    query: str,
    notebook_id: Optional[str] = None,
    mode: Optional[ResearchMode] = None,
) -> str:
    """NotebookLM에 쿼리를 던져 심층 분석 결과를 가져온다.

    notebook_id 미지정 시 `.af_setup_state.json`의 archive 노트북을 사용한다.
    archive가 설정되지 않은 경우 빈 문자열을 반환(graceful skip)한다.
    mode가 None이면 classify_research_depth로 자동 결정한다.
    """
    target_id = notebook_id or _get_archive_notebook_id()
    if not target_id:
        global _ARCHIVE_SKIP_LOGGED
        if not _ARCHIVE_SKIP_LOGGED:
            print(
                "[RESEARCH] NotebookLM archive 노트북 미설정 → 쿼리 스킵 "
                "(`af setup` 재실행 시 아카이브를 구성할 수 있음)",
                file=sys.stderr,
            )
            _ARCHIVE_SKIP_LOGGED = True
        return ""

    target_mode = mode or classify_research_depth(query)
    # mode는 호출자가 sticky/routing 용도로 사용할 수 있지만, 현재 nlm CLI 0.1.12의
    # `notebook query` 서브커맨드에는 `--mode` 옵션 자체가 없다 (Q4/af-cross-review).
    # 과거 구현은 `--mode`를 붙여서 실패시킨 뒤 옵션을 제거한 폴백을 재호출 — 매 쿼리당
    # 180초 timeout이 두 번(최악 6분) 누적됐다. 현재는 처음부터 옵션 없이 호출한다.
    print(f"[RESEARCH] NotebookLM Query (Mode: {target_mode.value})")

    try:
        p = _nlm_cli("notebook", "query", target_id, query, timeout=180)

        if p.returncode != 0:
            print(
                f"[RESEARCH Error] NotebookLM query 실패: {(p.stderr or '').strip()}",
                file=sys.stderr,
            )
            return ""

        return (p.stdout or "").strip()
    except Exception as e:
        print(f"[RESEARCH Error] NotebookLM 연결 실패: {e}", file=sys.stderr)
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# 2. 소스 주입 (Source Injection)
# ═══════════════════════════════════════════════════════════════════════════

def create_notebook(title: str) -> Optional[str]:
    """NotebookLM에 새 노트북을 생성하고 notebook_id를 반환한다."""
    try:
        p = _nlm_cli("notebook", "create", title, timeout=60)
        if p.returncode != 0:
            print(f"⚠️ [사서] 노트북 생성 실패: {(p.stderr or '').strip()}")
            return None

        output = (p.stdout or "").strip()
        try:
            data = json.loads(output)
            nb_id = (
                data.get("notebook_id")
                or data.get("id")
                or data.get("notebook", {}).get("id")
            )
            if nb_id:
                print(f"📓 [사서] 새 노트북 생성됨: {title} (ID: {nb_id})")
                return str(nb_id)
        except (json.JSONDecodeError, AttributeError):
            pass

        import re
        uuid_match = re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            output,
            re.IGNORECASE,
        )
        if uuid_match:
            nb_id = uuid_match.group(0)
            print(f"📓 [사서] 새 노트북 생성됨: {title} (ID: {nb_id})")
            return nb_id

        print(
            f"⚠️ [사서] 노트북은 생성되었으나 ID를 추출할 수 없습니다.\n  출력: {output[:300]}"
        )
        return None
    except Exception as e:
        print(f"⚠️ [사서] 노트북 생성 중 오류: {e}")
        return None


def inject_source_url(notebook_id: str, url: str) -> bool:
    """단일 URL을 NotebookLM 노트북에 소스로 추가한다."""
    try:
        p = _nlm_cli("source", "add", notebook_id, "--url", url, timeout=60)
        if p.returncode != 0:
            print(
                f"  ⚠️ 소스 추가 실패 ({url[:60]}): {(p.stderr or '').strip()[:200]}"
            )
            return False
        print(f"  ✅ 소스 추가됨: {url[:80]}")
        return True
    except Exception as e:
        print(f"  ⚠️ 소스 추가 중 오류 ({url[:60]}): {e}")
        return False


def inject_source_text(notebook_id: str, text: str, title: str = "Pasted Text") -> bool:
    """텍스트 내용을 NotebookLM 노트북에 소스로 추가한다."""
    try:
        p = _nlm_cli(
            "source", "add", notebook_id,
            "--text", text[:45000], "--title", title,
            timeout=60,
        )
        if p.returncode != 0:
            print(
                f"  ⚠️ 텍스트 소스 추가 실패 ({title}): {(p.stderr or '').strip()[:200]}"
            )
            return False
        print(f"  ✅ 텍스트 소스 추가됨: {title}")
        return True
    except Exception as e:
        print(f"  ⚠️ 텍스트 소스 추가 중 오류 ({title}): {e}")
        return False


def inject_sources(notebook_id: str, urls: list[str], delay: float = 1.0) -> dict:
    """여러 URL을 NotebookLM 노트북에 순차적으로 소스로 주입한다."""
    injected = 0
    failed = 0
    total = len(urls)

    print(f"📥 [사서] {total}개의 소스를 노트북({notebook_id[:8]}...)에 주입합니다...")

    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{total}] 소스 주입 중: {url[:80]}")
        ok = inject_source_url(notebook_id, url)
        if ok:
            injected += 1
        else:
            failed += 1
        if i < total and delay > 0:
            time.sleep(delay)

    print(f"📊 [사서] 소스 주입 완료: 성공 {injected}/{total}, 실패 {failed}")
    return {"injected": injected, "failed": failed, "total": total}


# ═══════════════════════════════════════════════════════════════════════════
# 3. 프롬프트 생성기
# ═══════════════════════════════════════════════════════════════════════════

def generate_deep_research_prompt(role: str) -> str:
    """Domain Deep-Dive 템플릿 생성 (Himari 전용)."""
    return f"""
    Target Role/Domain: {role}

    WARNING: Do NOT provide generic encyclopedia answers.
    Act as a hyper-specialized domain expert. Break down the exact operational realities for '{role}'.

    You MUST provide detailed, actionable data addressing these 4 pillars:

    1. [Current Context (Season/Time)]: What is critical RIGHT NOW? (e.g., Seasonal ingredients like 방어 in Winter, current market trends, time-sensitive risks).
    2. [Business/FinOps (Cost/Margin)]: What are the exact cost drivers? What is the target cost percentage (e.g., 'Target food cost 35%')? How does this role maximize profit margins and defend ROI?
    3. [Resources/Tools]: What specific, professional-grade tools/equipment/software/prerequisites are absolutely mandatory? (e.g., 야나기바, specific POS, specific machinery).
    4. [Execution (Recipe/Playbook)]: Provide a step-by-step, actionable 'Recipe' or 'Playbook' that this role executes on the floor. Be concrete, not abstract.

    Return the insights structured clearly around these 4 pillars.
    """.strip()

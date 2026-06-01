"""
core/utils.py
=============
범용 유틸리티 + 하위 호환 재수출 허브.

[모듈화 2026-03-01]
기능별 전담 모듈로 분해:
  - core.file_io        : YAML/Text 파일 I/O + 캐시
  - core.security_guard : 코드 보안 검사 + 격리 실행
  - core.dashboard      : 대시보드 JSON 관리
  - core.memory         : 에이전트 메모리

기존 `from core.utils import read_yaml` 등의 import를 깨뜨리지 않도록
모든 공개 심볼을 여기서 re-export 합니다.
"""

import math
import os
import re
import json
import random
import sys
from datetime import datetime
from core.config_paths import *

# =============================================================================
# [Re-Export] 하위 호환 — 기존 import 경로 유지
# =============================================================================
# file_io
from core.file_io import (
    read_yaml, write_yaml, write_text, sha256_text,
    _env_flag, _sha256_file, _yaml_cache_put,
)

# security_guard
from core.security_guard import (
    safe_generate, quick_guard, run_isolated, build_child_env,
    MAX_ITERATIONS, TEST_TIMEOUT_SEC,
    CHILD_ENV_PASSTHROUGH, BANNED_IMPORT_TOPS, BANNED_CALLS,
)

# dashboard
from core.dashboard import (
    append_dashboard_run, _safe_write_json, validate_context_with_schema,
)

# memory
from core.memory import read_core_memory

# executor (기존 re-export 유지)
from core.executor import run_skill_safely


# =============================================================================
# [Local] 범용 유틸리티 — 여기에만 존재하는 함수들
# =============================================================================
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_id(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return (t[:60] if t else "skill")


def safe_optional_id(text: str | None) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t[:60]


def truncate_text(text: str | None, max_len: int, suffix: str = "...") -> str:
    """문자열을 max_len 글자 이하로 자른다. 초과 시 suffix를 뒤에 붙인다."""
    s = text or ""
    if len(s) <= max_len:
        return s
    if max_len <= len(suffix):
        return s[:max_len]
    return s[: max_len - len(suffix)] + suffix


def clamp(value: int | float, min_val: int | float, max_val: int | float) -> int | float:
    """value를 [min_val, max_val] 범위로 제한한다. min_val > max_val이면 ValueError."""
    if min_val > max_val:
        raise ValueError(f"잘못된 범위: min_val({min_val}) > max_val({max_val})")
    return max(min_val, min(value, max_val))


def clamp_ratio(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """value를 [lo, hi] 범위로 클램프한 float을 반환한다. lo > hi이면 ValueError."""
    if lo > hi:
        raise ValueError(f"잘못된 범위: lo({lo}) > hi({hi})")
    return float(max(lo, min(value, hi)))


def median(values: list[int | float]) -> float:
    """정렬된 중앙값을 반환한다. 빈 리스트이면 ValueError."""
    if not values:
        raise ValueError("빈 리스트에서 중앙값을 계산할 수 없습니다.")
    s = sorted(values)
    m = len(s) // 2
    if len(s) % 2 == 1:
        return float(s[m])
    return (s[m - 1] + s[m]) / 2.0


def mode(values: list[int | float]) -> float:
    """최빈값을 float로 반환한다. 동률이면 입력 리스트에서 가장 먼저 등장한 값을 반환. 빈 리스트이면 ValueError."""
    if not values:
        raise ValueError("빈 리스트에서 최빈값을 계산할 수 없습니다.")
    counts: dict = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    max_count = max(counts.values())
    for v in values:
        if counts[v] == max_count:
            return float(v)
    return float(values[0])


def variance(values: list[int | float]) -> float:
    """모집단 분산을 반환한다. 빈 리스트이면 ValueError."""
    if not values:
        raise ValueError("빈 리스트에서 분산을 계산할 수 없습니다.")
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def std_dev(values: list[int | float]) -> float:
    """모집단 표준편차를 반환한다. 빈 리스트이면 ValueError."""
    return math.sqrt(variance(values))


def zscore(values: list[int | float]) -> list[float]:
    """각 원소의 Z-score를 반환한다. 빈 리스트이면 ValueError. 원소 1개 또는 표준편차 0이면 모두 0.0."""
    if not values:
        raise ValueError("빈 리스트에서 Z-score를 계산할 수 없습니다.")
    if len(values) == 1:
        return [0.0]
    mean = sum(values) / len(values)
    sd = std_dev(values)
    if sd == 0.0:
        return [0.0] * len(values)
    return [(x - mean) / sd for x in values]


def percentile(values: list[int | float], p: float) -> float:
    """p번째 백분위수를 선형 보간으로 반환한다. 빈 리스트이면 ValueError. p가 0~100 범위 밖이면 ValueError."""
    if not values:
        raise ValueError("빈 리스트에서 백분위수를 계산할 수 없습니다.")
    if p < 0.0 or p > 100.0:
        raise ValueError(f"p는 0.0~100.0 범위여야 합니다: {p}")
    s = sorted(values)
    idx = p / 100.0 * (len(s) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(s[lo])
    frac = idx - lo
    return float(s[lo] * (1.0 - frac) + s[hi] * frac)


def range_span(values: list[int | float]) -> float:
    """최댓값과 최솟값의 차이를 float로 반환한다. 빈 리스트이면 ValueError."""
    if not values:
        raise ValueError("빈 리스트에서 범위를 계산할 수 없습니다.")
    return float(max(values) - min(values))


def normalize(values: list[float]) -> list[float]:
    """입력 리스트를 [0.0, 1.0] 범위로 선형 정규화한다.

    빈 리스트이면 빈 리스트 반환. 모든 값이 동일하면 [0.0] * len(values) 반환.
    """
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.0] * len(values)
    span = hi - lo
    return [(x - lo) / span for x in values]


def cumsum(values: list[int | float]) -> list[float]:
    """각 위치까지의 누적 합 리스트를 float로 반환한다. 빈 리스트이면 빈 리스트 반환."""
    result: list[float] = []
    total = 0.0
    for x in values:
        total += x
        result.append(total)
    return result


def running_max(values: list[int | float]) -> list[int | float]:
    """각 위치까지의 누적 최댓값 리스트를 반환한다. 빈 리스트이면 빈 리스트 반환.

    원소 타입을 보존한다 — 입력 값을 그대로 비교·반환하므로 정수 입력은 정수로 유지된다.
    """
    result: list[int | float] = []
    current_max: int | float | None = None
    for x in values:
        if current_max is None or x > current_max:
            current_max = x
        result.append(current_max)
    return result


def chunks(lst: list, n: int) -> list[list]:
    """리스트를 최대 n개 크기의 서브리스트로 분할한다. n < 1이면 ValueError."""
    if n < 1:
        raise ValueError(f"청크 크기는 1 이상이어야 합니다: {n}")
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def flatten(lst: list) -> list:
    """리스트를 1단계만 평탄화한다. 중첩이 2단계 이상이면 첫 번째 단계만 풀린다."""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result


def _split_env_paths(raw: str | None) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


_SAFE_STEM_RE = re.compile(r"^[\w\-\.]+$")


def test_file_for(target: str) -> str | None:
    """소스 파일 경로에 대응하는 관례적 테스트 파일 경로를 반환한다.

    core/ 또는 scripts/ 하위 .py 파일에만 대응하며, 그 외는 None.
    shell 메타문자를 포함한 stem은 None 반환 (caller가 shell command에 안전하게 사용 가능).
    """
    from pathlib import Path
    p = Path(target)
    if p.suffix == ".py" and p.parent.name in ("core", "scripts"):
        if _SAFE_STEM_RE.match(p.stem):
            return f"tests/test_{p.stem}.py"
    return None


def strip_code_fences(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json|python)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def safe_json_load(s: str) -> dict:
    s = strip_code_fences(s)
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        return json.loads(m.group(0)) if m else {}


# =============================================================================
# [Local] 에이전트 헬퍼
# =============================================================================
def get_random_signature(agent_config: dict) -> str:
    """무작위 시그니처 대사를 반환합니다."""
    lines = agent_config.get("signature_lines")
    if not lines and "persona" in agent_config:
        lines = agent_config["persona"].get("signature_lines")
    if lines and isinstance(lines, list):
        return random.choice(lines)
    return ""


def safe_print(text: str) -> None:
    """유니코드 인코딩 오류를 안전하게 처리하며 출력."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = str(text).encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe)


def print_agent_msg(name: str, msg: str, signature: str = "", phase=None, visualizer=None):
    """에이전트 이름과 메시지, 그리고 시그니처 대사를 출력합니다.

    Args:
        phase: AgentPhase enum (terminal_visualizer 모듈). 주어지면 visualizer에 상태 업데이트.
        visualizer: TerminalVisualizer 인스턴스. None이면 기본 print 출력.
    """
    header = f"[{name}]"
    if signature:
        safe_print(f"\n{header} \"{signature}\"")
        safe_print(f"{header} {msg}")
    else:
        safe_print(f"{header} {msg}")

    if visualizer is not None and phase is not None:
        try:
            visualizer.update_phase(name, phase)
        except Exception:
            pass


def is_codex_model(model_name: str) -> bool:
    m = (model_name or "").strip().lower()
    return m.startswith("codex") or m.startswith("gpt-5")


def is_claude_model(model_name: str) -> bool:
    m = (model_name or "").strip().lower()
    return m.startswith("claude")


# =============================================================================
# [Local] 프로젝트 정책/설정
# =============================================================================
def read_project_policies() -> dict:
    data = read_yaml(POLICIES_PATH)
    return data if isinstance(data, dict) else {}


def read_skill_lock() -> dict:
    data = read_yaml(SKILL_LOCK_PATH)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("skills", {})
    return data


def lock_skill_state(skill_id: str, patch: dict | None = None):
    sid = safe_id(skill_id)
    if not sid:
        return
    lock = read_skill_lock()
    skills = lock.get("skills", {})
    if not isinstance(skills, dict):
        skills = {}
    prev = skills.get(sid, {})
    if not isinstance(prev, dict):
        prev = {}
    merged = dict(prev)
    if isinstance(patch, dict):
        for k, v in patch.items():
            merged[k] = v
    merged["updated_at"] = now_iso()
    if not str(merged.get("version", "")).strip():
        merged["version"] = "1.0.0"
    if not str(merged.get("status", "")).strip():
        merged["status"] = "active"
    skills[sid] = merged
    lock["skills"] = skills
    write_yaml(SKILL_LOCK_PATH, lock)


def read_project_settings() -> dict:
    data = read_yaml(PROJECT_SETTINGS_PATH)
    return data if isinstance(data, dict) else {}


# =============================================================================
# [Local] 경로 해석 + 에이전트 오버라이드
# =============================================================================
def resolve_existing_path(path_text: str) -> str | None:
    p = str(path_text or "").strip()
    if not p:
        return None
    if os.path.isabs(p) and os.path.exists(p):
        return os.path.normpath(p)
    for root in (BASE_DIR, SKILLS_DIR, PROJECT_ROOT):
        cand = os.path.normpath(os.path.join(root, p))
        if os.path.exists(cand):
            return cand
    return None


def to_portable_path(path_text: str) -> str:
    # Convert an abs/rel path to repo-relative POSIX when it lives under
    # BASE_DIR. We intentionally do NOT require the path to exist on disk —
    # eval/promotion reports are serialized before the file is flushed, and
    # PC-specific abs paths must never leak into committed artifacts.
    # Paths outside BASE_DIR fall back to abs (POSIX-normalized).
    p = str(path_text or "").strip()
    if not p:
        return p
    # Already a portable rel path (no abs prefix, no backslash) — keep as-is.
    if not os.path.isabs(p) and "\\" not in p:
        return p
    abs_p = os.path.normpath(p if os.path.isabs(p) else os.path.join(BASE_DIR, p))
    try:
        rel = os.path.relpath(abs_p, BASE_DIR)
        if not rel.startswith(".."):
            return rel.replace("\\", "/")
    except Exception:
        pass
    return abs_p.replace("\\", "/")


def is_portable_rel_path(path_text: str) -> bool:
    p = str(path_text or "").strip()
    if not p:
        return False
    return not os.path.isabs(p) and "\\" not in p


def resolve_skill_paths(skill_id: str) -> tuple[str | None, str | None]:
    sid = safe_id(skill_id)
    settings = read_project_settings()
    pref = settings.get("skill_overrides", {}) if isinstance(settings.get("skill_overrides"), dict) else {}
    prefer_project = bool(pref.get("prefer_project_skills", True))
    project_py = os.path.join(PROJECT_SKILLS_DIR, sid, "skill.py")
    project_meta = os.path.join(PROJECT_SKILLS_DIR, sid, "meta.yaml")
    global_py = os.path.join(SKILLS_DIR, sid, "skill.py")
    global_meta = os.path.join(SKILLS_DIR, sid, "meta.yaml")
    ordered = (
        [(project_py, project_meta), (global_py, global_meta)]
        if prefer_project
        else [(global_py, global_meta), (project_py, project_meta)]
    )
    for py_path, meta_path in ordered:
        if os.path.exists(py_path):
            return py_path, (meta_path if os.path.exists(meta_path) else None)
    # forge: directory 구조 우선, flat 구조 fallback
    forge_py_dir = os.path.join(SKILLS_DIR, "forge", sid, f"{sid}.py")
    forge_py_flat = os.path.join(SKILLS_DIR, "forge", f"{sid}.py")
    for forge_py in [forge_py_dir, forge_py_flat]:
        if os.path.exists(forge_py):
            return forge_py, None
    return None, None


def skill_markdown_filenames() -> tuple[str, ...]:
    return ("skill.md", "SKILL.md")


def get_external_skill_roots(extra_roots: list[str] | None = None) -> list[str]:
    """Claude Code / Codex / agents 스킬 디렉토리 목록을 반환한다.

    우선순위 (Claude 공식 precedence: personal > project):
      1. personal: ~/.claude/skills, ~/.codex/skills, ~/.agents/skills
      2. project:  SKILLS_DIR (BASE_DIR/skills), PROJECT_ROOT/skills,
                   PROJECT_ROOT/.claude/skills, .codex/skills, .agents/skills
      3. runtime:  $CODEX_HOME/skills
      4. env:      AGENT_CODEX_SKILL_DIRS, AGENT_CLAUDE_SKILL_DIRS
      5. system:   /etc/codex/skills (Linux only; Windows는 env opt-in)
    """
    roots: list[str] = []
    seen: set[str] = set()
    home_dir = os.path.expanduser("~")
    defaults = [
        # 1순위: personal (Claude 공식 precedence: personal > project)
        os.path.join(home_dir, ".claude", "skills"),
        os.path.join(home_dir, ".codex", "skills"),
        os.path.join(home_dir, ".agents", "skills"),
        # 2순위: project (SKILLS_DIR = BASE_DIR/skills, 레포 루트 직속 skills/)
        # AF_SELF_RUN 격리 모드에서는 BASE_DIR/skills 제외 (목표 프로젝트 스킬만 탐색)
        *([SKILLS_DIR] if not _env_flag("AF_SELF_RUN") else []),
        os.path.join(PROJECT_ROOT, "skills"),
        os.path.join(PROJECT_ROOT, ".claude", "skills"),
        os.path.join(PROJECT_ROOT, ".codex", "skills"),
        os.path.join(PROJECT_ROOT, ".agents", "skills"),
    ]
    # 3순위: Codex 런타임 홈
    codex_home = os.getenv("CODEX_HOME", "").strip()
    if codex_home:
        defaults.append(os.path.join(codex_home, "skills"))
    # 5순위: 시스템 경로 (Linux only; Windows는 공식 문서 근거 없어 env opt-in만)
    if os.name != "nt":
        defaults.append("/etc/codex/skills")

    # 4순위: 환경변수 (extra_roots → AGENT_CODEX_SKILL_DIRS → AGENT_CLAUDE_SKILL_DIRS → defaults)
    env_paths = (
        _split_env_paths(os.getenv("AGENT_CODEX_SKILL_DIRS"))
        + _split_env_paths(os.getenv("AGENT_CLAUDE_SKILL_DIRS"))
    )
    for raw_root in list(extra_roots or []) + env_paths + defaults:
        root = str(raw_root or "").strip()
        if not root:
            continue
        normalized = os.path.normpath(os.path.abspath(root))
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        roots.append(normalized)
    return roots


# 하위 호환 alias
get_codex_skill_roots = get_external_skill_roots


def resolve_knowledge_skill_path(skill_id: str, extra_roots: list[str] | None = None) -> str | None:
    sid = safe_id(skill_id)
    if not sid:
        return None
    settings = read_project_settings()
    pref = settings.get("skill_overrides", {}) if isinstance(settings.get("skill_overrides"), dict) else {}
    prefer_project = bool(pref.get("prefer_project_skills", True))
    priority = [PROJECT_SKILLS_DIR, SKILLS_DIR] if prefer_project else [SKILLS_DIR, PROJECT_SKILLS_DIR]
    ordered_roots = get_codex_skill_roots(priority + (extra_roots or []))
    for root in ordered_roots:
        for filename in skill_markdown_filenames():
            candidate = os.path.join(root, sid, filename)
            if os.path.exists(candidate):
                return candidate
    return None


def resolve_any_skill_path(skill_id: str, extra_knowledge_roots: list[str] | None = None) -> str | None:
    skill_py, _meta = resolve_skill_paths(skill_id)
    if skill_py:
        return skill_py
    return resolve_knowledge_skill_path(skill_id, extra_roots=extra_knowledge_roots)


def has_local_skill(skill_id: str, extra_knowledge_roots: list[str] | None = None) -> bool:
    return bool(resolve_any_skill_path(skill_id, extra_knowledge_roots=extra_knowledge_roots))


def _merge_dict(base: dict, override: dict) -> dict:
    out = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def apply_agent_overrides(agent: dict, role_spec: str) -> dict:
    settings = read_project_settings()
    over = settings.get("agent_overrides", {}) if isinstance(settings.get("agent_overrides"), dict) else {}
    key = safe_id(role_spec)
    cfg = over.get(key, {}) if isinstance(over.get(key), dict) else {}
    if not cfg:
        return agent
    merged = _merge_dict(agent, cfg)
    extra = [safe_id(str(s)) for s in (cfg.get("skills_add") or []) if str(s).strip()]
    if extra:
        base_skills = [safe_id(str(s)) for s in (merged.get("skills") or []) if str(s).strip()]
        merged["skills"] = list(dict.fromkeys(base_skills + extra))
    return merged


# =============================================================================
__all__ = [name for name in dir() if not name.startswith('_')]

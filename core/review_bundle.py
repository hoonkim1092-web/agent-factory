"""core/review_bundle.py — review bundle 생성 thin wrapper.

Phase 2-prep D: dev hook (Claude Code) + af.exe 배포 빌드 양쪽에서 동일하게 작동.
- build()    : 변경 파일 목록 → review bundle dict (AST + grep fallback)
- save()     : .af_review_queue/review_bundle.md 로 직렬화
- load()     : 기존 bundle 역직렬화

의존성: core/ast_engine.py (ast-grep-py 미설치 시 grep fallback 자동 전환)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ── AST availability ──────────────────────────────────────────────────────────

def _ast_available() -> bool:
    try:
        import ast_grep_py  # noqa: F401
        return True
    except ImportError:
        return False


# ── grep fallback ─────────────────────────────────────────────────────────────

_RISK_PATTERNS: list[tuple[str, str]] = [
    (r"subprocess\.(run|Popen|call|check_output)", "subprocess_usage"),
    (r"shell\s*=\s*True", "shell_true"),
    (r"shlex\.split", "shlex_split"),
    (r"os\.system", "os_system"),
    (r"eval\s*\(", "eval_usage"),
    (r"exec\s*\(", "exec_usage"),
    (r"__import__", "dynamic_import"),
]


def _grep_risks(file_path: str) -> list[dict]:
    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits: list[dict] = []
    for pattern, risk_id in _RISK_PATTERNS:
        for m in re.finditer(pattern, text):
            line_no = text[: m.start()].count("\n") + 1
            hits.append({"risk_id": risk_id, "line": line_no, "text": m.group(0)})
    return hits


def _ast_risks(file_path: str) -> list[dict]:
    try:
        from core import ast_engine
    except ImportError:
        return _grep_risks(file_path)

    patterns = [
        ("subprocess.$F($$$ARGS)", "subprocess_usage"),
        ("shell=True", "shell_true"),
        ("shlex.split($A)", "shlex_split"),
        ("os.system($A)", "os_system"),
        ("eval($A)", "eval_usage"),
        ("exec($A)", "exec_usage"),
        ("__import__($A)", "dynamic_import"),
    ]
    hits: list[dict] = []
    try:
        for pat, risk_id in patterns:
            for m in ast_engine.search_file(pat, file_path):
                hits.append({"risk_id": risk_id, "line": m["line"], "text": m["text"]})
    except Exception:
        return _grep_risks(file_path)
    return hits


# ── public API ────────────────────────────────────────────────────────────────

def build(changed_files: list[str], workspace: str | None = None) -> dict:
    """changed_files 목록 → review bundle dict.

    AST 분석 가용 시 ast_engine 사용, 미설치 시 regex grep fallback.
    """
    use_ast = _ast_available()
    bundle: dict = {
        "engine": "ast" if use_ast else "grep",
        "files": [],
    }
    for fp in changed_files:
        risks = _ast_risks(fp) if use_ast else _grep_risks(fp)
        bundle["files"].append({"path": fp, "risks": risks})
    return bundle


_RISK_DESC: dict[str, str] = {
    "subprocess_usage": "subprocess 호출 — 사용자 입력이 args에 직접 전달되면 command injection 위험",
    "shell_true": "shell=True — 문자열 명령어 조립 시 injection 가능, list 형태로 교체 권장",
    "shlex_split": "shlex.split — 신뢰 불가 입력에 사용 시 토큰 분리 오동작 가능",
    "os_system": "os.system — subprocess.run 으로 교체 권장, 반환값 무시됨",
    "eval_usage": "eval() — 임의 코드 실행 위험, 사용 맥락 필수 검토",
    "exec_usage": "exec() — 임의 코드 실행 위험, 사용 맥락 필수 검토",
    "dynamic_import": "동적 import — 외부 입력 경로 주입 시 모듈 실행 위험",
}


def save(bundle: dict, workspace: str) -> Path:
    """bundle을 .af_review_queue/review_bundle.md 에 저장 후 경로 반환."""
    queue_dir = Path(workspace) / ".af_review_queue"
    queue_dir.mkdir(exist_ok=True)
    out = queue_dir / "review_bundle.md"
    lines = [f"# review_bundle (engine={bundle.get('engine', '?')})\n"]
    for f in bundle.get("files", []):
        lines.append(f"\n## {f['path']}\n")
        risks = f.get("risks", [])
        if not risks:
            lines.append("_(no risks detected)_\n")
        else:
            for r in risks:
                desc = _RISK_DESC.get(r["risk_id"], r["risk_id"])
                lines.append(
                    f"- L{r['line']} `{r['risk_id']}` — {desc}. "
                    f"코드: `{r['text'].strip()[:120]}`\n"
                )
    out.write_text("".join(lines), encoding="utf-8")
    return out


def load(workspace: str) -> dict | None:
    """저장된 review_bundle.md 반환 (미존재 시 None)."""
    p = Path(workspace) / ".af_review_queue" / "review_bundle.md"
    if not p.exists():
        return None
    return {"raw": p.read_text(encoding="utf-8")}

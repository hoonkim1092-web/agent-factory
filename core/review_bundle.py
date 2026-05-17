"""core/review_bundle.py — review bundle 생성기.

Phase 2: 8-section full bundle (Git Diff / Test Gap / Related Tests /
Direct Callers / Risk Flags / Prior Findings / Stats) + 100KB cap.

Public API:
- build_full(workspace, pending_files) → full bundle dict
- save_full(bundle_full, workspace)    → .af_review_queue/review_bundle.md 경로
- build(changed_files, workspace)      → 기존 risk-scan dict (backward compat)
- save(bundle, workspace)              → 기존 .md 직렬화 (backward compat)
- load(workspace)                      → 기존 bundle 역직렬화

의존성: core/ast_engine.py (ast-grep-py 미설치 시 grep fallback 자동 전환)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_CAP_BYTES = 100 * 1024  # 100 KB


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


# =============================================================================
# Phase 2 — Full 8-Section Bundle
# =============================================================================

def _git_diff(workspace: str, files: list[str]) -> str:
    """git diff HEAD -- files (tracked). Untracked files get synthetic added diff."""
    try:
        rel_files = [os.path.relpath(f, workspace) for f in files]
        r = subprocess.run(
            ["git", "-C", workspace, "diff", "HEAD", "--"] + rel_files,
            capture_output=True, text=True, timeout=15,
        )
        diff = r.stdout
        # Find untracked files
        ls = subprocess.run(
            ["git", "-C", workspace, "ls-files", "--others", "--exclude-standard"] + rel_files,
            capture_output=True, text=True, timeout=5,
        )
        for rel in ls.stdout.splitlines():
            rel = rel.strip()
            if not rel:
                continue
            abs_f = os.path.join(workspace, rel)
            if not os.path.exists(abs_f):
                continue
            try:
                content = Path(abs_f).read_text(encoding="utf-8", errors="replace")
                diff += f"\n--- /dev/null\n+++ b/{rel}\n"
                for line in content.splitlines():
                    diff += f"+{line}\n"
            except Exception:
                pass
        return diff
    except Exception as e:
        return f"(git diff error: {e})"


def _extract_changed_symbols(diff_text: str) -> list[str]:
    """Extract function/class names introduced in diff (lines +def/+class)."""
    symbols: list[str] = []
    for line in diff_text.splitlines():
        m = re.match(r'^\+\s*(def|class)\s+(\w+)', line)
        if m:
            name = m.group(2)
            if name not in symbols and not name.startswith("test_"):
                symbols.append(name)
    return symbols[:20]


def _find_related_tests(workspace: str, pending_files: list[str], changed_symbols: list[str]) -> dict:
    """Return {test_file_path: [test_func_names]} for test files referencing changed code."""
    tests_dir = os.path.join(workspace, "tests")
    if not os.path.isdir(tests_dir):
        return {}

    related: dict[str, None] = {}

    search_terms: list[str] = []
    for fp in pending_files:
        search_terms.append(os.path.basename(fp).removesuffix(".py"))
    for sym in changed_symbols[:5]:
        search_terms.append(sym)

    for term in search_terms:
        try:
            r = subprocess.run(
                ["grep", "-rl", "--include=test_*.py", term, tests_dir],
                capture_output=True, text=True, timeout=5,
            )
            for tf in r.stdout.splitlines():
                tf = tf.strip()
                if tf:
                    related[tf] = None
        except Exception:
            pass

    result: dict[str, list[str]] = {}
    for tf in sorted(related.keys())[:5]:
        try:
            content = Path(tf).read_text(encoding="utf-8", errors="replace")
            funcs = re.findall(r'^def (test_\w+)\(', content, re.MULTILINE)
            result[tf] = funcs[:10]
        except Exception:
            result[tf] = []
    return result


def _caller_context(file_path: str, line_no: int, ctx: int = 5) -> str:
    """Return ±ctx lines around line_no (0-indexed)."""
    try:
        lines = Path(file_path).read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(0, line_no - ctx)
        end = min(len(lines), line_no + ctx + 1)
        return "\n".join(f"{i + 1:>4}: {l}" for i, l in enumerate(lines[start:end], start=start))
    except Exception:
        return ""


def _find_direct_callers(workspace: str, changed_symbols: list[str], max_per_symbol: int = 3) -> list[dict]:
    """Grep core/ + scripts/ for calls to changed_symbols. max 3 per symbol."""
    callers: list[dict] = []
    search_dirs = [d for d in [
        os.path.join(workspace, "core"),
        os.path.join(workspace, "scripts"),
    ] if os.path.isdir(d)]

    for sym in changed_symbols[:10]:
        count = 0
        for d in search_dirs:
            if count >= max_per_symbol:
                break
            try:
                r = subprocess.run(
                    ["grep", "-rn", "--include=*.py", f"{sym}(", d],
                    capture_output=True, text=True, timeout=5,
                )
                for line in r.stdout.splitlines():
                    if count >= max_per_symbol:
                        break
                    parts = line.split(":", 2)
                    if len(parts) < 3:
                        continue
                    caller_file, line_no_str, code = parts
                    # Skip self-definitions
                    if re.match(rf'\s*(def|class)\s+{re.escape(sym)}\b', code):
                        continue
                    try:
                        line_no = int(line_no_str) - 1
                    except ValueError:
                        continue
                    callers.append({
                        "file": caller_file,
                        "line": line_no,
                        "symbol": sym,
                        "context": _caller_context(caller_file, line_no),
                    })
                    count += 1
            except Exception:
                pass
    return callers


def _read_test_gap(workspace: str) -> str:
    p = Path(workspace) / ".af_review_queue" / "test_gap_report.json"
    if not p.exists():
        return "PASS (test_gap_report.json 없음)"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        verdict = data.get("verdict", "unknown")
        gaps = data.get("gaps", [])
        if not gaps:
            return f"PASS (verdict={verdict})"
        lines = [f"verdict={verdict}"]
        for g in gaps[:10]:
            lines.append(f"- {g}")
        return "\n".join(lines)
    except Exception as e:
        return f"(parse error: {e})"


def _read_prior_findings(workspace: str) -> str | None:
    p = Path(workspace) / ".af_review_queue" / "pending_agent_review.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        lr = data.get("last_round_summary")
        if not lr:
            return None
        lines = [f"Round {lr.get('round', '?')} — has_block={lr.get('has_block', False)}"]
        for agent, verdict in lr.get("verdicts", {}).items():
            lines.append(f"  {agent}: {verdict}")
        return "\n".join(lines)
    except Exception:
        return None


def _compute_source_hash(workspace: str, pending_files: list[str], diff_text: str) -> str:
    h = hashlib.sha256()
    p = Path(workspace) / ".af_review_queue" / "pending_agent_review.json"
    if p.exists():
        h.update(p.read_bytes())
    for fp in sorted(pending_files):
        try:
            h.update(str(os.path.getmtime(fp)).encode())
        except Exception:
            pass
    h.update(diff_text.encode("utf-8", errors="replace"))
    return h.hexdigest()[:16]


def _assemble(
    header: str,
    s1: list[str], s2: list[str], s3: list[str],
    s4: list[str], s5: list[str], s6: list[str], s7: list[str],
) -> str:
    return (
        header +
        "".join(s1) + "\n" +
        "".join(s2) + "\n" +
        "".join(s3) + "\n" +
        "".join(s4) + "\n" +
        "".join(s5) + "\n" +
        "".join(s6) + "\n" +
        "".join(s7) + "\n"
    )


def build_full(workspace: str, pending_files: list[str]) -> dict:
    """Full 8-section review bundle with 100KB cap.

    Returns:
        {"bundle_md": str, "source_hash": str, "generated_at": str, "stats": dict}
    """
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    diff_text = _git_diff(workspace, pending_files)
    source_hash = _compute_source_hash(workspace, pending_files, diff_text)

    # blast_tier from queue
    blast_tier = 1
    try:
        pq = Path(workspace) / ".af_review_queue" / "pending_agent_review.json"
        if pq.exists():
            blast_tier = json.loads(pq.read_text(encoding="utf-8")).get("blast_tier", 1)
    except Exception:
        pass

    # Risk flags per file
    use_ast = _ast_available()
    file_risks: dict[str, list[dict]] = {
        fp: (_ast_risks(fp) if use_ast else _grep_risks(fp))
        for fp in pending_files
    }

    changed_symbols = _extract_changed_symbols(diff_text)
    related_tests = _find_related_tests(workspace, pending_files, changed_symbols)
    all_callers = _find_direct_callers(workspace, changed_symbols)
    test_gap_text = _read_test_gap(workspace)
    prior = _read_prior_findings(workspace)

    # §1 Pending Files
    s1 = ["## 1. Pending Files\n"]
    for fp in pending_files:
        rel = os.path.relpath(fp, workspace)
        risk_ids = list({r["risk_id"] for r in file_risks.get(fp, [])})
        flag = f", risk_flags=[{', '.join(risk_ids)}]" if risk_ids else ""
        s1.append(f"- {rel} (blast_tier={blast_tier}{flag})\n")

    # §2 Git Diff
    diff_display = diff_text[:40_000]
    s2 = [f"## 2. Git Diff\n\n```diff\n{diff_display}\n```\n"]
    if len(diff_text) > 40_000:
        s2.append(f"_(diff truncated: {len(diff_text)} chars, showing 40000)_\n")

    # §3 Test Gap
    s3 = [f"## 3. Test Gap Analysis\n\n{test_gap_text}\n"]

    # §4 Related Tests
    s4 = ["## 4. Related Tests\n"]
    if related_tests:
        for tf, funcs in related_tests.items():
            s4.append(f"- {os.path.relpath(tf, workspace)}:\n")
            for fn in funcs:
                s4.append(f"  - {fn}\n")
    else:
        s4.append("_(no related tests found)_\n")

    # §5 Direct Callers (mutable — truncated first for cap)
    s5: list[str] = ["## 5. Direct Callers (1-step)\n"]
    caller_entries: list[tuple[str, str]] = []  # (header_line, context_block)
    if all_callers:
        for c in all_callers:
            rel = os.path.relpath(c["file"], workspace)
            header_line = f"- {rel}:{c['line'] + 1} calls `{c['symbol']}`\n"
            ctx_block = f"```\n{c['context']}\n```\n" if c["context"] else ""
            caller_entries.append((header_line, ctx_block))
    else:
        s5.append("_(no direct callers found)_\n")

    # §6 Risk Flags
    s6 = ["## 6. Risk Flags\n"]
    any_risk = False
    for fp, risks in file_risks.items():
        rel = os.path.relpath(fp, workspace)
        for r in risks:
            s6.append(f"- L{r['line']} `{r['risk_id']}` in {rel}: `{r['text'].strip()[:80]}`\n")
            any_risk = True
    if not any_risk:
        s6.append("_(no risk flags detected)_\n")

    # §7 Prior Findings
    s7 = ["## 7. Prior Findings\n"]
    s7.append(f"{prior}\n" if prior else "_(no prior findings)_\n")

    header = (
        f"# Review Bundle (generated_at: {generated_at}, source_hash: {source_hash})\n\n"
    )

    # Apply 100KB cap: drop caller entries from the back until under cap
    included = list(caller_entries)
    while True:
        s5_full = list(s5)
        for h_line, ctx in included:
            s5_full.append(h_line)
            if ctx:
                s5_full.append(ctx)
        body = _assemble(header, s1, s2, s3, s4, s5_full, s6, s7)
        if len(body.encode("utf-8")) <= _CAP_BYTES or not included:
            s5 = s5_full
            break
        included.pop()

    truncated = len(all_callers) - len(included)
    body = _assemble(header, s1, s2, s3, s4, s5, s6, s7)

    # §8 Stats
    size_bytes = len(body.encode("utf-8"))
    s8 = [
        "## 8. Bundle Stats\n",
        f"- caller files included: {len(included)}/{len(all_callers)}"
        + (f" ({truncated} truncated due to cap)" if truncated else "") + "\n",
        f"- size: {size_bytes // 1024}KB / {_CAP_BYTES // 1024}KB cap\n",
        f"- engine: {'ast' if use_ast else 'grep'}\n",
        f"- changed_symbols detected: {len(changed_symbols)}\n",
    ]

    bundle_md = body + "".join(s8)
    return {
        "bundle_md": bundle_md,
        "source_hash": source_hash,
        "generated_at": generated_at,
        "stats": {
            "size_bytes": len(bundle_md.encode("utf-8")),
            "caller_files_included": len(included),
            "caller_files_truncated": truncated,
            "cap_kb": _CAP_BYTES // 1024,
        },
    }


def save_full(bundle_full: dict, workspace: str) -> Path:
    """Write bundle_md to .af_review_queue/review_bundle.md."""
    queue_dir = Path(workspace) / ".af_review_queue"
    queue_dir.mkdir(exist_ok=True)
    out = queue_dir / "review_bundle.md"
    out.write_text(bundle_full["bundle_md"], encoding="utf-8")
    return out

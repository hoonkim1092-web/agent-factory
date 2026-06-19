"""scripts/review_consensus.py — finding-level evidence collector (S4+S5).

리뷰 합의 게이트 §5.3·§5.4 구현.
.af_review_queue/cr_findings.json (af-cross-review 산출 사이드카)를 읽어
각 ACCEPT/ACCEPT★ finding의 surrounding_code·callers·callees·tests를 수집하고
.af_review_queue/cr_evidence.json을 기록한다.

LLM 미호출 — 순수 코드 증거 수집. 합의 판정은 af-cross-review Step 6(LLM)이 담당.
"""

from __future__ import annotations

import ast as pyast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── surrounding code ──────────────────────────────────────────────────────────

def _surrounding_code(file_path: str, line: int, ctx: int = 10) -> str:
    """Return ±ctx lines around line (1-indexed)."""
    try:
        lines = Path(file_path).read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(0, line - 1 - ctx)
        end = min(len(lines), line - 1 + ctx + 1)
        return "\n".join(f"{i + 1:>4}: {l}" for i, l in enumerate(lines[start:end], start=start))
    except OSError:
        return ""


# ── AST helpers ───────────────────────────────────────────────────────────────

def _enclosing_function(file_path: str, line: int):
    """Return the innermost FunctionDef/AsyncFunctionDef node containing line."""
    try:
        source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        tree = pyast.parse(source, filename=file_path)
    except (OSError, SyntaxError):
        return None

    best = None
    for node in pyast.walk(tree):
        if isinstance(node, (pyast.FunctionDef, pyast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= line <= end:
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


_BUILTIN_SKIP = frozenset({
    "print", "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr", "delattr",
    "open", "super", "type", "repr", "hash", "id", "iter", "next",
    "any", "all", "min", "max", "sum", "abs", "round",
})


# ── callee collection (S5) ────────────────────────────────────────────────────

def _find_callees(workspace: str, file_path: str, line: int) -> list[dict]:
    """AST 1-hop: functions called within the enclosing function.

    core/ + scripts/ 에서 정의 위치를 grep.
    재귀·built-in·dunder 제외 (§5.4).
    """
    func_node = _enclosing_function(file_path, line)
    if func_node is None:
        return []

    search_dirs = [d for d in [
        os.path.join(workspace, "core"),
        os.path.join(workspace, "scripts"),
    ] if os.path.isdir(d)]

    seen: set[str] = set()
    callees: list[dict] = []

    for node in pyast.walk(func_node):
        if not isinstance(node, pyast.Call):
            continue
        if isinstance(node.func, pyast.Name):
            name = node.func.id
        elif isinstance(node.func, pyast.Attribute):
            name = node.func.attr
        else:
            continue

        if name in _BUILTIN_SKIP or name.startswith("__") or name in seen:
            continue
        seen.add(name)

        defined_at = None
        for d in search_dirs:
            try:
                r = subprocess.run(
                    ["grep", "-rn", "--include=*.py", f"def {name}(", d],
                    capture_output=True, text=True, timeout=5,
                )
                for match in r.stdout.splitlines():
                    parts = match.split(":", 2)
                    if len(parts) >= 3:
                        defined_at = f"{parts[0]}:{parts[1]}"
                        break
            except Exception:
                pass
            if defined_at:
                break

        callees.append({
            "callee": name,
            "call_line": node.lineno,
            "defined_at": defined_at,
        })
        if len(callees) >= 10:
            break

    return callees


# ── caller collection (§5.3 재사용 — _find_direct_callers 래퍼) ───────────────

def _find_callers(workspace: str, file_path: str, line: int) -> list[dict]:
    """Grep 1-hop: who calls the function enclosing line.

    review_bundle._find_direct_callers과 동형 — finding 단위 래퍼 (§2.2 갭 메움).
    """
    func_node = _enclosing_function(file_path, line)
    sym = func_node.name if func_node else None
    if not sym:
        return []

    search_dirs = [d for d in [
        os.path.join(workspace, "core"),
        os.path.join(workspace, "scripts"),
    ] if os.path.isdir(d)]

    callers: list[dict] = []
    for d in search_dirs:
        if len(callers) >= 5:
            break
        try:
            r = subprocess.run(
                ["grep", "-rn", "--include=*.py", f"{sym}(", d],
                capture_output=True, text=True, timeout=5,
            )
            for match in r.stdout.splitlines():
                if len(callers) >= 5:
                    break
                parts = match.split(":", 2)
                if len(parts) < 3:
                    continue
                caller_file, ln_str, code = parts
                if re.match(rf'\s*(def|class)\s+{re.escape(sym)}\b', code):
                    continue
                try:
                    caller_line = int(ln_str)
                except ValueError:
                    continue
                callers.append({
                    "file": caller_file,
                    "line": caller_line,
                    "symbol": sym,
                    "snippet": code.strip()[:120],
                })
        except Exception:
            pass
    return callers


# ── test collection (§5.3 재사용 — _find_related_tests 래퍼) ─────────────────

def _find_tests(workspace: str, file_path: str, line: int) -> dict:
    """Grep tests/ for files referencing module or function at line."""
    func_node = _enclosing_function(file_path, line)
    sym = func_node.name if func_node else None
    module = os.path.splitext(os.path.basename(file_path))[0]
    tests_dir = os.path.join(workspace, "tests")
    if not os.path.isdir(tests_dir):
        return {}

    terms = [module]
    if sym:
        terms.append(sym)

    related: dict[str, None] = {}
    for term in terms:
        try:
            r = subprocess.run(
                ["grep", "-rl", "--include=test_*.py", term, tests_dir],
                capture_output=True, text=True, timeout=5,
            )
            for tf in r.stdout.splitlines():
                if tf.strip():
                    related[tf.strip()] = None
        except Exception:
            pass

    result: dict[str, list[str]] = {}
    for tf in sorted(related)[:3]:
        try:
            content = Path(tf).read_text(encoding="utf-8", errors="replace")
            funcs = re.findall(r"^def (test_\w+)\(", content, re.MULTILINE)
            result[tf] = funcs[:5]
        except Exception:
            result[tf] = []
    return result


# ── evidence collection (§5.3 public API) ────────────────────────────────────

def collect_evidence(workspace: str, findings: list[dict]) -> list[dict]:
    """For each ACCEPT/ACCEPT★ finding with file+line, collect evidence pack.

    ACCEPT-ADV/REJECTED/BONUS는 non-blocking → skip_reason만 기록.
    file:line 누락 또는 파일 미존재 → consensus=UNVERIFIED (INV-5).
    """
    evidence: list[dict] = []
    for f in findings:
        fid = f.get("id", "?")
        label = f.get("label", "")
        file_path = f.get("file")
        line = f.get("line")

        if label not in ("ACCEPT", "ACCEPT★"):
            evidence.append({"id": fid, "label": label, "skip_reason": "non-blocking label"})
            continue

        if not file_path or line is None:
            evidence.append({
                "id": fid, "label": label,
                "skip_reason": "no file:line", "consensus": "UNVERIFIED",
            })
            continue

        abs_file = file_path if os.path.isabs(file_path) else os.path.join(workspace, file_path)
        if not os.path.isfile(abs_file):
            evidence.append({
                "id": fid, "label": label, "file": file_path, "line": line,
                "skip_reason": "file not found", "consensus": "UNVERIFIED",
            })
            continue

        evidence.append({
            "id": fid,
            "label": label,
            "severity": f.get("severity"),
            "file": file_path,
            "line": line,
            "claim": f.get("claim", ""),
            "surrounding_code": _surrounding_code(abs_file, line),
            "callers": _find_callers(workspace, abs_file, line),
            "callees": _find_callees(workspace, abs_file, line),
            "tests": _find_tests(workspace, abs_file, line),
        })
    return evidence


# ── main ──────────────────────────────────────────────────────────────────────

def main(workspace: str | None = None) -> int:
    ws = workspace or os.getcwd()
    q = Path(ws) / ".af_review_queue"
    findings_path = q / "cr_findings.json"
    evidence_path = q / "cr_evidence.json"

    if not findings_path.exists():
        print("cr_findings.json 없음 — 합의기 SKIP", file=sys.stderr)
        return 0

    try:
        data = json.loads(findings_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"cr_findings.json 파싱 실패: {e}", file=sys.stderr)
        return 1

    findings = data.get("findings", [])
    evidence = collect_evidence(ws, findings)

    out = {"round": data.get("round"), "evidence": evidence}
    q.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cr_evidence.json 저장: {len(evidence)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
